"""Public *sample-only* Vercel entrypoint for the actual Jaal/Dash viewer.

This file is intentionally NOT imported by the local CLI or consumer.
It shares the viewer/core implementation; only fictional, committed CSV
fixtures are exposed. No uploads, private files, database or secrets.
"""
from __future__ import annotations

from pathlib import Path

from flask import jsonify

from jaal_topology import load_graph, select_subgraph
from jaal_topology.viewer import build_app

_ROOT = Path(__file__).resolve().parent
_SOURCE = _ROOT / "examples"

# Same real graph and Dash/visdcc interface used by the standalone CLI.
# select_subgraph applies the normal render bounds; the fixture is 77 / 169.
_graph = select_subgraph(
    load_graph(
        _SOURCE / "company_communications.csv",
        _SOURCE / "company_people.csv",
    ),
    max_nodes=250,
    max_edges=5000,
)
if len(_graph.nodes) != 77 or len(_graph.edges) != 169:
    raise RuntimeError("Public PoC fixture changed; review before deployment")

dash_app = build_app(_graph)
app = dash_app.server  # Flask WSGI entrypoint auto-detected by Vercel.


@app.get("/healthz")
def healthz():
    """Non-sensitive runtime identity and bounded fixture contract."""
    return jsonify(
        status="ok",
        demo="public-fictional-data",
        viewer="jaal-dash-real-runtime",
        modes=5,
        nodes=len(_graph.nodes),
        directed_edges=len(_graph.edges),
    )
