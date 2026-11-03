"""Source-level acceptance for the deployed genuine Dash/Jaal WSGI entrypoint."""
from __future__ import annotations

import json
import unittest


class VercelJaalRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import app, dash_app, _graph

        cls.app = app
        cls.dash_app = dash_app
        cls.graph = _graph
        cls.client = app.test_client()

    def test_real_dash_server_and_original_five_modes(self):
        page = self.client.get("/")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"_dash-renderer", page.data)

        layout = self.client.get("/_dash-layout")
        self.assertEqual(layout.status_code, 200)
        payload = layout.get_json()
        self.assertIsInstance(payload, dict)
        serialized = json.dumps(payload, ensure_ascii=False)
        for mode in (
            "network", "network-collapsed", "network-community-collapsed",
            "hierarchical", "hierarchical-collapsed",
        ):
            self.assertIn(f'"value": "{mode}"', serialized)
        self.assertIn("jaal-focus-toggle", serialized)
        self.assertIn("jaal-viewer-root", serialized)
        self.assertIn("jaal-sidebar-toggle", serialized)
        self.assertIn("jaal-original-help-details", serialized)
        self.assertIn("jaal-original-app-shell", serialized)
        self.assertIn("jaal-original-chinese-labels", serialized)
        self.assertIn("search_graph", serialized)

        callbacks = self.client.get("/_dash-dependencies")
        self.assertEqual(callbacks.status_code, 200)
        self.assertTrue(callbacks.get_json())
        self.assertTrue(self.dash_app.callback_map)

    def test_original_jaal_assets_and_only_synthetic_data(self):
        self.assertEqual(len(self.graph.nodes), 77)
        self.assertEqual(len(self.graph.edges), 169)
        for name in (
            "16.jaal_visible_labels.js",
            "17.jaal_structural_collapse.js",
            "18.jaal_community_collapse.js",
            "bootstrap.min.css",
            "19.jaal_compact_layout.css",
            "20.jaal_focus_escape.js",
        ):
            result = self.client.get("/assets/" + name)
            self.assertEqual(result.status_code, 200, name)
            self.assertTrue(result.data, name)
        health = self.client.get("/healthz")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(
            health.get_json(),
            {
                "status": "ok", "demo": "public-fictional-data",
                "viewer": "jaal-dash-real-runtime",
                "modes": 5, "nodes": 77, "directed_edges": 169,
            },
        )

    def test_public_gallery_cases_use_real_dash_routes_and_distinct_graphs(self):
        from app import _CASES, _tree, _dag

        self.assertEqual(len(_CASES), 3)
        self.assertEqual((len(_tree.nodes), len(_tree.edges)), (52, 51))
        self.assertEqual((len(_dag.nodes), len(_dag.edges)), (19, 31))
        for path, case_label, expected_mode, expected_count in (
            ("/", "公司寄收件網路（一般有環）", "network", 77),
            ("/cases/org-tree/", "公司組織階層樹（無環）",
             "hierarchical-collapsed", 52),
            ("/cases/project-dag/", "專案相依網路（多父 DAG）",
             "hierarchical", 19),
        ):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)
                result = self.client.get(path + "_dash-layout")
                self.assertEqual(result.status_code, 200)
                payload = json.dumps(result.get_json(), ensure_ascii=False)
                self.assertIn(case_label, payload)
                self.assertIn('"value": "' + expected_mode + '"', payload)
                self.assertIn('"id": "jaal-case-picker"', payload)
                self.assertIn('"id": "jaal-case-location"', payload)
                self.assertIn('"id": "graph"', payload)
                self.assertIn('"nodes": [', payload)
                self.assertEqual(
                    self.client.get(path + "assets/16.jaal_visible_labels.js").status_code,
                    200,
                )
        self.assertIs(self.app._jaal_topology_mounts["/cases/org-tree"].server.wsgi_app
                      is not None, True)

    def test_vercel_configuration_never_automatically_builds_prs(self):
        from pathlib import Path

        cfg = json.loads(
            (Path(__file__).parents[1] / "vercel.json").read_text("utf-8")
        )
        self.assertIs(cfg["git"]["deploymentEnabled"], False)
        self.assertEqual(cfg["framework"], "flask")
        self.assertNotIn("outputDirectory", cfg)
        self.assertNotIn("buildCommand", cfg)
        self.assertIn("jaal_topology/assets", cfg["functions"]["app.py"]["includeFiles"])


if __name__ == "__main__":
    unittest.main()
