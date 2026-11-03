"""Public sample-only Vercel entrypoint for the actual Jaal/Dash gallery.

Only explicitly committed fictional CSV fixtures are loaded on startup.
Case switching uses separate same-origin Jaal apps and preserves their
original per-case Search/Filter/Color/Size callbacks and cycle guard.
No user file upload, environment secrets, database, or external graph data.
"""
from __future__ import annotations

from pathlib import Path

from flask import jsonify

from jaal_topology import load_graph, select_subgraph
from jaal_topology.gallery import GalleryCase, create_gallery_app

_ROOT = Path(__file__).resolve().parent
_SOURCE = _ROOT / "examples"


def _sample(edges: str, labels: str, expected_nodes: int, expected_edges: int):
    """Fail closed if a public fixture is edited without reviewing its contract."""
    graph = select_subgraph(
        load_graph(_SOURCE / edges, _SOURCE / labels),
        max_nodes=250, max_edges=5000,
    )
    if (len(graph.nodes), len(graph.edges)) != (expected_nodes, expected_edges):
        raise RuntimeError(f"Unexpected fictional PoC fixture: {edges}")
    return graph


_graph = _sample("company_communications.csv", "company_people.csv", 77, 169)
_tree = _sample("org_tree.csv", "org_tree_labels.csv", 52, 51)
_dag = _sample("project_dag.csv", "project_dag_labels.csv", 19, 31)

# The root '/' still opens the original communications example by default.
# Two additional cases are mounted under /cases/<slug>/ on the SAME WSGI port.
# No input path is taken from the browser; all cases are an allowlist.
_CASES = (
    GalleryCase("mail-network", "公司寄收件網路（一般有環）", _graph),
    GalleryCase("org-tree", "公司組織階層樹（無環）", _tree,
                initial_mode="hierarchical-collapsed"),
    GalleryCase("project-dag", "專案相依網路（多父 DAG）", _dag,
                initial_mode="hierarchical"),
)
dash_app = create_gallery_app(_CASES)
app = dash_app.server  # Flask WSGI entrypoint auto-detected by Vercel.


@app.get("/healthz")
def healthz():
    """Keep the previous non-sensitive default-case health contract stable."""
    return jsonify(
        status="ok",
        demo="public-fictional-data",
        viewer="jaal-dash-real-runtime",
        modes=5,
        nodes=len(_graph.nodes),
        directed_edges=len(_graph.edges),
    )
