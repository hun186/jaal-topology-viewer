"""Bounded temporal graph snapshots from timestamped directed events.

The original Graph stays an immutable *full-period* source. All snapshots
are derived from event timestamps and have their own per-window edge weights
and Louvain membership. No real mail connection, filesystem writes, or
background scheduler is involved.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, time, timedelta, timezone

from .community import detect_louvain
from .data import Graph, GraphInputError

MAX_TEMPORAL_DAYS = 120
MAX_TEMPORAL_EVENTS = 50_000
MAX_TEMPORAL_FRAMES_EDGES = 180_000
MAX_TEMPORAL_FRAMES = 240


class TemporalTimeline:
    """Time-ordered directed events with consistent naive-local or aware-UTC dates."""

    def __init__(self, graph: Graph, events):
        if not isinstance(graph, Graph) or not graph.edges:
            raise GraphInputError("Temporal timeline requires a populated Graph")
        events = tuple(events)
        if not 1 <= len(events) <= MAX_TEMPORAL_EVENTS:
            raise GraphInputError("Temporal event count is out of bounds")
        if len(graph.nodes) > 3000 or len(graph.edges) > 5000:
            raise GraphInputError("Temporal source graph exceeds render bounds")
        edge_set = set(graph.edges)
        daily = {}
        timestamped = []
        aware = None
        for event in events:
            try:
                timestamp = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
                sender, recipient = str(event.sender), str(event.recipient)
            except (AttributeError, TypeError, ValueError) as exc:
                raise GraphInputError("Temporal events need valid ISO timestamps and endpoints") from exc
            current_aware = timestamp.tzinfo is not None and (
                timestamp.utcoffset() is not None
            )
            if aware is None:
                aware = current_aware
            elif current_aware != aware:
                raise GraphInputError("Do not mix timezone-aware and naive event timestamps")
            if current_aware:
                timestamp = timestamp.astimezone(timezone.utc)
            if (sender, recipient) not in edge_set:
                raise GraphInputError("Temporal event endpoint absent from source Graph")
            day = timestamp.date()
            daily.setdefault(day, Counter())[(sender, recipient)] += 1
            timestamped.append((timestamp, (sender, recipient)))
        self.graph = graph
        self.timezone = "UTC" if aware else "local-naive"
        self.by_day = daily
        # Minute/hour analysis needs original timestamps: daily counters alone
        # cannot reconstruct precise half-open windows.
        self._timestamped = tuple(sorted(timestamped, key=lambda row: row[0]))
        self.first_day = min(daily)
        self.last_day = max(daily)
        days = (self.last_day - self.first_day).days + 1
        if days > MAX_TEMPORAL_DAYS:
            raise GraphInputError("Temporal date span exceeds 120 calendar days")
        self.days = tuple(
            self.first_day + timedelta(days=i) for i in range(days)
        )
        self._edges = tuple(graph.edges)
        self._last_counts = sum(daily.values(), Counter())
        if graph.edge_counts and dict(self._last_counts) != graph.edge_counts:
            raise GraphInputError("Temporal events do not match the full graph edge counts")

    def snapshot(self, day_index: int, *, first_index: int = 0,
                 last_index: int | None = None, mode="cumulative",
                 window_days=7):
        """Return a true windowed graph plus display metadata.

        Both time bounds and the playhead are calendar-day indices.
        Cumulative: [first_index, playhead].
        Rolling: [max(first_index, playhead-window_days+1), playhead].
        """
        n = len(self.days)
        if last_index is None:
            last_index = n - 1
        if (any(type(x) is not int for x in (day_index, first_index, last_index))
                or not 0 <= first_index <= last_index < n
                or not first_index <= day_index <= last_index):
            raise GraphInputError("Invalid temporal selection or playhead")
        if mode not in ("cumulative", "rolling"):
            raise GraphInputError("Temporal mode must be cumulative or rolling")
        if type(window_days) is not int or not 1 <= window_days <= 60:
            raise GraphInputError("Rolling window must be between 1 and 60 days")
        start = (first_index if mode == "cumulative" else
                 max(first_index, day_index - window_days + 1))
        counts = Counter()
        for i in range(start, day_index + 1):
            counts.update(self.by_day.get(self.days[i], ()))
        endpoints = {id_ for pair in counts for id_ in pair}
        graph = Graph(
            tuple(sorted(counts)),
            tuple(node for node in self.graph.nodes if node in endpoints),
            {id_: label for id_, label in self.graph.translations.items()
             if id_ in endpoints},
            dict(counts),
        )
        return graph, {
            "date": self.days[day_index].isoformat(),
            "from": self.days[start].isoformat(),
            "to": self.days[day_index].isoformat(),
            "messages": sum(counts.values()),
            "nodes": len(graph.nodes),
            "links": len(graph.edges),
            "mode": mode,
        }

    def frames(self, *, first_index=0, last_index=None,
               mode="cumulative", window_days=7):
        """Precompute bounded frames; client playback uses NO per-tick HTTP."""
        if last_index is None:
            last_index = len(self.days) - 1
        if (type(first_index) is not int or type(last_index) is not int or
                not 0 <= first_index <= last_index < len(self.days) or
                mode not in ("cumulative", "rolling") or
                type(window_days) is not int or not 1 <= window_days <= 60):
            raise GraphInputError("Invalid temporal frame selection")
        rows = []
        total_edges = 0
        for index in range(first_index, last_index + 1):
            snap, meta = self.snapshot(
                index, first_index=first_index, last_index=last_index,
                mode=mode, window_days=window_days,
            )
            total_edges += len(snap.edges)
            if total_edges > MAX_TEMPORAL_FRAMES_EDGES:
                raise GraphInputError("Temporal frame payload exceeds 180000 edges")
            groups = detect_louvain(snap)
            rows.append({
                **meta,
                "edges": [
                    [a, b, snap.edge_counts[(a, b)]]
                    for a, b in snap.edges
                ],
                "partition": groups.member_to_group,
            })
        return {
            "frames": rows,
            "start_index": first_index,
            "end_index": last_index,
            "timezone": self.timezone,
        }

    def interval_frames(self, *, start_minute=0, end_minute=None,
                        mode="rolling", window_minutes=4320,
                        step_minutes=None):
        """Bounded minute-resolution playback with [start,end) event semantics.

        Offsets are integer minutes since midnight at the first event day.
        rolling + step==window is a disjoint partition (the default).
        rolling + step<window overlaps; cumulative retains the analysis start.
        Day-based snapshot()/frames() stay backwards-compatible.
        """
        from datetime import datetime as _datetime
        base = _datetime.combine(
            self.first_day, time.min,
            tzinfo=timezone.utc if self.timezone == "UTC" else None,
        )
        total = len(self.days) * 1440
        if end_minute is None:
            end_minute = total
        if step_minutes is None:
            step_minutes = window_minutes
        if (any(type(value) is not int for value in (
                start_minute, end_minute, window_minutes, step_minutes))
                or not 0 <= start_minute < end_minute <= total
                or not 1 <= window_minutes <= MAX_TEMPORAL_DAYS * 1440
                or not 1 <= step_minutes <= window_minutes
                or mode not in ("rolling", "cumulative")):
            raise GraphInputError("Invalid precise temporal interval, window or step")
        # Strict capacity guard: never silently skip frames or collapse the
        # user's requested 1-minute precision into daily counts.
        starts = range(start_minute, end_minute, step_minutes)
        if len(starts) > MAX_TEMPORAL_FRAMES:
            raise GraphInputError(
                "Too many animation frames (max 240); narrow the selected "
                "analysis dates/times, or choose a larger window/step"
            )
        rows = []
        total_edges = 0
        for offset in starts:
            lo = start_minute if mode == "cumulative" else offset
            hi = min(end_minute, offset + window_minutes)
            begin = base + timedelta(minutes=lo)
            finish = base + timedelta(minutes=hi)
            counts = Counter(pair for timestamp, pair in self._timestamped
                             if begin <= timestamp < finish)
            endpoints = {id_ for pair in counts for id_ in pair}
            snap = Graph(
                tuple(sorted(counts)),
                tuple(node for node in self.graph.nodes if node in endpoints),
                {id_: label for id_, label in self.graph.translations.items()
                 if id_ in endpoints},
                dict(counts),
            )
            total_edges += len(snap.edges)
            if total_edges > MAX_TEMPORAL_FRAMES_EDGES:
                raise GraphInputError("Temporal frame payload exceeds 180000 edges")
            groups = detect_louvain(snap)
            start_iso = begin.isoformat(timespec="minutes")
            end_iso = finish.isoformat(timespec="minutes")
            rows.append({
                "date": start_iso, "from": start_iso, "to": end_iso,
                "to_exclusive": end_iso, "mode": mode,
                "messages": sum(counts.values()),
                "nodes": len(snap.nodes), "links": len(snap.edges),
                "edges": [[a, b, snap.edge_counts[(a, b)]]
                          for a, b in snap.edges],
                "partition": groups.member_to_group,
                "window_minutes": window_minutes,
                "step_minutes": step_minutes,
                "axis_start": (lo - start_minute) / (end_minute - start_minute),
                "axis_end": (hi - start_minute) / (end_minute - start_minute),
            })
        return {
            "frames": rows,
            "start_index": 0, "end_index": len(rows) - 1,
            "timezone": self.timezone, "unit_minutes": 1,
            "window_minutes": window_minutes,
            "step_minutes": step_minutes,
            "analysis_from": (base + timedelta(minutes=start_minute)).isoformat(timespec="minutes"),
            "analysis_to_exclusive": (base + timedelta(minutes=end_minute)).isoformat(timespec="minutes"),
        }
