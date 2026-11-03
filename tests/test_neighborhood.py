"""Root-centered local graph exploration for DAG, cycles and disconnected data."""
import unittest

from jaal_topology import Graph, GraphInputError
from jaal_topology.neighborhood import reachable_node_ids


class ReachableNeighborhoodTests(unittest.TestCase):
    def setUp(self):
        self.graph = Graph(
            (("A", "B"), ("B", "C"), ("C", "A"), ("C", "D"),
             ("E", "A"), ("F", "E")),
            ("A", "B", "C", "D", "E", "F", "Z"),
            {"A": "主管", "C": "同事"},
        )

    def test_outgoing_radius_contains_unique_original_ids(self):
        self.assertEqual(reachable_node_ids(self.graph, "A", hops=0), ("A",))
        self.assertEqual(reachable_node_ids(self.graph, "A", hops=1), ("A", "B"))
        self.assertEqual(reachable_node_ids(self.graph, "A", hops=2),
                         ("A", "B", "C"))
        self.assertEqual(reachable_node_ids(self.graph, "A", hops=3),
                         ("A", "B", "C", "D"))
        self.assertEqual(reachable_node_ids(self.graph, "A", hops="all"),
                         ("A", "B", "C", "D"))

    def test_inward_and_bidirectional_are_distinct(self):
        self.assertEqual(reachable_node_ids(self.graph, "A", hops=1,
                                             direction="in"),
                         ("A", "C", "E"))
        self.assertEqual(reachable_node_ids(self.graph, "A", hops=1,
                                             direction="both"),
                         ("A", "B", "C", "E"))
        self.assertEqual(reachable_node_ids(self.graph, "A", hops="all",
                                             direction="both"),
                         ("A", "B", "C", "D", "E", "F"))

    def test_disconnected_isolated_and_restore_full_scope(self):
        self.assertEqual(reachable_node_ids(self.graph, "Z", hops="all"),
                         ("Z",))
        self.assertEqual(reachable_node_ids(self.graph, None),
                         self.graph.nodes)
        snapshot = repr(self.graph)
        reachable_node_ids(self.graph, "A", hops=5)
        self.assertEqual(repr(self.graph), snapshot)

    def test_invalid_selection_rejected_without_fallback(self):
        for root, hops, direction in (
            ("missing", 2, "out"), ("A", -1, "out"),
            ("A", 11, "out"), ("A", 1.0, "out"),
            ("A", True, "out"), ("A", 2, "sideways"),
        ):
            with self.subTest(root=root, hops=hops, direction=direction):
                with self.assertRaises(GraphInputError):
                    reachable_node_ids(self.graph, root, hops=hops,
                                       direction=direction)


if __name__ == "__main__":
    unittest.main()
