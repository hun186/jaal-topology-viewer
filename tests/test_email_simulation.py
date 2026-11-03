"""Business-process and reproducibility checks for fictional mail demo."""
from __future__ import annotations

import csv
import io
import unittest
from collections import Counter
from datetime import datetime

from jaal_topology.email_simulation import (
    SEED, WORKFLOW_LABELS, simulate_company_email,
)
from jaal_topology import Graph, GraphInputError, select_subgraph
from jaal_topology.viewer import to_jaal_dataframes
from jaal_topology.community import detect_louvain


class BusinessEmailSimulationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sample = simulate_company_email()

    def test_deterministic_20_day_event_log_and_unique_pair_counts(self):
        a = self.sample
        self.assertEqual(a, simulate_company_email(SEED))
        self.assertNotEqual(a.events, simulate_company_email(SEED + 1).events)
        self.assertGreater(len(a.events), 1000)
        self.assertLess(len(a.events), 6000)
        self.assertGreaterEqual(len(a.graph.nodes), 70)
        self.assertLessEqual(len(a.graph.nodes), 90)
        self.assertGreater(len(a.graph.edges), 160)
        self.assertLess(len(a.graph.edges), 5000)
        self.assertEqual(sum(a.counts.values()), len(a.events))
        self.assertEqual(set(a.graph.edges), set(a.counts))
        self.assertEqual(a.graph.edge_counts, a.counts)
        self.assertEqual(len(set(m.id for m in a.events)), len(a.events))
        self.assertTrue(all(m.workflow in WORKFLOW_LABELS for m in a.events))
        self.assertTrue(all(m.sender != m.recipient for m in a.events))
        self.assertTrue(all(
            a.events[i].timestamp <= a.events[i + 1].timestamp
            for i in range(len(a.events) - 1)
        ))

    def test_replies_have_a_prior_original_same_thread_and_reverse_direction(self):
        a = self.sample
        by_id = {m.id: m for m in a.events}
        replies = [m for m in a.events if m.reply_to]
        self.assertGreater(len(replies), 200)
        for reply in replies:
            original = by_id[reply.reply_to]
            self.assertEqual(reply.thread_id, original.thread_id)
            self.assertEqual((reply.sender, reply.recipient),
                             (original.recipient, original.sender))
            self.assertGreater(datetime.fromisoformat(reply.timestamp),
                               datetime.fromisoformat(original.timestamp))
        self.assertTrue(
            any((b, a) in self.sample.counts for a, b in self.sample.counts)
        )

    def test_business_pattern_has_department_assortativity_and_event_spikes(self):
        a = self.sample
        share = sum(
            a.divisions[m.sender] == a.divisions[m.recipient]
            for m in a.events
        ) / len(a.events)
        self.assertGreater(share, 0.48)
        self.assertLess(share, 0.93)
        workflows = Counter(m.workflow for m in a.events)
        for case in WORKFLOW_LABELS:
            self.assertGreater(workflows[case], 0, case)
        self.assertGreater(workflows["team-routine"], workflows["management-update"])
        self.assertGreater(workflows["customer-deal"], workflows["management-update"])
        incident = [m for m in a.events if m.workflow == "incident-response"]
        self.assertGreater(len(incident), 30)
        self.assertTrue(all(datetime.fromisoformat(m.timestamp).hour >= 20
                            for m in incident))
        self.assertLess(
            sum(m.sender == "Executive / CEO" for m in a.events),
            sum(m.sender.startswith("Engineering /") for m in a.events),
        )
        self.assertGreater(len({m.thread_id for m in a.events}), 200)

    def test_csv_export_matches_events_and_aggregation(self):
        a = self.sample
        rows = list(csv.DictReader(io.StringIO(a.events_csv())))
        self.assertEqual(len(rows), len(a.events))
        self.assertIn("reply_to", rows[0])
        self.assertEqual(len(set(row["event_id"] for row in rows)), len(rows))
        aggregate = list(csv.DictReader(io.StringIO(a.aggregate_csv())))
        self.assertEqual(len(aggregate), len(a.graph.edges))
        self.assertEqual(sum(int(row["message_count"]) for row in aggregate),
                         len(a.events))
        self.assertTrue(all(row["synthetic"] == "true" for row in aggregate))

    def test_weighted_louvain_and_node_volume_keep_legacy_separate(self):
        a = self.sample
        result = detect_louvain(a.graph)
        self.assertEqual(result.method, "directed-louvain-message-count-weighted")
        self.assertEqual(result, detect_louvain(a.graph))
        self.assertEqual(sum(result.cross_group_edges.values()) +
                         sum(result.internal_edges.values()), len(a.graph.edges))
        edges, nodes = to_jaal_dataframes(a.graph)
        self.assertIn("SentEmails", nodes)
        self.assertIn("ReceivedEmails", nodes)
        self.assertEqual(sum(nodes.SentEmails), len(a.events))
        self.assertEqual(sum(nodes.ReceivedEmails), len(a.events))
        base = Graph(a.graph.edges, a.graph.nodes, a.graph.translations)
        self.assertEqual(detect_louvain(base).method,
                         "directed-louvain-topology-only")
        _, ordinary_nodes = to_jaal_dataframes(base)
        self.assertNotIn("SentEmails", ordinary_nodes)
        subset = select_subgraph(a.graph, a.graph.nodes[0], max_nodes=250)
        self.assertEqual(set(subset.edge_counts), set(subset.edges))
        with self.assertRaises(GraphInputError):
            simulate_company_email(-1)
        with self.assertRaises(GraphInputError):
            simulate_company_email(True)


if __name__ == "__main__":
    unittest.main()
