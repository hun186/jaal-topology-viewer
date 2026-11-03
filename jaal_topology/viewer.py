"""Standalone Jaal rendering; independent of Stage 4 and taxonomy utilities.

Uses Jaal's real Search/Filter/Color/Size Dash app. Enriches the graph
with optional display-language and network/hierarchy controls. The full
Stage-4-only collapse animation remains a separate migration milestone.
"""
from __future__ import annotations

from copy import deepcopy
from html import escape as escape_html
from collections import defaultdict, deque

from .data import Graph, assess_structural_collapse


def _depths(graph: Graph, root=None):
    adj = defaultdict(list)
    indegree = defaultdict(int)
    for parent, child in graph.edges:
        adj[parent].append(child)
        indegree[child] += 1
    seeds = [root] if root is not None else [
        name for name in graph.nodes if indegree[name] == 0
    ]
    # Disconnected cycles have no zero-indegree root.
    queue = deque((seed, 0) for seed in seeds)
    depths = {}
    while queue:
        name, level = queue.popleft()
        if name in depths:
            continue
        depths[name] = level
        for child in adj.get(name, ()):
            queue.append((child, level + 1))
    for name in graph.nodes:
        if name not in depths:
            queue = deque([(name, 0)])
            while queue:
                node, level = queue.popleft()
                if node in depths:
                    continue
                depths[node] = level
                for child in adj.get(node, ()):
                    queue.append((child, level + 1))
    return depths


def to_jaal_dataframes(graph: Graph, *, root=None):
    """Adapt any two-column directed graph to original Jaal DataFrame columns."""
    import pandas as pd

    depths = _depths(graph, root=root)
    incoming = defaultdict(int)
    outgoing = defaultdict(int)
    for parent, child in graph.edges:
        incoming[child] += 1
        outgoing[parent] += 1
    nodes = pd.DataFrame([
        {
            "id": name,
            "label": name,
            "title": escape_html(name, quote=True),
            "depth": depths[name],
            "InDegree": incoming[name],
            "OutDegree": outgoing[name],
            "Degree": incoming[name] + outgoing[name],
        } for name in graph.nodes
    ])
    edges = pd.DataFrame([
        {"from": parent, "to": child, "strength": "medium"}
        for parent, child in graph.edges
    ], columns=["from", "to", "strength"])
    return edges, nodes


def _search_english_id(graph_data, search_text):
    needle = (search_text or "").casefold()
    for node in graph_data["nodes"]:
        node["hidden"] = needle not in str(node["id"]).casefold()
    return graph_data


def _descendants(component):
    pending = [component]
    while pending:
        item = pending.pop()
        yield item
        children = getattr(item, "children", None)
        if isinstance(children, (list, tuple)):
            pending.extend(children)
        elif children is not None and not isinstance(children, (str, int, float)):
            pending.append(children)


def _normalize_upstream_layout(layout):
    """Normalize upstream Jaal layout and tag its original panel and canvas columns."""
    from dash import html
    import dash_bootstrap_components as dbc

    for item in _descendants(layout):
        if isinstance(item, html.Img) and isinstance(
            getattr(item, "src", None), str
        ) and item.src.startswith("data:image/png;base64,"):
            if item.width == "80px":
                item.width = 48
                item.style = {**(getattr(item, "style", None) or {}),
                              "width": "48px", "maxWidth": "100%",
                              "height": "auto"}
                break
    if isinstance(layout, html.Div):
        children = layout.children
        if isinstance(children, (list, tuple)):
            for row in children:
                if isinstance(row, dbc.Row):
                    classes = (getattr(row, "className", None) or "").split()
                    if "g-0" not in classes:
                        row.className = " ".join([*classes, "g-0"])

    # Retain upstream component IDs and callbacks. Only tag their existing
    # Bootstrap columns for a reversible, CSS-driven responsive layout.
    panel_found = graph_found = False
    for item in _descendants(layout):
        if isinstance(item, dbc.Row) and any(
            isinstance(child, html.Img)
            and isinstance(getattr(child, "src", None), str)
            and child.src.startswith("data:image/png;base64,")
            for child in _descendants(item)
        ):
            item.className = " ".join(filter(None, [
                getattr(item, "className", "") or "", "jaal-brand-row"
            ]))
        if not isinstance(item, dbc.Col):
            continue
        ids = {getattr(child, "id", None) for child in _descendants(item)}
        if "search_graph" in ids:
            item.className = " ".join(filter(None, [
                getattr(item, "className", "") or "", "jaal-settings-col"
            ]))
            panel_found = True
        elif "graph" in ids:
            item.className = " ".join(filter(None, [
                getattr(item, "className", "") or "", "jaal-graph-col"
            ]))
            graph_found = True
    if not (panel_found and graph_found):
        raise RuntimeError("Upstream Jaal panel/graph column contract changed")


def build_app(graph: Graph, *, root=None, requests_pathname_prefix="/"):
    """Build an independent localhost-ready Dash Jaal app, including community mode.

    The original Jaal Search/Filter/Color/Size callbacks are preserved.
    JavaScript is installed from THIS package, not from the calling project.
    """
    from .data import GraphInputError
    from .modes import layout_options
    from .community import detect_louvain
    from . import ASSETS_DIR

    prefix = requests_pathname_prefix
    if (not isinstance(prefix, str) or
            not prefix.startswith("/") or not prefix.endswith("/") or
            "//" in prefix):
        raise GraphInputError(
            "requests_pathname_prefix must be an absolute slash-terminated path"
        )
    if not graph.edges:
        raise GraphInputError(
            "Jaal requires at least one visible directed edge; "
            "select a parent/ancestor rather than an isolated leaf"
        )
    if len(graph.nodes) > 3000 or len(graph.edges) > 5000:
        raise GraphInputError(
            "Graph must be bounded before Jaal app construction"
        )

    from dash import (
        Dash, Input, Output, ClientsideFunction, callback_context,
        dcc, html, no_update,
    )
    from jaal import Jaal

    structure = assess_structural_collapse(graph)
    community_result = detect_louvain(graph)
    community_partition = community_result.member_to_group
    edges, nodes = to_jaal_dataframes(graph, root=root)
    network = Jaal(edges, nodes)
    network._callback_search_graph = _search_english_id
    for collection in (network.data, network.filtered_data):
        for node in collection["nodes"]:
            if node.get("shape") == "dot":
                del node["shape"]
            # visdcc's Popup.setText uses innerHTML for string title values.
            # Escape title, never IDs/labels (canvas labels are plain text).
            # Jaal.parse_dataframe may recompute title after the CSV adapter.
            node["title"] = escape_html(str(node["id"]), quote=True)
        # Jaal's from+"__"+to edge ID collides for arbitrary string IDs.
        for index, edge in enumerate(collection["edges"]):
            edge["id"] = f"jaal-edge-{index}"
            if isinstance(edge.get("title"), str):
                edge["title"] = escape_html(edge["title"], quote=True)

    # Vis Network officially supports percentage heights and autoResize.
    # CSS sets an explicit height on the graph column; the original canvas
    # follows ordinary and viewport-focused layouts without reinitializing.
    original_app = network.create(directed=True, vis_opts={
        "height": "100%",
        "interaction": {"hover": True},
        "physics": {"enabled": True, "stabilization": {"iterations": 100}},
    })
    graph_network = next(
        (item for item in _descendants(original_app.layout)
         if getattr(item, "id", None) == "graph"), None
    )
    if graph_network is None or not isinstance(graph_network.options, dict):
        raise RuntimeError("Original Jaal graph/options layout contract changed")
    base = deepcopy(graph_network.options)
    base.setdefault("nodes", {}).setdefault("shape", "dot")
    graph_network.options = deepcopy(base)
    _normalize_upstream_layout(original_app.layout)

    type_labels = {
        "tree": "樹狀階層（單一起點）",
        "forest": "樹狀森林（多個起點）",
        "dag": "無環 DAG（共享後代／多父節點）",
        "cyclic": "一般有環網路（不適合子樹收攏）",
    }
    # Keep the original mode, language and cycle guard IDs unchanged.
    # The compact top bar stays visible; verbose explanations are available
    # from a native details popup and consume no drawing height by default.
    controls = html.Div([
        html.Button(
            "收合設定 ◀", id="jaal-sidebar-toggle", n_clicks=0,
            className="jaal-sidebar-toggle", title="收合左側 Search / Filter / Color / Size 設定",
            **{"aria-expanded": "true", "aria-controls": "jaal-original-app-shell"},
        ),
        html.Button(
            "全版檢視 ⛶", id="jaal-focus-toggle", n_clicks=0,
            className="jaal-focus-toggle",
            title="拓撲圖佔滿視窗；再按一次退出全版",
            **{"aria-pressed": "false"},
        ),
        html.Span(
            "圖形：" + type_labels[structure.graph_kind],
            id="jaal-original-graph-profile",
            className=("jaal-graph-kind jaal-graph-kind-warning"
                       if structure.has_cycle else "jaal-graph-kind"),
        ),
        html.Div([
            html.Span("顯示模式", className="jaal-mode-caption"),
            dcc.RadioItems(
                id="jaal-original-layout-mode",
                className="jaal-mode-options",
                options=[
                    {"label": "網狀（全展開）", "value": "network"},
                    {"label": "網狀（收攏）", "value": "network-collapsed",
                     "disabled": structure.has_cycle},
                    {"label": "網狀（社群收攏・Louvain）",
                     "value": "network-community-collapsed"},
                    {"label": "階層（全展開）", "value": "hierarchical"},
                    {"label": "階層（收攏）", "value": "hierarchical-collapsed",
                     "disabled": structure.has_cycle},
                ],
                value="network", inline=True,
            ),
        ], className="jaal-mode-group"),
        dcc.Checklist(
            id="jaal-original-chinese-labels",
            className="jaal-language-toggle",
            options=[{"label": "優先顯示中文名稱（無翻譯時顯示英文）",
                      "value": "zh"}],
            value=[], inline=True,
        ),
        html.Details([
            html.Summary("圖形說明", title="查看圖形結構與收攏規則"),
            html.Div([
                html.Div(
                    ("原始圖無環，但 Louvain 社群彙總後產生循環；不代表分類父子關係有環。"
                     if not structure.has_cycle and community_result.quotient_has_cycle else
                     "原始圖含有向迴路，社群彙總圖也有循環。"
                     if structure.has_cycle and community_result.quotient_has_cycle else
                     "社群彙總圖無循環；原始關係與社群彙總屬不同層級。"),
                    id="jaal-original-community-cycle-hint",
                ),
                html.Div(
                    ("已檢測到有向迴路：子樹收攏會把循環可達的節點誤當階層後代，故停用網狀／階層的「收攏」選項；請改用網狀（社群收攏・Louvain）。"
                     if structure.has_cycle else
                     f"這是無環有向圖，但有 {structure.multi_parent_nodes} 個多父節點；子樹收攏計算的是可達的不同節點，不一定是獨占的下屬。"
                     if structure.multi_parent_nodes else
                     "子樹收攏：點節點逐層展開。")
                    + " 社群收攏：點社群展開、點成員收合；分群依連線拓樸，不代表職級。",
                    id="jaal-original-structural-hint",
                ),
            ], className="jaal-context-popup"),
        ], id="jaal-original-help-details", className="jaal-context-details"),
        # Stores/interval remain mounted even when user hides the left pane.
        dcc.Store(id="jaal-original-ct-translations",
                  data=graph.translations, storage_type="memory"),
        dcc.Store(id="jaal-community-membership",
                  data=community_partition, storage_type="memory"),
        dcc.Store(id="jaal-structural-eligible",
                  data=not structure.has_cycle, storage_type="memory"),
        dcc.Interval(id="jaal-original-physics-restore",
                     interval=300, disabled=True, n_intervals=0),
    ], id="jaal-compact-toolbar", className="jaal-compact-toolbar")

    # Jaal creates a Dash instance without a configurable asset directory.
    # Construct a correctly configured shell and reuse its actual callbacks,
    # rather than using a separate graph implementation or copying JS from
    # the old application at runtime. The shell serves bundled assets offline.
    app = Dash(
        __name__, assets_folder=str(ASSETS_DIR),
        requests_pathname_prefix=prefix,
        routes_pathname_prefix="/",
        # Original Jaal uses CDN-only Bootstrap; include a locally served
        # MIT-licensed copy so controls retain layout even on an air-gapped PC.
        external_stylesheets=[
            prefix + "assets/bootstrap.min.css",
            *list(original_app.config.external_stylesheets),
        ],
    )
    app.layout = html.Div([
        controls,
        html.Div(original_app.layout, id="jaal-original-app-shell",
                 className="jaal-original-app-shell"),
    ], id="jaal-viewer-root", className="jaal-viewer-shell")
    app.callback_map.update(original_app.callback_map)
    app._callback_list.extend(original_app._callback_list)
    if not app.callback_map or len(app.callback_map) != len(original_app.callback_map):
        raise RuntimeError("Original Jaal callbacks were not preserved")

    @app.callback(
        Output("jaal-viewer-root", "className"),
        Output("jaal-focus-toggle", "children"),
        Output("jaal-focus-toggle", "aria-pressed"),
        Input("jaal-focus-toggle", "n_clicks"),
    )
    def toggle_focus_view(clicks):
        """Overlay a viewport-sized graph without replacing the real visdcc canvas."""
        focused = bool((clicks or 0) % 2)
        return (
            "jaal-viewer-shell jaal-focus-mode"
            if focused else "jaal-viewer-shell",
            "退出全版 ✕" if focused else "全版檢視 ⛶",
            "true" if focused else "false",
        )

    @app.callback(
        Output("jaal-original-app-shell", "className"),
        Output("jaal-sidebar-toggle", "children"),
        Output("jaal-sidebar-toggle", "aria-expanded"),
        Input("jaal-sidebar-toggle", "n_clicks"),
    )
    def toggle_settings_panel(clicks):
        """Expand graph width without unmounting Jaal settings or losing filters."""
        collapsed = bool((clicks or 0) % 2)
        return (
            "jaal-original-app-shell jaal-panel-collapsed"
            if collapsed else "jaal-original-app-shell",
            "顯示設定 ▶" if collapsed else "收合設定 ◀",
            "false" if collapsed else "true",
        )

    @app.callback(
        Output("graph", "options"),
        Output("jaal-original-physics-restore", "disabled"),
        Input("jaal-original-layout-mode", "value"),
        Input("jaal-original-physics-restore", "n_intervals"),
        prevent_initial_call=True,
    )
    def switch_mode(mode, _ticks):
        if structure.has_cycle and mode in ("network-collapsed", "hierarchical-collapsed"):
            raise ValueError("Structural descendant collapse disabled for directed cycles")
        triggered = callback_context.triggered[0]["prop_id"].split(".", 1)[0]
        if triggered == "jaal-original-physics-restore":
            if mode not in ("network", "network-collapsed", "network-community-collapsed"):
                return no_update, True
            reset = layout_options(base, mode)
            physics = base.get("physics", {})
            enabled = physics.get("enabled", True) if isinstance(
                physics, dict
            ) else bool(physics)
            return {
                "physics": {"enabled": enabled},
                "edges": {"smooth": reset["edges"]["smooth"]},
                "nodes": {key: reset["nodes"][key] for key in (
                    "shape", "widthConstraint", "margin", "borderWidth"
                )},
            }, True
        if mode in (
            "network", "network-collapsed", "network-community-collapsed",
            "hierarchical", "hierarchical-collapsed",
        ):
            return layout_options(base, mode), mode.startswith("hierarchical")
        raise ValueError("Unsupported Jaal layout mode")

    app.clientside_callback(
        ClientsideFunction(namespace="jaal_visible_labels",
                           function_name="apply"),
        Output("graph", "run"),
        Input("jaal-original-layout-mode", "value"),
        Input("graph", "data"),
        Input("jaal-original-chinese-labels", "value"),
        Input("jaal-original-ct-translations", "data"),
        Input("jaal-community-membership", "data"),
        Input("jaal-structural-eligible", "data"),
    )
    return app
