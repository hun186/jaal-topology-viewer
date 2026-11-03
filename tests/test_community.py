"""Deterministic Louvain topology and directed quotient invariants."""
from pathlib import Path
import unittest

from jaal_topology import Graph, GraphInputError, load_graph, select_subgraph
from jaal_topology.community import detect_louvain, community_quotient_has_cycle


class DirectedCommunityTests(unittest.TestCase):
    def test_general_company_demo_is_partitioned_and_direction_is_preserved(self):
        folder = Path(__file__).resolve().parents[1] / "examples"
        graph = select_subgraph(load_graph(
            folder / "company_communications.csv",
            folder / "company_people.csv",
        ))
        result = detect_louvain(graph)
        again = detect_louvain(graph)
        self.assertEqual(result, again)
        self.assertIsInstance(result.quotient_has_cycle, bool)
        self.assertEqual(len(result.member_to_group), 77)
        self.assertEqual(set(result.member_to_group), set(graph.nodes))
        self.assertGreaterEqual(len(result.groups), 2)
        self.assertEqual(
            sum(result.cross_group_edges.values()) +
            sum(result.internal_edges.values()),
            169,
        )
        for (a, b), count in result.cross_group_edges.items():
            self.assertNotEqual(a, b)
            self.assertGreater(count, 0)

    def test_cycle_reciprocals_disconnected_components_and_isolates(self):
        edges = (("A", "B"), ("B", "A"), ("B", "C"), ("C", "A"),
                 ("D", "E"), ("E", "D"))
        graph = Graph(edges, ("A", "B", "C", "D", "E", "F"), {})
        result = detect_louvain(graph)
        self.assertEqual(set(result.member_to_group), set(graph.nodes))
        self.assertEqual(sum(map(len, result.groups)), len(graph.nodes))
        self.assertEqual(
            sum(result.internal_edges.values()) +
            sum(result.cross_group_edges.values()), len(edges),
        )
        self.assertEqual(result.groups, detect_louvain(graph).groups)

    def test_quotient_cycle_does_not_imply_original_dag_cycle(self):
        from jaal_topology.data import assess_structural_collapse
        original = Graph(
            (("A", "C"), ("D", "B")),
            ("A", "B", "C", "D"),
        )
        self.assertFalse(assess_structural_collapse(original).has_cycle)
        partition = {"A": "alpha", "B": "alpha",
                     "C": "beta", "D": "beta"}
        projected = tuple(
            (partition[a], partition[b]) for a, b in original.edges
        )
        self.assertTrue(
            community_quotient_has_cycle(partition.values(), projected)
        )
        self.assertFalse(community_quotient_has_cycle(
            partition.values(), (("alpha", "beta"),)
        ))
        self.assertFalse(community_quotient_has_cycle(
            partition.values(), (("alpha", "alpha"),)
        ))
        self.assertFalse(detect_louvain(Graph((), ("Solo",))).quotient_has_cycle)

    def test_empty_and_invalid_inputs(self):
        graph = Graph((), ("Solo",), {})
        result = detect_louvain(graph)
        self.assertEqual(result.groups, (("Solo",),))
        for resolution in (0, -1, float("nan"), float("inf"), True):
            with self.subTest(resolution=resolution):
                with self.assertRaises(GraphInputError):
                    detect_louvain(graph, resolution=resolution)
        with self.assertRaises(GraphInputError):
            detect_louvain(graph, seed=True)
        with self.assertRaises(GraphInputError):
            detect_louvain(Graph((("A", "missing"),), ("A",), {}))

    def test_resolution_and_seed_are_repeatable_without_losing_direction(self):
        # A complete directed graph has one group at low resolution,
        # and singleton groups at sufficiently high resolution.
        nodes = tuple(f"Node-{index}" for index in range(6))
        edges = tuple((a, b) for a in nodes for b in nodes if a != b)
        graph = Graph(edges, nodes)
        low = detect_louvain(graph, seed=7, resolution=0.01)
        high = detect_louvain(graph, seed=7, resolution=10.0)
        self.assertEqual(low, detect_louvain(graph, seed=7, resolution=0.01))
        self.assertEqual(high, detect_louvain(graph, seed=7, resolution=10.0))
        self.assertEqual(len(low.groups), 1)
        self.assertEqual(len(high.groups), len(nodes))
        self.assertEqual(high.seed, 7)
        self.assertEqual(high.resolution, 10.0)
        self.assertEqual(set(high.member_to_group), set(nodes))
        self.assertEqual(
            sum(high.cross_group_edges.values()) +
            sum(high.internal_edges.values()), len(edges),
        )
        a, b = high.member_to_group[nodes[0]], high.member_to_group[nodes[1]]
        self.assertEqual(high.cross_group_edges[(a, b)], 1)
        self.assertEqual(high.cross_group_edges[(b, a)], 1)
        self.assertEqual(graph.edges, edges)

    def test_maximum_bounded_graph_and_one_over_limit_fail_closed(self):
        # Exact documented viewer ceiling, not a synthetic small-graph proxy.
        nodes = tuple(f"N{index:04d}" for index in range(3000))
        edges = (
            tuple((nodes[i], nodes[(i + 1) % 3000]) for i in range(3000)) +
            tuple((nodes[i], nodes[(i + 17) % 3000]) for i in range(2000))
        )
        graph = Graph(edges, nodes)
        result = detect_louvain(graph)
        self.assertEqual(result, detect_louvain(graph))
        self.assertEqual(len(result.member_to_group), 3000)
        self.assertEqual(set(result.member_to_group), set(nodes))
        self.assertEqual(sum(map(len, result.groups)), 3000)
        self.assertEqual(
            sum(result.cross_group_edges.values()) +
            sum(result.internal_edges.values()), 5000,
        )
        self.assertEqual(len(set(graph.edges)), 5000)
        self.assertEqual(graph.edges, edges)
        with self.assertRaises(GraphInputError):
            detect_louvain(Graph(edges, nodes + ("EXTRA",)))
        with self.assertRaises(GraphInputError):
            detect_louvain(Graph(edges + ((nodes[2000], nodes[2017]),), nodes))
