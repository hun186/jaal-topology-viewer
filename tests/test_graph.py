"""Tests that run without cloning text-category-profiler."""
from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from jaal_topology import Graph, GraphInputError, load_graph, select_subgraph
from jaal_topology.modes import layout_options


class CSVInterfaceTests(unittest.TestCase):
    def test_examples_load_without_application_files(self):
        examples = Path(__file__).resolve().parents[1] / "examples"
        g = load_graph(examples / "relationships.csv",
                       examples / "metadata.csv")
        self.assertEqual(len(g.nodes), 5)
        self.assertEqual(len(g.edges), 5)
        self.assertEqual(g.translations["Technology"], "科技")
        self.assertEqual(
            select_subgraph(g, "Technology").nodes,
            ("AI", "Semiconductors", "Technology"),
        )
        self.assertEqual(g.edges[0], ("Root", "Technology"))

    def test_empty_translations_are_optional_and_ids_are_literal(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "edges.csv"
            path.write_text('parent,child\nA__B,C\nA,B__C\n',
                            encoding='utf-8')
            graph = load_graph(path)
            self.assertEqual(len(graph.edges), 2)
            self.assertEqual(graph.translations, {})
            with self.assertRaises(GraphInputError):
                select_subgraph(graph, max_nodes=1)


    def test_html_escapes_hover_only_not_literal_identifier(self):
        from jaal_topology.viewer import build_app
        unsafe = '<svg onload="alert(1)">'
        app = build_app(Graph((("Parent", unsafe),), ("Parent", unsafe), {}))
        def find(item):
            if isinstance(item, dict):
                if item.get("props", {}).get("id") == "graph":
                    return item["props"]["data"]["nodes"]
                for v in item.values():
                    found = find(v)
                    if found is not None:
                        return found
            elif isinstance(item, list):
                for v in item:
                    found = find(v)
                    if found is not None:
                        return found
            return None
        nodes = find(app.server.test_client().get("/_dash-layout").get_json())
        node = next(n for n in nodes if n["id"] == unsafe)
        self.assertEqual(node["label"], unsafe)
        self.assertIn("&lt;svg", node["title"])
        self.assertNotIn("<svg", node["title"])

    def test_wsgi_mount_keeps_host_and_assets_on_same_port(self):
        from flask import Flask
        from jaal_topology.integration import mount_flask

        examples = Path(__file__).resolve().parents[1] / "examples"
        graph = select_subgraph(
            load_graph(examples / "relationships.csv",
                       examples / "metadata.csv"), "Technology"
        )
        host = Flask(__name__)
        @host.route("/")
        def root():
            return "host-still-alive"
        child = mount_flask(
            host, graph, mount_path="/topology", root="Technology"
        )
        client = host.test_client()
        self.assertEqual(client.get("/").get_data(as_text=True),
                         "host-still-alive")
        result = client.get("/topology/")
        self.assertEqual(result.status_code, 200)
        self.assertIn("/topology/assets/16.jaal_visible_labels.js",
                      result.get_data(as_text=True))
        self.assertEqual(client.get("/topology/_dash-layout").status_code, 200)
        self.assertEqual(
            client.get("/topology/assets/17.jaal_structural_collapse.js").status_code,
            200,
        )
        self.assertEqual(
            client.get("/topology/assets/bootstrap.min.css").status_code, 200
        )
        with self.assertRaisesRegex(GraphInputError, "already mounted"):
            mount_flask(host, graph, mount_path="/topology")
        self.assertIsNotNone(child)


    def test_company_communications_example_is_directed_non_tree(self):
        examples = Path(__file__).resolve().parents[1] / "examples"
        graph = load_graph(
            examples / "company_communications.csv",
            examples / "company_people.csv",
        )
        self.assertEqual(len(graph.nodes), 77)
        self.assertEqual(len(graph.edges), 169)
        self.assertEqual(len(set(graph.edges)), len(graph.edges))
        self.assertIn("CEO / Executive Office", graph.nodes)
        self.assertEqual(
            graph.translations["CEO / Executive Office"], "執行長／總經理室"
        )
        self.assertTrue(
            any((b, a) in set(graph.edges) for a, b in graph.edges),
            "Realistic emails include reciprocal directed pairs",
        )
        self.assertEqual(len(select_subgraph(graph).edges), 169)
        mapping_file = examples / "company_communications_source_mapping.csv"
        import csv
        with mapping_file.open(encoding="utf-8", newline="") as stream:
            mapping = list(csv.DictReader(stream))
        self.assertEqual(len(mapping), 77)
        self.assertEqual(
            {row["synthetic_sender_id"] for row in mapping}, set(graph.nodes)
        )

    def test_structural_collapse_cycle_gate_and_dag_multi_parent_warning(self):
        from jaal_topology.data import Graph, assess_structural_collapse

        tree = Graph((("A", "B"), ("A", "C")), ("A", "B", "C"))
        forest = Graph((("A", "B"), ("C", "D")), ("A", "B", "C", "D"))
        diamond = Graph(
            (("A", "B"), ("A", "C"), ("B", "D"), ("C", "D")),
            ("A", "B", "C", "D"),
        )
        cycle = Graph((("A", "B"), ("B", "C"), ("C", "B")), ("A", "B", "C"))
        self_loop = Graph((("A", "A"),), ("A",))
        mixed = Graph(
            (("A", "B"), ("C", "D"), ("D", "C")),
            ("A", "B", "C", "D"),
        )
        for graph in (tree, forest, diamond):
            self.assertFalse(assess_structural_collapse(graph).has_cycle)
        self.assertEqual(
            [assess_structural_collapse(x).graph_kind
             for x in (tree, forest, diamond, cycle, self_loop, mixed)],
            ["tree", "forest", "dag", "cyclic", "cyclic", "cyclic"],
        )
        self.assertEqual(assess_structural_collapse(tree).multi_parent_nodes, 0)
        self.assertEqual(assess_structural_collapse(forest).root_count, 2)
        self.assertEqual(assess_structural_collapse(diamond).multi_parent_nodes, 1)
        for graph in (cycle, self_loop, mixed):
            self.assertTrue(assess_structural_collapse(graph).has_cycle)
        self.assertEqual(assess_structural_collapse(cycle).root_count, 1)

    def test_company_demo_serves_full_real_jaal_layout(self):
        """No mock renderer: load the shipped CSV and inspect the Dash app."""
        from jaal_topology.viewer import build_app
        examples = Path(__file__).resolve().parents[1] / "examples"
        graph = select_subgraph(load_graph(
            examples / "company_communications.csv",
            examples / "company_people.csv",
        ))
        app = build_app(graph)
        client = app.server.test_client()
        layout = client.get("/_dash-layout")
        self.assertEqual(layout.status_code, 200)
        self.assertEqual(client.get("/assets/17.jaal_structural_collapse.js").status_code, 200)
        def find(item, node_id):
            if isinstance(item, dict):
                if item.get("props", {}).get("id") == node_id:
                    return item["props"]
                for value in item.values():
                    match = find(value, node_id)
                    if match is not None:
                        return match
            if isinstance(item, list):
                for value in item:
                    match = find(value, node_id)
                    if match is not None:
                        return match
            return None
        graph_data = find(layout.get_json(), "graph")["data"]
        self.assertEqual(len(graph_data["nodes"]), 77)
        self.assertEqual(len(graph_data["edges"]), 169)
        self.assertEqual(
            find(layout.get_json(), "jaal-original-layout-mode")["value"],
            "network",
        )
        modes = {
            option["value"]: option
            for option in find(layout.get_json(), "jaal-original-layout-mode")["options"]
        }
        self.assertIs(
            find(layout.get_json(), "jaal-structural-eligible")["data"], False
        )
        self.assertTrue(modes["network-collapsed"]["disabled"])
        self.assertTrue(modes["hierarchical-collapsed"]["disabled"])
        self.assertFalse(modes["network"].get("disabled", False))
        self.assertFalse(modes["network-community-collapsed"].get("disabled", False))
        self.assertIn(
            "已檢測到有向迴路",
            find(layout.get_json(), "jaal-original-structural-hint")["children"],
        )
        self.assertIn(
            "一般有環網路",
            find(layout.get_json(), "jaal-original-graph-profile")["children"],
        )
        self.assertIn(
            "社群彙總圖",
            find(layout.get_json(), "jaal-original-community-cycle-hint")["children"],
        )


    def test_all_four_options_have_bounded_reversible_styles(self):
        base = {"nodes": {"shape": "dot"},
                "physics": {"enabled": True},
                "edges": {"smooth": {"enabled": True, "type": "dynamic"}}}
        for mode in ("network", "hierarchical",
                     "network-collapsed", "hierarchical-collapsed"):
            result = layout_options(base, mode)
            self.assertIsInstance(result, dict)
            self.assertIn("physics", result)
            self.assertEqual(base["nodes"]["shape"], "dot")
        hierarchical = layout_options(base, "hierarchical-collapsed")
        self.assertTrue(hierarchical["layout"]["hierarchical"]["enabled"])
        network = layout_options(base, "network")
        self.assertFalse(network["layout"]["hierarchical"]["enabled"])
        community_options = layout_options(base, "network-community-collapsed")
        self.assertFalse(community_options["layout"]["hierarchical"]["enabled"])
        self.assertEqual(base["nodes"]["shape"], "dot")
