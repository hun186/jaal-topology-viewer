"""Reusable read-only gallery of independently mounted Jaal/Dash graphs.

Each case owns one full Jaal callback graph. Navigation performs a standard
same-origin page load instead of swapping only visdcc data while leaving the
original Jaal Search/Filter/Color/Size closures bound to a previous graph.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

from .data import Graph, GraphInputError

_SLUG = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")


@dataclass(frozen=True)
class GalleryCase:
    """One bounded, already-loaded graph and its public display metadata."""

    key: str
    title: str
    graph: Graph
    root: str | None = None
    initial_mode: str = "network"


def create_gallery_app(
    cases: Sequence[GalleryCase], *, route_prefix: str = "/cases",
):
    """Build a self-contained Flask/Dash case-picker on one port.

    The first case is shown at '/', preserving the existing entrypoint.
    Other cases use /cases/<slug>/ by default. Custom graph cases may be
    provided by downstream Python callers; no file uploads or scanning.
    Each case is constructed once during startup, not per HTTP request.

    Returns the root Dash instance. Its '.server' is the WSGI/Flask host.
    """
    from .viewer import build_app
    from .integration import mount_flask

    if not isinstance(cases, (list, tuple)) or not 1 <= len(cases) <= 20:
        raise GraphInputError("Gallery needs 1..20 explicit graph cases.")
    if not isinstance(route_prefix, str) or not re.fullmatch(
        r"/[a-z][a-z0-9]*(?:/[a-z][a-z0-9]*)*", route_prefix
    ):
        raise GraphInputError("route_prefix must be a fixed absolute lowercase path.")

    used = set()
    for case in cases:
        if not isinstance(case, GalleryCase):
            raise GraphInputError("All gallery entries must be GalleryCase values.")
        if not isinstance(case.key, str) or not _SLUG.fullmatch(case.key):
            raise GraphInputError("Case keys must be ASCII lowercase URL slugs.")
        if case.key in used:
            raise GraphInputError(f"Duplicate gallery case key {case.key!r}.")
        used.add(case.key)
        if not isinstance(case.title, str) or not 1 <= len(case.title.strip()) <= 100:
            raise GraphInputError("Each case needs a nonempty title (max 100 chars).")
        if not isinstance(case.graph, Graph):
            raise GraphInputError("Gallery cases must contain a loaded Graph.")

    paths = ["/"] + [
        route_prefix + "/" + case.key + "/" for case in cases[1:]
    ]
    options = [
        {"label": case.title, "value": path}
        for case, path in zip(cases, paths)
    ]
    first = cases[0]
    root_app = build_app(
        first.graph, root=first.root, initial_mode=first.initial_mode,
        case_options=options, current_case_path=paths[0],
    )
    for case, path in zip(cases[1:], paths[1:]):
        mount_flask(
            root_app.server, case.graph, root=case.root,
            mount_path=path.rstrip("/"),
            case_options=options, current_case_path=path,
            initial_mode=case.initial_mode,
        )
    return root_app
