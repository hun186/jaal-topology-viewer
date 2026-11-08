"""Public gallery opt-in, strict browser-only local case routes and privacy headers."""
from __future__ import annotations

import json
import unittest

from jaal_topology import Graph, GalleryCase, create_gallery_app


class BrowserCaseWorkspaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        graph = Graph(edges=(("A", "B"),), nodes=("A", "B"), translations={})
        cls.gallery = create_gallery_app([GalleryCase("only", "Demo", graph)])
        cls.client = cls.gallery.server.test_client()

    def test_gallery_has_a_visible_local_case_link_without_changing_dash_graph(self):
        layout = self.client.get("/_dash-layout")
        self.assertEqual(layout.status_code, 200)
        payload = json.dumps(layout.get_json(), ensure_ascii=False)
        self.assertIn("＋ 我的案例／上傳 CSV", payload)
        self.assertIn("/my-cases/", payload)
        self.assertIn('"id": "graph"', payload)
        self.assertEqual(self.client.get("/_dash-dependencies").status_code, 200)

    def test_route_serves_real_static_workspace_with_strict_privacy_boundary(self):
        page = self.client.get("/my-cases/")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"IndexedDB", page.data)
        self.assertIn(b"case_core.js", page.data)
        self.assertIn(b"case_ui.js", page.data)
        self.assertIn("text/html", page.content_type)
        self.assertEqual(page.headers["Cache-Control"], "no-store")
        self.assertIn("connect-src 'none'", page.headers["Content-Security-Policy"])
        self.assertIn("script-src 'self'", page.headers["Content-Security-Policy"])
        for asset, mime in (("case_core.js", "javascript"),
                            ("case_ui.js", "javascript"),
                            ("cases.css", "text/css")):
            response = self.client.get("/my-cases/" + asset)
            self.assertEqual(response.status_code, 200, asset)
            self.assertIn(mime, response.content_type)
            self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(self.client.post("/my-cases/", data={"file": "secret"}).status_code, 405)
        self.assertEqual(self.client.post("/my-cases/case_ui.js").status_code, 405)
        self.assertEqual(self.client.get("/my-cases/.env").status_code, 404)
        self.assertEqual(self.client.get("/my-cases/index.html").status_code, 404)
        self.assertEqual(self.client.get("/my-cases/unknown.js").status_code, 404)
        self.assertEqual(self.client.get("/_dash-layout").status_code, 200)


if __name__ == "__main__":
    unittest.main()
