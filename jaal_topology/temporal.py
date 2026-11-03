"""Bounded temporal graph snapshots from timestamped directed events.

The original Graph stays an immutable *full-period* source. All snapshots
are derived from event timestamps and have their own per-window edge weights
and Louvain membership. No real mail connection, filesystem writes, or
background scheduler is involved.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone

from .community import detect_louvain
from .data import Graph, GraphInputError

MAX_TEMPORAL_DAYS = 120
MAX_TEMPORAL_EVENTS = 50_000
MAX_TEMPORAL_FRAMES_EDGES = 180_000


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
        self.graph = graph
        self.timezone = "UTC" if aware else "local-naive"
        self.by_day = daily
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
