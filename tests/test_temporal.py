"""Time-window correctness, safety bounds and compatibility with old Graphs."""
from __future__ import annotations

import unittest

from jaal_topology import Graph, GraphInputError
from jaal_topology.email_simulation import EmailEvent, simulate_company_email
from jaal_topology.temporal import TemporalTimeline


class TemporalTimelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.simulation = simulate_company_email()
        cls.timeline = TemporalTimeline(cls.simulation.graph,
                                        cls.simulation.events)

    def test_full_cumulative_snapshot_equals_authoritative_events(self):
        t = self.timeline
        self.assertGreater(len(t.days), 20)
        self.assertLessEqual(len(t.days), 31)
        self.assertEqual(t.timezone, "local-naive")
        full, meta = t.snapshot(len(t.days) - 1)
        self.assertEqual(full.edge_counts, self.simulation.graph.edge_counts)
        self.assertEqual(full.edges, self.simulation.graph.edges)
        self.assertEqual(meta["messages"], len(self.simulation.events))
        self.assertEqual(meta["nodes"], len(full.nodes))
        self.assertEqual(meta["links"], len(full.edges))
        self.assertEqual(meta["from"], t.first_day.isoformat())
        self.assertEqual(meta["to"], t.last_day.isoformat())

    def test_real_rolling_window_and_custom_range_are_not_labels_only(self):
        t = self.timeline
        i = len(t.days) - 1
        one, one_meta = t.snapshot(i, mode="rolling", window_days=1)
        week, week_meta = t.snapshot(i, mode="rolling", window_days=7)
        alltime, all_meta = t.snapshot(i, mode="cumulative")
        self.assertEqual(sum(one.edge_counts.values()), one_meta["messages"])
        self.assertEqual(sum(week.edge_counts.values()), week_meta["messages"])
        self.assertTrue(0 <= one_meta["messages"] <= week_meta["messages"] <
                        all_meta["messages"])
        self.assertEqual(one_meta["from"], t.days[i].isoformat())
        self.assertEqual(week_meta["from"], t.days[i-6].isoformat())
        start = 6
        subset, segment = t.snapshot(i, first_index=start, mode="cumulative")
        self.assertLess(segment["messages"], all_meta["messages"])
        self.assertEqual(segment["from"], t.days[start].isoformat())
        self.assertTrue(set(subset.edges).issubset(set(alltime.edges)))

    def test_frames_recalculate_partition_and_emit_bounded_compact_pairs(self):
        t = self.timeline
        packet = t.frames(first_index=4, last_index=11,
                          mode="rolling", window_days=3)
        self.assertEqual(len(packet["frames"]), 8)
        self.assertEqual((packet["start_index"], packet["end_index"]), (4, 11))
        for frame in packet["frames"]:
            self.assertEqual(frame["messages"], sum(
                count for _, _, count in frame["edges"]))
            self.assertEqual(frame["links"], len(frame["edges"]))
            live_nodes = {id_ for a, b, _ in frame["edges"] for id_ in (a, b)}
            self.assertEqual(set(frame["partition"]), live_nodes)
            self.assertLessEqual(len(frame["edges"]), 5000)
        self.assertEqual(packet, t.frames(first_index=4, last_index=11,
                                          mode="rolling", window_days=3))

    def test_rolling_slice_expires_real_edges_while_cumulative_retains_them(self):
        graph = Graph(
            (("A", "B"), ("C", "D")),
            ("A", "B", "C", "D"),
            edge_counts={("A", "B"): 2, ("C", "D"): 1},
        )
        events = [
            EmailEvent("1", "2026-10-05T09:00", "t1", "A", "B", "team-routine", "one"),
            EmailEvent("2", "2026-10-05T10:00", "t1", "A", "B", "team-routine", "two"),
            EmailEvent("3", "2026-10-07T10:00", "t2", "C", "D", "team-routine", "three"),
        ]
        timeline = TemporalTimeline(graph, events)
        rolling, rolling_meta = timeline.snapshot(2, mode="rolling", window_days=1)
        cumulative, cumulative_meta = timeline.snapshot(2, mode="cumulative")
        self.assertEqual(rolling.edge_counts, {("C", "D"): 1})
        self.assertEqual(rolling_meta["from"], "2026-10-07")
        self.assertEqual(rolling_meta["messages"], 1)
        self.assertEqual(cumulative.edge_counts, graph.edge_counts)
        self.assertEqual(cumulative_meta["messages"], 3)
        frame = timeline.frames(mode="rolling", window_days=1)["frames"][2]
        self.assertEqual(frame["edges"], [["C", "D", 1]])
        self.assertEqual(frame["links"], 1)

    def test_exact_half_open_disjoint_minute_boundaries_and_overlapping_hour_windows(self):
        graph = Graph(
            (("A", "B"), ("C", "D")), ("A", "B", "C", "D"),
            edge_counts={("A", "B"): 3, ("C", "D"): 1},
        )
        events = [
            EmailEvent("1", "2026-10-05T09:00", "x", "A", "B", "team-routine", "one"),
            EmailEvent("2", "2026-10-05T09:09", "x", "A", "B", "team-routine", "two"),
            EmailEvent("3", "2026-10-05T09:10", "x", "C", "D", "team-routine", "boundary"),
            EmailEvent("4", "2026-10-05T09:20", "x", "A", "B", "team-routine", "tail"),
        ]
        timeline = TemporalTimeline(graph, events)
        start = 9 * 60
        disjoint = timeline.interval_frames(
            start_minute=start, end_minute=start + 30,
            mode="rolling", window_minutes=10, step_minutes=10,
        )
        self.assertEqual(len(disjoint["frames"]), 3)
        self.assertEqual(
            [f["messages"] for f in disjoint["frames"]], [2, 1, 1]
        )
        self.assertEqual(
            disjoint["frames"][0]["to_exclusive"],
            disjoint["frames"][1]["from"]
        )
        self.assertEqual(disjoint["frames"][1]["edges"], [["C", "D", 1]])
        self.assertEqual(disjoint["frames"][1]["from"], "2026-10-05T09:10")
        self.assertEqual(disjoint["frames"][0]["to"], "2026-10-05T09:10")
        self.assertEqual(disjoint["frames"][1]["axis_start"], 1/3)
        self.assertEqual(disjoint["frames"][1]["axis_end"], 2/3)
        overlap = timeline.interval_frames(
            start_minute=start, end_minute=start + 30,
            mode="rolling", window_minutes=20, step_minutes=10,
        )
        self.assertEqual(
            [f["messages"] for f in overlap["frames"]], [3, 2, 1]
        )
        cumulative = timeline.interval_frames(
            start_minute=start, end_minute=start + 30,
            mode="cumulative", window_minutes=10, step_minutes=10,
        )
        self.assertEqual(
            [f["messages"] for f in cumulative["frames"]], [2, 3, 4]
        )
        self.assertEqual([f["axis_start"] for f in cumulative["frames"]],
                         [0, 0, 0])
        self.assertEqual(sum(f["messages"] for f in disjoint["frames"]), 4)

    def test_minute_resolution_is_bounded_not_silently_downsampled(self):
        t = self.timeline
        with self.assertRaisesRegex(GraphInputError, "max 240"):
            t.interval_frames(window_minutes=1, step_minutes=1)
        with self.assertRaises(GraphInputError):
            t.interval_frames(window_minutes=10, step_minutes=20)
        with self.assertRaises(GraphInputError):
            t.interval_frames(start_minute=100, end_minute=100)
        with self.assertRaises(GraphInputError):
            t.interval_frames(start_minute=0, end_minute=3, step_minutes=0)
        packet = t.interval_frames(
            start_minute=100, end_minute=104,
            window_minutes=1, step_minutes=1,
        )
        self.assertEqual(len(packet["frames"]), 4)
        self.assertEqual(packet["frames"][0]["from"][-5:], "01:40")
        self.assertEqual(packet["frames"][-1]["to_exclusive"][-5:], "01:44")
        self.assertEqual(packet["timezone"], "local-naive")

    def test_empty_weekend_does_not_invent_mail_or_edges(self):
        graph = Graph((("A", "B"),), ("A", "B"),
                      edge_counts={("A", "B"): 2})
        records = [
            EmailEvent("1", "2026-10-05T09:00", "t1", "A", "B", "team-routine", "x"),
            EmailEvent("2", "2026-10-07T11:00", "t2", "A", "B", "team-routine", "y"),
        ]
        t = TemporalTimeline(graph, records)
        empty, meta = t.snapshot(1, mode="rolling", window_days=1)
        self.assertEqual((len(empty.edges), len(empty.nodes)), (0, 0))
        self.assertEqual(meta["messages"], 0)
        self.assertEqual(t.frames(mode="rolling", window_days=1)["frames"][1]["partition"], {})
        cumulative, cumul_meta = t.snapshot(1)
        self.assertEqual(cumul_meta["messages"], 1)
        self.assertEqual(cumulative.edge_counts[("A", "B")], 1)

    def test_reject_timezone_mixing_invalid_ranges_and_untrusted_edges(self):
        sim = self.simulation
        with self.assertRaises(GraphInputError):
            self.timeline.snapshot(-1)
        with self.assertRaises(GraphInputError):
            self.timeline.snapshot(len(self.timeline.days))
        with self.assertRaises(GraphInputError):
            self.timeline.snapshot(2, first_index=3)
        with self.assertRaises(GraphInputError):
            self.timeline.snapshot(2, mode="future")
        with self.assertRaises(GraphInputError):
            self.timeline.snapshot(2, window_days=0)
        with self.assertRaises(GraphInputError):
            self.timeline.frames(first_index=5, last_index=4)
        with self.assertRaises(GraphInputError):
            self.timeline.frames(window_days=999)
        with self.assertRaises(GraphInputError):
            TemporalTimeline(sim.graph, [
                EmailEvent("1", "2026-10-05T09:00", "x", "Missing",
                           "Other", "team-routine", "x")
            ])
        graph = Graph((("A", "B"),), ("A", "B"),
                      edge_counts={("A", "B"): 2})
        with self.assertRaises(GraphInputError):
            TemporalTimeline(graph, [
                EmailEvent("1", "2026-10-05T09:00", "a", "A", "B",
                           "team-routine", "1"),
                EmailEvent("2", "2026-10-05T09:00Z", "b", "A", "B",
                           "team-routine", "2"),
            ])


if __name__ == "__main__":
    unittest.main()
