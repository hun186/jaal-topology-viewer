"""Same-origin static UI for large fictional corporate email graphs.

Dataset generation and Canvas rendering happen in the client's browser. No
server upload, source file access, API endpoint or stateful backend is needed.
This view does not change the original Jaal/Dash rendering limits.
"""
from pathlib import Path

_DIR = Path(__file__).resolve().parent / "stress_lab"
_ASSETS = {
    "index.html": "text/html; charset=utf-8",
    "scale_core.js": "text/javascript; charset=utf-8",
    "scale_ui.js": "text/javascript; charset=utf-8",
    "scale.css": "text/css; charset=utf-8",
}
_CSP = (
    "default-src 'none'; script-src 'self'; style-src 'self'; "
    "img-src 'self'; connect-src 'none'; object-src 'none'; "
    "base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
)


def register_stress_lab(flask_server):
    from flask import Response, abort

    def serve(filename):
        if filename not in _ASSETS:
            abort(404)
        result = Response((_DIR / filename).read_bytes(),
                          content_type=_ASSETS[filename])
        result.headers["Content-Security-Policy"] = _CSP
        result.headers["X-Content-Type-Options"] = "nosniff"
        result.headers["Cache-Control"] = "no-store"
        return result

    @flask_server.get("/stress-lab/", endpoint="jaal_stress_lab_home")
    def home():
        return serve("index.html")

    @flask_server.get("/stress-lab/<filename>", endpoint="jaal_stress_lab_asset")
    def asset(filename):
        if filename == "index.html":
            abort(404)
        return serve(filename)
