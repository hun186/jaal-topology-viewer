"""Optional same-origin WSGI integration, with no second socket."""
from __future__ import annotations

from werkzeug.middleware.dispatcher import DispatcherMiddleware

from .data import Graph, GraphInputError


def mount_flask(flask_server, graph: Graph, *,
                mount_path="/jaal-topology", root=None,
                case_options=None, current_case_path=None,
                initial_mode="network", case_description="",
                case_resources=(), temporal_timeline=None):
    """Mount a standalone Jaal app under an existing Flask host.

    Call before the Flask server accepts requests. Returns the child Dash
    application. This is optional; the package CLI launches directly.

    Example:
        child = mount_flask(app.server, selected, mount_path="/topology")
        # <iframe src="/topology/"></iframe>
    """
    if (not isinstance(mount_path, str) or
            not mount_path.startswith("/") or
            mount_path == "/" or mount_path.endswith("/") or
            "//" in mount_path):
        raise GraphInputError(
            "mount_path must be an absolute path like '/topology' with no trailing slash"
        )
    registry = getattr(flask_server, "_jaal_topology_mounts", None)
    if registry is None:
        registry = {}
        flask_server._jaal_topology_mounts = registry
    if mount_path in registry:
        raise GraphInputError(
            f"Jaal topology is already mounted at {mount_path!r}"
        )
    from .viewer import build_app
    child = build_app(
        graph, root=root, requests_pathname_prefix=mount_path + "/",
        case_options=case_options, current_case_path=current_case_path,
        initial_mode=initial_mode, case_description=case_description,
        case_resources=case_resources, temporal_timeline=temporal_timeline,
    )
    flask_server.wsgi_app = DispatcherMiddleware(
        flask_server.wsgi_app, {mount_path: child.server}
    )
    registry[mount_path] = child
    return child
