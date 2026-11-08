"""True full-Jaal scale demos, five presets and opt-in deferred routing."""
from __future__ import annotations

import unittest

from jaal_topology.data import GraphInputError
from jaal_topology.scaled_demo import (
    SCALES, build_scaled_email_demo, component_sizes,
)


class FullJaalSyntheticScaleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scenarios = {k: build_scaled_email_demo(k) for k in SCALES}

    def test_precise_nodes_real_edges_components_and_hierarchy(self):
        for key,(nodes,parts) in SCALES.items():
            with self.subTest(key=key):
                model=self.scenarios[key]
                graph=model.graph
                self.assertEqual(len(graph.nodes),nodes)
                self.assertEqual(set(graph.edges),set(graph.edge_counts))
                self.assertEqual(len(graph.edges),len(set(graph.edges)))
                self.assertLess(len(graph.edges),50_000)
                self.assertEqual(len(model.events),len(graph.edges))
                self.assertEqual(len(model.positions),nodes)
                self.assertGreater(model.departments,0)
                self.assertGreaterEqual(model.depth,5)
                self.assertEqual(component_sizes(graph),model.components)
                self.assertEqual(len(model.components),parts)
                self.assertEqual(sum(model.components),nodes)
                self.assertEqual(len(set(graph.nodes)),nodes)
                self.assertTrue(all(a!=b for a,b in graph.edges))
                for node in graph.nodes:
                    self.assertIn(node,graph.translations)
                self.assertEqual(len(set(event.id for event in model.events)),
                                 len(model.events))
                self.assertEqual(
                    {(m.sender,m.recipient) for m in model.events},
                    set(graph.edges))

    def test_three_real_islands_have_no_cross_company_edges(self):
        model=self.scenarios["three-components"]
        self.assertEqual(model.components,(167,167,166))
        for a,b in model.graph.edges:
            self.assertEqual(a[:3],b[:3],"Cross-island edge must never exist")
        self.assertGreater(model.positions["C02-N00001"][0],
                           model.positions["C01-N00001"][0])

    def test_determinism_and_invalid_scale_rejection(self):
        a=self.scenarios["500"]
        b=build_scaled_email_demo("500")
        self.assertEqual(a.graph,b.graph)
        self.assertEqual(a.events,b.events)
        self.assertEqual(a.positions,b.positions)
        with self.assertRaises(GraphInputError):
            build_scaled_email_demo("50000")
        with self.assertRaises(GraphInputError):
            build_scaled_email_demo(True)

    def test_original_caps_are_not_silently_raised(self):
        from jaal_topology.community import detect_louvain
        from jaal_topology.temporal import TemporalTimeline
        from jaal_topology.viewer import build_app
        huge=self.scenarios["5000"]
        with self.assertRaises(GraphInputError):
            detect_louvain(huge.graph)
        with self.assertRaises(GraphInputError):
            TemporalTimeline(huge.graph,huge.events)
        with self.assertRaises(GraphInputError):
            build_app(huge.graph)

    def test_real_jaal_viewer_for_500_and_three_islands(self):
        from jaal_topology.temporal import TemporalTimeline
        from jaal_topology.viewer import build_app
        import json
        for key in ("500","three-components"):
            with self.subTest(key=key):
                model=self.scenarios[key]
                timeline=TemporalTimeline(model.graph,model.events,
                                          allow_large_demo=True)
                viewer=build_app(
                    model.graph,initial_mode="network-community-collapsed",
                    temporal_timeline=timeline,allow_large_demo=True,
                    initial_positions=model.positions)
                client=viewer.server.test_client()
                layout=client.get("/_dash-layout")
                self.assertEqual(layout.status_code,200)
                data=json.dumps(layout.get_json(),ensure_ascii=False)
                self.assertIn("jaal-original-layout-mode",data)
                self.assertIn("jaal-temporal-controls",data)
                self.assertIn("jaal-local-root",data)
                self.assertIn("network-community-collapsed",data)
                self.assertIn("search_graph",data)
                self.assertIn("graph",data)
                self.assertIn("jaal-community-membership",data)
                self.assertEqual(client.get("/_dash-dependencies").status_code,200)

    def test_deferred_case_initializes_only_when_first_visited(self):
        import json
        from jaal_topology.gallery import (
            DeferredGalleryCase,GalleryCase,create_gallery_app,
        )
        from jaal_topology.temporal import TemporalTimeline
        small=self.scenarios["500"]
        count=[]
        def factory():
            count.append(1)
            return GalleryCase("scaled","原版 Jaal｜500 人",small.graph,
                               temporal_timeline=TemporalTimeline(
                                   small.graph,small.events,
                                   allow_large_demo=True),
                               initial_positions=small.positions,
                               allow_large_demo=True)
        root=build_scaled_email_demo("500")
        app=create_gallery_app([
            GalleryCase("base","Existing graph",root.graph),
            DeferredGalleryCase("scaled","原版 Jaal｜500 人",factory),
        ])
        client=app.server.test_client()
        self.assertEqual(count,[])
        home=client.get("/_dash-layout")
        self.assertEqual(home.status_code,200)
        # Dash escapes / in raw JSON. Inspect parsed option values instead.
        def picker_options(node):
            if isinstance(node,dict):
                if node.get("props",{}).get("id")=="jaal-case-picker":
                    return node["props"]["options"]
                for child in node.values():
                    found=picker_options(child)
                    if found is not None: return found
            elif isinstance(node,list):
                for child in node:
                    found=picker_options(child)
                    if found is not None: return found
            return None
        options=picker_options(home.get_json())
        self.assertIsNotNone(options)
        self.assertIn("/cases/scaled/",[o["value"] for o in options])
        self.assertEqual(count,[])
        self.assertEqual(client.get("/cases/scaled/_dash-layout").status_code,200)
        self.assertEqual(count,[1])
        self.assertEqual(client.get("/cases/scaled/_dash-dependencies").status_code,200)
        self.assertEqual(count,[1])
        with self.assertRaises(GraphInputError):
            create_gallery_app([DeferredGalleryCase("a","a",factory)])


if __name__=="__main__":
    unittest.main()
