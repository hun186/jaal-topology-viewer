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
