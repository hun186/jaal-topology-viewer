"""Static, local-only CSV case workspace served beside the read-only Dash gallery.

The Python server never receives, parses, stores or logs uploaded case bytes.
All browser file access, rendering and IndexedDB persistence stay client-side.
"""
from __future__ import annotations

from pathlib import Path

_DIR = Path(__file__).resolve().parent / "browser_cases"
_ALLOWED = {
    "index.html": "text/html; charset=utf-8",
    "case_core.js": "text/javascript; charset=utf-8",
    "case_ui.js": "text/javascript; charset=utf-8",
    "cases.css": "text/css; charset=utf-8",
}
_CSP = (
    "default-src 'none'; script-src 'self'; style-src 'self'; "
    "img-src 'self' data:; connect-src 'none'; object-src 'none'; "
    "base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
)


def register_browser_case_workspace(flask_server):
    """Register a same-origin /my-cases/ route, without accepting POST or files."""
    from flask import Response, abort

    @flask_server.get("/my-cases/", endpoint="jaal_browser_cases_home")
    def home():
        return serve("index.html")

    @flask_server.get("/my-cases/<filename>", endpoint="jaal_browser_cases_asset")
    def asset(filename):
        if filename == "index.html" or filename not in _ALLOWED:
            abort(404)
        return serve(filename)

    def serve(filename):
        if filename not in _ALLOWED:
            abort(404)
        path = _DIR / filename  # Fixed allowlist; never a caller-supplied path.
        response = Response(path.read_bytes(), content_type=_ALLOWED[filename])
        response.headers["Content-Security-Policy"] = _CSP
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response
