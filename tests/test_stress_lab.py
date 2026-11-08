"""GET-only static synthetic Canvas lab alongside the real Jaal gallery."""
from __future__ import annotations

import unittest


class StressLabRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import app
        cls.client = app.test_client()

    def test_read_only_csp_and_allowed_assets(self):
        home = self.client.get("/stress-lab/")
        self.assertEqual(home.status_code, 200)
        self.assertIn(b"scale_core.js", home.data)
        self.assertIn(b"scale_ui.js", home.data)
        self.assertIn("connect-src 'none'",
                      home.headers["Content-Security-Policy"])
        self.assertEqual(home.headers.get("X-Content-Type-Options"), "nosniff")
        for name in ("scale_core.js", "scale_ui.js", "scale.css"):
            response = self.client.get("/stress-lab/" + name)
            self.assertEqual(response.status_code, 200, name)
            self.assertTrue(response.data)
            self.assertEqual(response.headers.get("Cache-Control"), "no-store")
            self.assertIn("connect-src 'none'",
                          response.headers["Content-Security-Policy"])
        self.assertEqual(self.client.get("/stress-lab/secret").status_code, 404)
        self.assertEqual(self.client.get("/stress-lab/index.html").status_code, 404)
        for route in ("/stress-lab/", "/stress-lab/scale_core.js"):
            self.assertEqual(self.client.post(route, data=b"private").status_code, 405)

    def test_gallery_keeps_all_original_cases_and_links_to_lab(self):
        from app import _CASES
        self.assertEqual(len(_CASES), 4)
        layout = self.client.get("/_dash-layout")
        self.assertEqual(layout.status_code, 200)
        self.assertNotIn("/stress-lab/", layout.get_data(as_text=True))
        self.assertIn("jaal-case-picker", layout.get_data(as_text=True))
        self.assertEqual(self.client.get("/healthz").status_code, 200)

    def test_packaged_static_files_present(self):
        from jaal_topology.stress_lab import _DIR
        for file in ("index.html", "scale_core.js", "scale_ui.js", "scale.css"):
            self.assertTrue((_DIR / file).is_file(), file)


if __name__ == "__main__":
    unittest.main()
