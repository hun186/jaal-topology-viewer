"""Source-level acceptance for the deployed genuine Dash/Jaal WSGI entrypoint."""
from __future__ import annotations

import json
import unittest


class VercelJaalRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import app, dash_app, _graph, _email, _simulation

        cls.app = app
        cls.dash_app = dash_app
        cls.graph = _graph
        cls.email_graph = _email
        cls.simulation = _simulation
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
        self.assertIn("jaal-focus-panel-toggle", serialized)
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

    def test_focus_panel_density_toggles_without_replacing_graph(self):
        """The root Dash callback changes only CSS and button labels."""
        callback = next(
            config["callback"].__wrapped__
            for key, config in self.dash_app.callback_map.items()
            if "jaal-viewer-root.className" in key
            and "jaal-focus-panel-toggle.children" in key
        )
        normal = callback(0, 0)
        full = callback(1, 0)
        compact = callback(1, 1)
        restored = callback(1, 2)
        out = callback(2, 1)
        self.assertEqual(normal[0], "jaal-viewer-shell")
        self.assertEqual(full[0], "jaal-viewer-shell jaal-focus-mode")
        self.assertEqual(compact[0],
                         "jaal-viewer-shell jaal-focus-mode jaal-focus-compact")
        self.assertEqual(compact[3:], ("完整面板", "true"))
        self.assertEqual(restored[3:], ("精簡資訊", "false"))
        self.assertEqual(out[0], "jaal-viewer-shell")
        self.assertEqual(self.client.get("/_dash-layout").status_code, 200)

    def test_scale_lab_public_assets_are_allowed_only_for_reading(self):
        for path in ("/stress-lab/", "/stress-lab/scale_core.js",
                     "/stress-lab/scale_ui.js", "/stress-lab/scale.css"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
            self.assertIn("connect-src 'none'",
                          response.headers["Content-Security-Policy"])
            self.assertEqual(self.client.post(path).status_code, 405)
        self.assertEqual(self.client.get("/stress-lab/not-allowed").status_code, 404)

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
            "21.jaal_temporal_playback.js",
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
                "modes": 5,
                "nodes": len(self.email_graph.nodes),
                "directed_edges": len(self.email_graph.edges),
            },
        )

    def test_public_gallery_cases_use_real_dash_routes_and_distinct_graphs(self):
        from app import _CASES, _tree, _dag

        self.assertEqual(len(_CASES), 4)
        self.assertEqual((len(_tree.nodes), len(_tree.edges)), (52, 51))
        self.assertEqual((len(_dag.nodes), len(_dag.edges)), (19, 31))
        for path, case_label, expected_mode, expected_count in (
            ("/", "企業郵件實務模擬（業務與事件）",
             "network-community-collapsed", len(self.email_graph.nodes)),
            ("/cases/mail-network/", "舊版通訊拓樸（類別樹改編）",
             "network", 77),
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

    def test_email_event_downloads_are_read_only_and_consistent(self):
        import csv
        import io

        client = self.client
        events = client.get("/demo/mail-events.csv")
        edges = client.get("/demo/mail-edges.csv")
        summary = client.get("/demo/mail-summary")
        self.assertEqual(events.status_code, 200)
        self.assertEqual(edges.status_code, 200)
        self.assertEqual(summary.status_code, 200)
        self.assertEqual(client.post("/demo/mail-events.csv").status_code, 405)
        rows = list(csv.DictReader(io.StringIO(events.get_data(as_text=True))))
        aggregated = list(csv.DictReader(io.StringIO(edges.get_data(as_text=True))))
        self.assertEqual(len(rows), len(self.simulation.events))
        self.assertEqual(len(aggregated), len(self.email_graph.edges))
        self.assertEqual(sum(int(r["message_count"]) for r in aggregated), len(rows))
        payload = summary.get_json()
        self.assertEqual(payload["status"], "fictional-simulation")
        self.assertEqual(payload["events"], len(rows))
        self.assertEqual(payload["directed_pairs"], len(aggregated))
        self.assertEqual(payload["work_days"], 20)
        self.assertGreater(payload["replies"], 100)
        layout = client.get("/_dash-layout").get_json()
        serialized = json.dumps(layout, ensure_ascii=False)
        self.assertIn("下載模擬郵件事件 CSV", serialized)
        self.assertIn("本案例以合成郵件收發量加權", serialized)
        self.assertIn("企業郵件實務模擬（業務與事件）", serialized)

    def test_temporal_controls_and_callbacks_exist_only_on_event_case(self):
        from app import _timeline

        layout = self.client.get("/_dash-layout").get_json()
        serialized = json.dumps(layout, ensure_ascii=False)
        for control in (
            "jaal-temporal-controls", "jaal-temporal-range",
            "jaal-temporal-mode", "jaal-temporal-window",
            "jaal-temporal-step", "jaal-temporal-speed",
            "jaal-temporal-play", "jaal-temporal-back",
            "jaal-temporal-forward", "jaal-temporal-loop",
            "jaal-temporal-index", "jaal-temporal-status",
            "jaal-temporal-frames", "jaal-temporal-frame",
            "jaal-temporal-labels", "jaal-temporal-community-policy",
        ):
            self.assertIn(control, serialized)
        self.assertGreater(len(_timeline.days), 20)
        self.assertLessEqual(len(_timeline.days), 31)
        self.assertEqual(self.client.get(
            "/assets/21.jaal_temporal_playback.js").status_code, 200)
        callbacks = self.client.get("/_dash-dependencies").get_json()
        self.assertTrue(any("jaal-temporal" in str(item)
                            for item in callbacks))
        for path in ("/cases/mail-network/", "/cases/org-tree/",
                     "/cases/project-dag/"):
            child_layout = self.client.get(path + "_dash-layout").get_json()
            self.assertNotIn("jaal-temporal-controls",
                             json.dumps(child_layout))

    def test_precise_start_and_end_fields_synchronize_analysis_range(self):
        from types import SimpleNamespace
        from dash._callback_context import context_value
        from dash import no_update
        handler = next(
            config["callback"].__wrapped__
            for key, config in self.dash_app.callback_map.items()
            if "jaal-temporal-start-text.value" in key
            and "jaal-temporal-end-text.value" in key
            and "jaal-temporal-range.value" in key
        )
        from app import _timeline
        from datetime import datetime, time, timedelta
        origin = datetime.combine(_timeline.first_day, time.min)
        start = origin.isoformat(timespec="minutes")
        end = (origin + timedelta(hours=12)).isoformat(timespec="minutes")
        def invoke(prop, bounds, first, last):
            token = context_value.set(SimpleNamespace(
                triggered_inputs=[{"prop_id": prop, "value": None}]
            ))
            try:
                return handler(bounds, first, last)
            finally:
                context_value.reset(token)
        new_bounds, first_out, last_out = invoke(
            "jaal-temporal-start-text.value", [0,1440], start, end,
        )
        self.assertEqual(new_bounds, [0, 720])
        self.assertIs(first_out, no_update)
        self.assertIs(last_out, no_update)
        bounds_out, first_text, last_text = invoke(
            "jaal-temporal-range.value", [60,120], start, end,
        )
        self.assertIs(bounds_out, no_update)
        self.assertTrue(first_text.endswith("01:00"))
        self.assertTrue(last_text.endswith("02:00"))

    def test_root_picker_supports_search_and_induced_local_neighborhood(self):
        from app import _timeline
        payload = self.client.get("/_dash-layout").get_json()
        serialized = json.dumps(payload)
        for component in ("jaal-local-root", "jaal-local-hops",
                          "jaal-local-direction", "jaal-local-status",
                          "jaal-local-scope"):
            self.assertIn(component, serialized)
        self.assertEqual(self.client.get(
            "/assets/22.jaal_local_focus.js").status_code, 200)
        callback = next(
            config["callback"].__wrapped__
            for key, config in self.dash_app.callback_map.items()
            if "jaal-local-scope.data" in key
            and "jaal-local-status.children" in key
        )
        node = _timeline.graph.nodes[0]
        before = repr(_timeline.graph)
        packet, label = callback(node, 0, "out")
        self.assertEqual(packet["root"], node)
        self.assertEqual(packet["ids"], [node])
        self.assertIn("1 節點、0 有向邊", label)
        whole, whole_status = callback(None, 2, "both")
        self.assertEqual(whole, {"root": None})
        self.assertIn("全圖", whole_status)
        invalid, status = callback("UNKNOWN_NODE", 2, "out")
        self.assertEqual(invalid["root"], None)
        self.assertIn("無效", status)
        self.assertEqual(repr(_timeline.graph), before)

    def test_temporal_layout_changes_do_not_restart_physics(self):
        # Exercise the real registered Dash callback using Dash's own
        # request-local context variable, not a mocked product implementation.
        from types import SimpleNamespace
        from dash._callback_context import context_value

        callback = next(
            config["callback"].__wrapped__
            for key, config in self.dash_app.callback_map.items()
            if "graph.options" in key
            and "jaal-original-physics-restore.disabled" in key
        )

        def invoke(mode, triggered, ticks=0):
            token = context_value.set(SimpleNamespace(
                triggered_inputs=[{"prop_id": triggered, "value": None}]
            ))
            try:
                return callback(mode, ticks, 0)
            finally:
                context_value.reset(token)

        length_control = self.client.get("/_dash-layout").get_json()
        self.assertIn("jaal-original-edge-length", json.dumps(length_control))
        for mode in ("network", "network-community-collapsed", "hierarchical"):
            with self.subTest(mode=mode):
                options, _disabled = invoke(
                    mode, "jaal-original-layout-mode.value"
                )
                self.assertIs(options["physics"]["enabled"], False)

        length_options, unchanged = invoke("network", "jaal-original-edge-length.value")
        self.assertIn("length", length_options["edges"])
        self.assertEqual(length_options["edges"]["length"], 120)
        self.assertIs(length_options["physics"]["enabled"], False)
        self.assertEqual(length_options["physics"]["barnesHut"]["springLength"], 120)
        restored, disabled = invoke(
            "network", "jaal-original-physics-restore.n_intervals", ticks=1
        )
        self.assertIs(restored["physics"]["enabled"], False)
        self.assertTrue(disabled)

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
