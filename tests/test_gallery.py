"""An opt-in multi-case gallery must isolate each original Jaal callback graph."""
from __future__ import annotations

import json
import unittest

from jaal_topology import Graph, GraphInputError, GalleryCase, create_gallery_app
from jaal_topology.viewer import build_app


def _get_id(component, component_id):
    if isinstance(component, dict):
        props = component.get("props", {})
        if props.get("id") == component_id:
            return component
        for value in component.values():
            found = _get_id(value, component_id)
            if found:
                return found
    if isinstance(component, list):
        for value in component:
            found = _get_id(value, component_id)
            if found:
                return found
    return None


class GalleryContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cycle = Graph(
            edges=(("X", "Y"), ("Y", "X")),
            nodes=("X", "Y"),
            translations={"X": "循環甲", "Y": "循環乙"},
        )
        cls.tree = Graph(
            edges=(("Root", "Team"), ("Team", "Leaf")),
            nodes=("Root", "Team", "Leaf"),
            translations={"Root": "根", "Team": "部門", "Leaf": "職員"},
        )
        cls.dag = Graph(
            edges=(("Start", "Left"), ("Start", "Right"),
                   ("Left", "Shared"), ("Right", "Shared")),
            nodes=("Start", "Left", "Right", "Shared"),
            translations={"Shared": "共用項目"},
        )
        cls.gallery = create_gallery_app([
            GalleryCase("cycle", "寄收件網路", cls.cycle),
            GalleryCase("tree", "組織階層樹", cls.tree,
                        initial_mode="hierarchical-collapsed"),
            GalleryCase("dag", "多父 DAG", cls.dag,
                        initial_mode="hierarchical"),
        ])
        cls.client = cls.gallery.server.test_client()

    def test_case_pages_are_really_separate_dash_apps_on_one_port(self):
        for path in ("/", "/cases/tree/", "/cases/dag/"):
            with self.subTest(path=path):
                page = self.client.get(path)
                self.assertEqual(page.status_code, 200, path)
                self.assertIn(b"_dash-renderer", page.data)
                layout_path = path + "_dash-layout"
                deps_path = path + "_dash-dependencies"
                self.assertEqual(self.client.get(layout_path).status_code, 200)
                self.assertEqual(self.client.get(deps_path).status_code, 200)
                self.assertEqual(
                    self.client.get(path + "assets/16.jaal_visible_labels.js").status_code,
                    200,
                )
        mounted = self.gallery.server._jaal_topology_mounts
        self.assertEqual(set(mounted), {"/cases/tree", "/cases/dag"})
        self.assertIsNot(mounted["/cases/tree"], mounted["/cases/dag"])
        self.assertTrue(any("graph.data" in key
                            for key in mounted["/cases/tree"].callback_map))
        self.assertTrue(any("graph.data" in key
                            for key in mounted["/cases/dag"].callback_map))

    def test_dropdown_matches_current_route_and_modes_reset_per_case(self):
        for path, selected, expected_graph_kind, expected_mode, structural_disabled in [
            ("/", "/", "一般有環網路", "network", True),
            ("/cases/tree/", "/cases/tree/", "樹狀階層", "hierarchical-collapsed", False),
            ("/cases/dag/", "/cases/dag/", "無環 DAG", "hierarchical", False),
        ]:
            with self.subTest(path=path):
                root = self.client.get(path + "_dash-layout").get_json()
                picker = _get_id(root, "jaal-case-picker")
                self.assertIsNotNone(picker)
                self.assertEqual(picker["props"]["value"], selected)
                choices = picker["props"]["options"]
                self.assertEqual([x["value"] for x in choices],
                                 ["/", "/cases/tree/", "/cases/dag/"])
                profile = _get_id(root, "jaal-original-graph-profile")
                self.assertIn(expected_graph_kind, json.dumps(profile, ensure_ascii=False))
                mode = _get_id(root, "jaal-original-layout-mode")
                self.assertEqual(mode["props"]["value"], expected_mode)
                structural = [x for x in mode["props"]["options"]
                              if x["value"] == "hierarchical-collapsed"][0]
                self.assertEqual(bool(structural.get("disabled", False)),
                                 structural_disabled)
                self.assertIsNotNone(_get_id(root, "jaal-case-location"))
        self.assertIn("jaal-case-location.href", self.gallery.callback_map)

    def test_temporal_case_on_nonroot_route_keeps_other_cases_untouched(self):
        # The public demo currently uses a timeline only at '/', but the
        # reusable gallery must support a time-aware case in ANY slot.
        from jaal_topology.email_simulation import EmailEvent
        from jaal_topology.temporal import TemporalTimeline

        timeline = TemporalTimeline(self.cycle, (
            EmailEvent("m1", "2026-10-05T09:00", "thread",
                       "X", "Y", "team-routine", "hello"),
            EmailEvent("m2", "2026-10-06T10:00", "thread",
                       "Y", "X", "team-routine", "reply", reply_to="m1"),
        ))
        gallery = create_gallery_app([
            GalleryCase("tree", "Non-temporal root", self.tree,
                        initial_mode="hierarchical"),
            GalleryCase("timed", "Temporal child", self.cycle,
                        initial_mode="network-community-collapsed",
                        temporal_timeline=timeline),
            GalleryCase("dag", "Non-temporal DAG", self.dag),
        ])
        client = gallery.server.test_client()

        for route, has_timeline in (
            ("/", False),
            ("/cases/timed/", True),
            ("/cases/dag/", False),
        ):
            with self.subTest(route=route):
                layout_response = client.get(route + "_dash-layout")
                self.assertEqual(layout_response.status_code, 200)
                payload = layout_response.get_json()
                frames = _get_id(payload, "jaal-temporal-frames")
                self.assertEqual(frames is not None, has_timeline)
                self.assertEqual(
                    _get_id(payload, "jaal-temporal-controls") is not None,
                    has_timeline,
                )
                self.assertEqual(
                    _get_id(payload, "jaal-case-picker")["props"]["value"],
                    route,
                )
                deps = client.get(route + "_dash-dependencies")
                self.assertEqual(deps.status_code, 200)
                self.assertEqual(
                    "jaal-temporal-" in json.dumps(deps.get_json()),
                    has_timeline,
                )
                if has_timeline:
                    packet = frames["props"]["data"]
                    self.assertEqual(len(packet["frames"]), 1)
                    self.assertEqual(packet["frames"][0]["messages"], 2)
                    self.assertEqual(
                        packet["frames"][0]["edges"],
                        [["X", "Y", 1], ["Y", "X", 1]],
                    )
                    self.assertEqual(client.get(
                        route + "assets/21.jaal_temporal_playback.js"
                    ).status_code, 200)
        mounted = gallery.server._jaal_topology_mounts
        self.assertEqual(set(mounted), {"/cases/timed", "/cases/dag"})
        self.assertIsNot(mounted["/cases/timed"], mounted["/cases/dag"])
        # A timeline is bound to its own graph, never shared across cases.
        with self.assertRaisesRegex(GraphInputError, "must match this Graph"):
            create_gallery_app([
                GalleryCase("bad", "Unrelated", self.tree,
                            temporal_timeline=timeline),
            ])

    def test_original_single_graph_ui_is_unchanged(self):
        independent = build_app(self.tree)
        payload = independent.server.test_client().get("/_dash-layout").get_json()
        self.assertIsNone(_get_id(payload, "jaal-case-picker"))
        self.assertIsNone(_get_id(payload, "jaal-case-location"))
        self.assertEqual(
            _get_id(payload, "jaal-original-layout-mode")["props"]["value"],
            "network",
        )

    def test_reject_unsafe_case_keys_duplicates_and_invalid_modes(self):
        with self.assertRaises(GraphInputError):
            create_gallery_app([])
        with self.assertRaises(GraphInputError):
            create_gallery_app([GalleryCase("../other", "Bad", self.tree)])
        with self.assertRaises(GraphInputError):
            create_gallery_app([GalleryCase("ok", "One", self.tree),
                                GalleryCase("ok", "Two", self.tree)])
        with self.assertRaises(GraphInputError):
            create_gallery_app([GalleryCase("one", "One", self.tree)],
                                    route_prefix="/../../secret")
        with self.assertRaises(GraphInputError):
            create_gallery_app([GalleryCase("cycle", "Cyclic", self.cycle,
                                           initial_mode="hierarchical-collapsed")])


if __name__ == "__main__":
    unittest.main()
