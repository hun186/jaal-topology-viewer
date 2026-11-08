"""Reusable read-only gallery of independently mounted Jaal/Dash graphs.

Each case owns one full Jaal callback graph. Navigation performs a standard
same-origin page load instead of swapping only visdcc data while leaving the
original Jaal Search/Filter/Color/Size closures bound to a previous graph.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Sequence

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
    description: str = ""
    resources: tuple[tuple[str, str], ...] = ()
    temporal_timeline: object | None = None
    allow_large_demo: bool = False
    initial_positions: dict[str, tuple[float, float]] | None = None


@dataclass(frozen=True)
class DeferredGalleryCase:
    """Allowlisted route whose complete genuine Jaal app builds on FIRST visit.

    The route is known upfront for the original case picker; graph creation,
    Louvain and temporal frames remain deferred until the user selects it.
    """
    key: str
    title: str
    factory: Callable[[], GalleryCase]


class _DeferredWSGI:
    def __init__(self, factory, key, title, path, options):
        from threading import Lock
        self.factory, self.key, self.title = factory, key, title
        self.path, self.options = path, options
        self._lock = Lock()
        self.application = None

    def __call__(self, environ, start_response):
        if self.application is None:
            with self._lock:
                if self.application is None:
                    case = self.factory()
                    if (not isinstance(case, GalleryCase) or
                            (case.key, case.title) != (self.key, self.title) or
                            not isinstance(case.graph, Graph)):
                        raise GraphInputError("Deferred factory returned wrong case")
                    from .viewer import build_app
                    dash_app = build_app(
                        case.graph, root=case.root,
                        requests_pathname_prefix=self.path + "/",
                        case_options=self.options,
                        current_case_path=self.path + "/",
                        initial_mode=case.initial_mode,
                        case_description=case.description,
                        case_resources=case.resources,
                        temporal_timeline=case.temporal_timeline,
                        allow_large_demo=case.allow_large_demo,
                        initial_positions=case.initial_positions,
                    )
                    self.application = dash_app.server.wsgi_app
        return self.application(environ, start_response)



def create_gallery_app(
    cases: Sequence[GalleryCase | DeferredGalleryCase], *, route_prefix: str = "/cases",
):
    """Build a self-contained Flask/Dash case-picker on one port.

    The first case is shown at '/', preserving the existing entrypoint.
    Other cases use /cases/<slug>/ by default. Custom graph cases may be
    provided by downstream Python callers; no file uploads or scanning.
    Eager cases are constructed on startup. Explicit deferred cases are
    constructed at first visit and cached for later HTTP requests.

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
        if not isinstance(case, (GalleryCase, DeferredGalleryCase)):
            raise GraphInputError("Gallery entry needs Graph or deferred factory.")
        if isinstance(case, DeferredGalleryCase) and not callable(case.factory):
            raise GraphInputError("Deferred case needs a fixed Python factory.")
        if not isinstance(case.key, str) or not _SLUG.fullmatch(case.key):
            raise GraphInputError("Case keys must be ASCII lowercase URL slugs.")
        if case.key in used:
            raise GraphInputError(f"Duplicate gallery case key {case.key!r}.")
        used.add(case.key)
        if not isinstance(case.title, str) or not 1 <= len(case.title.strip()) <= 100:
            raise GraphInputError("Each case needs a nonempty title (max 100 chars).")
        if isinstance(case, GalleryCase):
            if not isinstance(case.graph, Graph):
                raise GraphInputError("Gallery cases must contain a loaded Graph.")
            if case.temporal_timeline is not None:
                from .temporal import TemporalTimeline
                if not isinstance(case.temporal_timeline, TemporalTimeline):
                    raise GraphInputError("Gallery timeline must be a TemporalTimeline")
            if not isinstance(case.description, str) or len(case.description) > 900:
                raise GraphInputError("Gallery case description must be at most 900 chars.")
            if not isinstance(case.resources, tuple) or len(case.resources) > 5:
                raise GraphInputError("Gallery resources must be a short tuple.")
            for resource in case.resources:
                if (not isinstance(resource, tuple) or len(resource) != 2
                        or not isinstance(resource[0], str)
                        or not isinstance(resource[1], str)
                        or not 1 <= len(resource[0]) <= 80
                        or not re.fullmatch(r"/[a-z0-9][a-z0-9/_.-]*[a-z0-9]", resource[1])
                        or ".." in resource[1] or "//" in resource[1]):
                    raise GraphInputError("Gallery resource URLs must be safe local paths.")

    paths = ["/"] + [
        route_prefix + "/" + case.key + "/" for case in cases[1:]
    ]
    options = [
        {"label": case.title, "value": path}
        for case, path in zip(cases, paths)
    ]
    first = cases[0]
    if not isinstance(first, GalleryCase):
        raise GraphInputError("First Gallery case must be eagerly loaded")
    root_app = build_app(
        first.graph, root=first.root, initial_mode=first.initial_mode,
        case_options=options, current_case_path=paths[0],
        case_description=first.description, case_resources=first.resources,
        temporal_timeline=first.temporal_timeline,
        allow_large_demo=first.allow_large_demo,
        initial_positions=first.initial_positions,
    )
    for case, path in zip(cases[1:], paths[1:]):
        if isinstance(case, DeferredGalleryCase):
            # Under the SAME Flask/port and original Dash/Jaal callback engine.
            # No on-demand data is mounted in Vercel unless explicitly opted in.
            from werkzeug.middleware.dispatcher import DispatcherMiddleware
            mount_path = path.rstrip("/")
            lazy = _DeferredWSGI(case.factory, case.key, case.title,
                                 mount_path, options)
            root_app.server.wsgi_app = DispatcherMiddleware(
                root_app.server.wsgi_app, {mount_path: lazy})
            registry = getattr(root_app.server, "_jaal_topology_mounts", None)
            if registry is None:
                registry = {}
                root_app.server._jaal_topology_mounts = registry
            registry[mount_path] = lazy
        else:
            mount_flask(
                root_app.server, case.graph, root=case.root,
                mount_path=path.rstrip("/"),
                case_options=options, current_case_path=path,
                initial_mode=case.initial_mode,
                case_description=case.description, case_resources=case.resources,
                temporal_timeline=case.temporal_timeline,
                allow_large_demo=case.allow_large_demo,
                initial_positions=case.initial_positions,
            )
    # Opt-in browser-local workbench is separated from preloaded Dash cases.
    from .browser_cases import register_browser_case_workspace
    register_browser_case_workspace(root_app.server)
    from .stress_lab import register_stress_lab
    register_stress_lab(root_app.server)
    return root_app
