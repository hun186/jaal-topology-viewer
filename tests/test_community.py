"""Deterministic Louvain topology and directed quotient invariants."""
from pathlib import Path
import unittest

from jaal_topology import Graph, GraphInputError, load_graph, select_subgraph
from jaal_topology.community import detect_louvain


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
