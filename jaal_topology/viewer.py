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
    sent_messages = defaultdict(int)
    received_messages = defaultdict(int)
    edge_set = set(graph.edges)
    for parent, child in graph.edges:
        incoming[child] += 1
        outgoing[parent] += 1
    if graph.edge_counts:
        if set(graph.edge_counts) != edge_set:
            raise ValueError("Weighted email graph needs a count for every directed edge.")
        for (sender, recipient), count in graph.edge_counts.items():
            if type(count) is not int or count < 1 or count > 1_000_000:
                raise ValueError("Email counts must be positive bounded integers.")
            sent_messages[sender] += count
            received_messages[recipient] += count
    nodes = pd.DataFrame([
        {
            "id": name,
            "label": name,
            "title": escape_html(name, quote=True),
            "depth": depths[name],
            "InDegree": incoming[name],
            "OutDegree": outgoing[name],
            "Degree": incoming[name] + outgoing[name],
            **({
                "SentEmails": sent_messages[name],
                "ReceivedEmails": received_messages[name],
                "TotalEmails": sent_messages[name] + received_messages[name],
            } if graph.edge_counts else {}),
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


def build_app(graph: Graph, *, root=None, requests_pathname_prefix="/",
              case_options=None, current_case_path=None,
              initial_mode="network", case_description="",
              case_resources=(), temporal_timeline=None):
    """Build a localhost-ready Dash Jaal app; optional isolated case navigation.

    Original Jaal Search/Filter/Color/Size callbacks remain intact. Each
    gallery case is its own Dash app; switching pages reloads the target case
    rather than attaching stale callbacks to another graph's data.
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
        Dash, Input, Output, State, ClientsideFunction, callback_context,
        dcc, html, no_update,
    )
    from jaal import Jaal

    structure = assess_structural_collapse(graph)
    if initial_mode not in (
        "network", "network-collapsed", "network-community-collapsed",
        "hierarchical", "hierarchical-collapsed",
    ):
        raise GraphInputError("Unsupported initial gallery layout mode.")
    if structure.has_cycle and initial_mode in (
        "network-collapsed", "hierarchical-collapsed",
    ):
        raise GraphInputError("Cannot start a cyclic gallery case in structural collapse.")
    if (case_options is None) != (current_case_path is None):
        raise GraphInputError("Case navigation needs both choices and current case path.")
    if case_options is not None:
        if (not isinstance(case_options, (list, tuple))
                or not case_options
                or not isinstance(current_case_path, str)
                or current_case_path not in {
                    opt.get("value") for opt in case_options
                    if isinstance(opt, dict) and isinstance(opt.get("value"), str)
                }):
            raise GraphInputError("Invalid case navigation options or selected path.")
    if not isinstance(case_description, str) or len(case_description) > 900:
        raise GraphInputError("Case description must be a short string.")
    if not isinstance(case_resources, tuple):
        raise GraphInputError("Case resources must be a tuple of local links.")
    # Time-aware playback is opt-in and must represent precisely this same
    # graph. The ordinary CSV/Graph API and all existing Jaal Dash callbacks
    # remain unchanged for non-temporal callers.
    temporal_frames = None
    if temporal_timeline is not None:
        from .temporal import TemporalTimeline

        if not isinstance(temporal_timeline, TemporalTimeline):
            raise GraphInputError("temporal_timeline must be a TemporalTimeline")
        source = temporal_timeline.graph
        if (tuple(graph.edges) != tuple(source.edges)
                or set(graph.nodes) != set(source.nodes)
                or graph.edge_counts != source.edge_counts):
            raise GraphInputError("Temporal event source must match this Graph")
        temporal_frames = temporal_timeline.interval_frames(
            mode="rolling", window_minutes=3*1440, step_minutes=3*1440,
        )
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
            if graph.edge_counts:
                directed_pair = (str(edge["from"]), str(edge["to"]))
                count = graph.edge_counts[directed_pair]
                # Explicit edge width and tooltip carry actual *synthetic*
                # mail-event volume; Jaal's default "strength" is categorical
                # and must not be mistaken for raw number of emails.
                import math
                edge["width"] = round(min(8.0, 1.0 + math.log2(count + 1)), 2)
                edge["mailCount"] = count
                edge["title"] = f"合成郵件：{count} 封（統計期間 20 個工作日）"
            if isinstance(edge.get("title"), str):
                edge["title"] = escape_html(edge["title"], quote=True)

    # visdcc adds its own intermediate wrapper, so '100%' can shrink to
    # ~150px even when Bootstrap's graph column is viewport-sized. Use a
    # viewport CSS length on the actual vis-network frame instead.
    original_app = network.create(directed=True, vis_opts={
        "height": "calc(100dvh - 150px)",
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
    graph_network.options = (
        deepcopy(base) if initial_mode == "network"
        else layout_options(base, initial_mode)
    )
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
    controls_children = [
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
                value=initial_mode, inline=True,
            ),
        ], className="jaal-mode-group"),
        html.Details([
            html.Summary("調整邊長", title="調整非時間圖的彈簧長度或時間圖固定座標的間距"),
            html.Div([
                html.Span("基礎邊長／間距（60–300 px）"),
                dcc.Slider(
                    id="jaal-original-edge-length", min=60, max=300, step=20,
                    value=120, marks={60:"短", 120:"標準", 300:"長"},
                    tooltip={"placement":"bottom", "always_visible":False},
                ),
            ], className="jaal-edge-length-control"),
        ], className="jaal-edge-length-details"),
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
                *([html.Div([
                    html.Strong("業務情境與可驗證資料"),
                    html.P(case_description, className="jaal-case-description"),
                    html.Div([
                        html.A(label, href=url, target="_blank",
                               rel="noopener noreferrer")
                        for label, url in case_resources
                    ], className="jaal-case-resources"),
                ])] if case_description or case_resources else []),
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
                    + (" 社群收攏：點社群展開、點成員收合；本案例以合成郵件收發量加權 Louvain，不代表組織職級；社群間邊數仍是不同寄收件對數，不是郵件總封數。"
                       if graph.edge_counts else
                       " 社群收攏：點社群展開、點成員收合；分群依連線拓樸，不代表職級。"),
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
    ]
    if temporal_frames is not None:
        from datetime import datetime, time, timedelta, timezone
        days = temporal_timeline.days
        total_minutes = len(days) * 1440
        first_instant = datetime.combine(
            days[0], time.min,
            tzinfo=timezone.utc if temporal_timeline.timezone == "UTC" else None,
        )
        last_instant = first_instant + timedelta(minutes=total_minutes)
        date_marks = {
            i * 1440: day.strftime("%m/%d")
            for i, day in enumerate(days)
            if i == 0 or day.weekday() == 0
        }
        date_marks[total_minutes] = last_instant.strftime("%m/%d")
        controls_children.append(html.Div([
            html.Div([
                html.Strong("時間演化", className="jaal-temporal-heading"),
                dcc.RadioItems(
                    id="jaal-temporal-mode",
                    options=[
                        {"label": "累積至目前", "value": "cumulative"},
                        {"label": "滑動時間窗", "value": "rolling"},
                    ],
                    value="rolling", inline=True,
                    className="jaal-temporal-modes",
                ),
                html.Span("時間單位"),
                dcc.Dropdown(
                    id="jaal-temporal-unit",
                    options=[
                        {"label": "1 分鐘", "value": 1},
                        {"label": "10 分鐘", "value": 10},
                        {"label": "1 小時", "value": 60},
                        {"label": "3 小時", "value": 180},
                        {"label": "1 天", "value": 1440},
                    ], value=1440, clearable=False, searchable=False,
                    className="jaal-temporal-select",
                ),
                html.Span("區間長度"),
                dcc.Dropdown(
                    id="jaal-temporal-window",
                    options=[{"label": f"{n} 單位", "value": n}
                             for n in (1, 2, 3, 6, 12, 24, 30)],
                    value=3, clearable=False, searchable=False,
                    className="jaal-temporal-select",
                ),
                dcc.RadioItems(
                    id="jaal-temporal-overlap",
                    options=[
                        {"label": "互斥分段（步長＝窗長）", "value": "disjoint"},
                        {"label": "重疊滑窗（自訂步長）", "value": "overlap"},
                    ], value="disjoint", inline=True,
                    className="jaal-temporal-modes",
                ),
                html.Span("社群演化"),
                dcc.RadioItems(
                    id="jaal-temporal-community-policy",
                    options=[
                        {"label": "固定社群（比較流量）", "value": "fixed"},
                        {"label": "逐格重分群（實驗）", "value": "dynamic"},
                    ], value="fixed", inline=True,
                ),
                dcc.Checklist(
                    id="jaal-temporal-labels",
                    options=[{"label": "顯示全部節點名稱（較擁擠）", "value": "all"}],
                    value=[], inline=True,
                ),
                html.Span("重疊時步長"),
                dcc.Dropdown(
                    id="jaal-temporal-step",
                    options=[{"label": f"{n} 單位", "value": n}
                             for n in (1, 2, 3, 6, 12, 24)],
                    value=1, clearable=False, searchable=False,
                    className="jaal-temporal-select",
                ),
                html.Span("速度"),
                dcc.Dropdown(
                    id="jaal-temporal-speed",
                    options=[
                        {"label": "快", "value": 350},
                        {"label": "標準", "value": 700},
                        {"label": "慢", "value": 1400},
                        {"label": "極慢", "value": 2500},
                    ], value=700, clearable=False, searchable=False,
                    className="jaal-temporal-select",
                ),
                dcc.Checklist(
                    id="jaal-temporal-loop",
                    options=[{"label": "循環", "value": "loop"}],
                    value=["loop"], inline=True,
                ),
            ], className="jaal-temporal-options"),
            html.Div([
                html.Span("分析範圍（兩端皆可拖曳）"),
                html.Div(
                    dcc.RangeSlider(
                        id="jaal-temporal-range", min=0, max=total_minutes,
                        step=1440, marks=date_marks, value=[0, total_minutes],
                        allowCross=False, updatemode="mouseup",
                    ), className="jaal-temporal-range",
                ),
                html.Span("起點"),
                dcc.Input(
                    id="jaal-temporal-start-text", type="text", debounce=True,
                    value=first_instant.isoformat(timespec="minutes"),
                    className="jaal-temporal-date-input",
                    placeholder="YYYY-MM-DDTHH:MM",
                ),
                html.Span("終點（不含）"),
                dcc.Input(
                    id="jaal-temporal-end-text", type="text", debounce=True,
                    value=last_instant.isoformat(timespec="minutes"),
                    className="jaal-temporal-date-input",
                    placeholder="YYYY-MM-DDTHH:MM",
                ),
                html.Button("◀", id="jaal-temporal-back", n_clicks=0,
                            title="後退一個時間步長"),
                html.Button("▶ 播放", id="jaal-temporal-play", n_clicks=0),
                html.Button("▶", id="jaal-temporal-forward", n_clicks=0,
                            title="前進一個時間步長"),
                html.Span("播放進度"),
                html.Div(
                    dcc.Slider(
                        id="jaal-temporal-index", min=0,
                        max=temporal_frames["end_index"], step=1,
                        marks={0:"開始", temporal_frames["end_index"]:"結束"},
                        value=temporal_frames["end_index"], updatemode="mouseup",
                    ), className="jaal-temporal-playhead",
                ),
            ], className="jaal-temporal-navigation"),
            html.Div([
                html.Span("目前播放時窗（藍條隨時間移動，右端不含）"),
                html.Div(
                    html.Div(
                        id="jaal-temporal-window-highlight",
                        className="jaal-temporal-window-highlight",
                        style={
                            "left": f"{temporal_frames['frames'][-1]['axis_start'] * 100}%",
                            "width": f"{(temporal_frames['frames'][-1]['axis_end'] - temporal_frames['frames'][-1]['axis_start']) * 100}%",
                        },
                    ),
                    className="jaal-temporal-window-axis",
                ),
            ], className="jaal-temporal-live-window"),
            html.Div(
                f"互斥分段｜[{temporal_frames['frames'][-1]['from']}, "
                f"{temporal_frames['frames'][-1]['to']})　"
                f"{temporal_frames['frames'][-1]['messages']} 封信",
                id="jaal-temporal-status", className="jaal-temporal-status",
                role="status",
            ),
            dcc.Store(id="jaal-temporal-frames", data=temporal_frames,
                      storage_type="memory"),
            dcc.Store(
                id="jaal-temporal-frame",
                data=temporal_frames["frames"][-1], storage_type="memory",
            ),
            dcc.Interval(
                id="jaal-temporal-tick", interval=700, n_intervals=0,
                disabled=True,
            ),
        ], id="jaal-temporal-controls", className="jaal-temporal-controls"))
    if case_options is not None:
        # A normal URL change deliberately creates a clean Dash instance per
        # graph. Using graph.data alone would leave upstream Jaal callbacks
        # searching/filtering a different, previously loaded graph.
        controls_children.insert(0, html.Div([
            html.Span("示範案例", className="jaal-case-caption"),
            dcc.Dropdown(
                id="jaal-case-picker", options=case_options,
                value=current_case_path, clearable=False, searchable=True,
                className="jaal-case-picker",
            ),
            dcc.Location(id="jaal-case-location", refresh=True),
        ], className="jaal-case-selector"))
    controls = html.Div(
        controls_children, id="jaal-compact-toolbar",
        className="jaal-compact-toolbar",
    )

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

    if case_options is not None:
        from dash.exceptions import PreventUpdate

        allowed_paths = frozenset(option["value"] for option in case_options)

        @app.callback(
            Output("jaal-case-location", "href"),
            Input("jaal-case-picker", "value"),
            prevent_initial_call=True,
        )
        def change_gallery_case(selected_path):
            if selected_path not in allowed_paths or selected_path == current_case_path:
                raise PreventUpdate
            return selected_path

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
        Input("jaal-focus-toggle", "n_clicks"),
        Input("jaal-original-edge-length", "value"),
        prevent_initial_call=True,
    )
    def switch_mode(mode, _ticks, focus_clicks, edge_length=120):
        if structure.has_cycle and mode in ("network-collapsed", "hierarchical-collapsed"):
            raise ValueError("Structural descendant collapse disabled for directed cycles")
        triggered = callback_context.triggered[0]["prop_id"].split(".", 1)[0]
        focused = bool((focus_clicks or 0) % 2)
        # Update the *real* vis-network frame height when focus changes.
        # This is a partial options update: all Louvain/graph data and
        # current mode remain mounted; no second renderer is created.
        if triggered == "jaal-focus-toggle":
            return {"height": "100dvh" if focused else base["height"]}, no_update
        if triggered == "jaal-original-edge-length":
            if type(edge_length) is not int or not 60 <= edge_length <= 300:
                return no_update, no_update
            physics_enabled = (temporal_frames is None and
                               not mode.startswith("hierarchical"))
            return ({"edges": {"length": edge_length},
                     "physics": {"enabled": physics_enabled,
                                 "barnesHut": {"springLength": edge_length}}},
                    no_update)
        if triggered == "jaal-original-physics-restore":
            if mode not in ("network", "network-collapsed", "network-community-collapsed"):
                return no_update, True
            reset = layout_options(base, mode)
            physics = base.get("physics", {})
            enabled = physics.get("enabled", True) if isinstance(
                physics, dict
            ) else bool(physics)
            return {
                # Timeline playback keeps a stable node universe and camera.
                # Never restart physics in its delayed layout-restore tick.
                # Ordinary non-temporal Jaal viewers retain legacy behavior.
                "physics": {"enabled": enabled and temporal_frames is None},
                "edges": {"smooth": reset["edges"]["smooth"]},
                "nodes": {key: reset["nodes"][key] for key in (
                    "shape", "widthConstraint", "margin", "borderWidth"
                )},
            }, True
        if mode in (
            "network", "network-collapsed", "network-community-collapsed",
            "hierarchical", "hierarchical-collapsed",
        ):
            options = layout_options(base, mode)
            if temporal_frames is not None:
                # Switching hierarchy/network otherwise re-enables vis physics
                # after the clientside first-frame lock (including on resume).
                # Keep temporal positions steady in all five layout modes.
                options["physics"] = {"enabled": False}
            if focused:
                options["height"] = "100dvh"
            return options, mode.startswith("hierarchical")
        raise ValueError("Unsupported Jaal layout mode")

    if temporal_frames is not None:
        from dash.exceptions import PreventUpdate

        @app.callback(
            Output("jaal-temporal-range", "value"),
            Output("jaal-temporal-start-text", "value"),
            Output("jaal-temporal-end-text", "value"),
            Input("jaal-temporal-range", "value"),
            Input("jaal-temporal-start-text", "value"),
            Input("jaal-temporal-end-text", "value"),
            prevent_initial_call=True,
        )
        def sync_analysis_bounds(bounds, start_text, end_text):
            from datetime import datetime, timedelta
            if (not isinstance(bounds, list) or len(bounds) != 2
                    or not all(type(n) is int for n in bounds)):
                raise PreventUpdate
            triggered = callback_context.triggered[0]["prop_id"].split(".", 1)[0]
            if triggered == "jaal-temporal-range":
                return (
                    no_update,
                    (first_instant + timedelta(minutes=bounds[0])).isoformat(timespec="minutes"),
                    (first_instant + timedelta(minutes=bounds[1])).isoformat(timespec="minutes"),
                )
            if triggered not in ("jaal-temporal-start-text", "jaal-temporal-end-text"):
                raise PreventUpdate
            try:
                left = datetime.fromisoformat(start_text.strip().replace(" ", "T"))
                right = datetime.fromisoformat(end_text.strip().replace(" ", "T"))
                if ((left.utcoffset() is None) != (first_instant.utcoffset() is None)
                        or (right.utcoffset() is None) != (first_instant.utcoffset() is None)
                        or left.second or left.microsecond or right.second or right.microsecond):
                    raise ValueError("Timezone or minute precision mismatch")
                offsets = ((left - first_instant).total_seconds() / 60,
                           (right - first_instant).total_seconds() / 60)
                if (not all(n.is_integer() for n in offsets)
                        or not 0 <= offsets[0] < offsets[1] <= total_minutes):
                    raise ValueError("Invalid bounds")
                return [int(offsets[0]), int(offsets[1])], no_update, no_update
            except (ValueError, TypeError, AttributeError):
                raise PreventUpdate

        @app.callback(
            Output("jaal-temporal-range", "step"),
            Input("jaal-temporal-unit", "value"),
        )
        def interval_selection_granularity(unit):
            return unit if unit in (1, 10, 60, 180, 1440) else 1

        @app.callback(
            Output("jaal-temporal-frames", "data"),
            Input("jaal-temporal-range", "value"),
            Input("jaal-temporal-mode", "value"),
            Input("jaal-temporal-unit", "value"),
            Input("jaal-temporal-window", "value"),
            Input("jaal-temporal-overlap", "value"),
            Input("jaal-temporal-step", "value"),
        )
        def prepare_temporal_frames(bounds, mode, unit, window_units,
                                    overlap, stride_units):
            if (not isinstance(bounds, (list, tuple)) or len(bounds) != 2
                    or any(type(n) is not int for n in bounds)
                    or mode not in ("cumulative", "rolling")
                    or unit not in (1, 10, 60, 180, 1440)
                    or window_units not in (1, 2, 3, 6, 12, 24, 30)
                    or stride_units not in (1, 2, 3, 6, 12, 24)
                    or overlap not in ("disjoint", "overlap")):
                raise PreventUpdate
            window_minutes = unit * window_units
            stride_minutes = (window_minutes if overlap == "disjoint"
                              else unit * stride_units)
            try:
                result = temporal_timeline.interval_frames(
                    start_minute=bounds[0], end_minute=bounds[1],
                    mode=mode, window_minutes=window_minutes,
                    step_minutes=stride_minutes,
                )
                result["overlap"] = overlap
                return result
            except GraphInputError as exc:
                # A bad request must not leave a stale earlier packet on
                # screen while showing incompatible granularity controls.
                return {"frames": [], "start_index": 0, "end_index": 0,
                        "error": str(exc), "unit_minutes": unit,
                        "overlap": overlap}

        app.clientside_callback(
            ClientsideFunction(namespace="jaal_temporal", function_name="playback"),
            Output("jaal-temporal-index", "value"),
            Output("jaal-temporal-tick", "disabled"),
            Output("jaal-temporal-play", "children"),
            Input("jaal-temporal-play", "n_clicks"),
            Input("jaal-temporal-back", "n_clicks"),
            Input("jaal-temporal-forward", "n_clicks"),
            Input("jaal-temporal-tick", "n_intervals"),
            Input("jaal-temporal-frames", "data"),
            State("jaal-temporal-index", "value"),
            State("jaal-temporal-tick", "disabled"),
            State("jaal-temporal-step", "value"),
            State("jaal-temporal-loop", "value"),
        )
        app.clientside_callback(
            ClientsideFunction(namespace="jaal_temporal", function_name="choose"),
            Output("jaal-temporal-frame", "data"),
            Output("jaal-temporal-status", "children"),
            Output("jaal-temporal-window-highlight", "style"),
            Input("jaal-temporal-index", "value"),
            Input("jaal-temporal-frames", "data"),
        )
        app.clientside_callback(
            ClientsideFunction(namespace="jaal_temporal", function_name="axis"),
            Output("jaal-temporal-index", "max"),
            Output("jaal-temporal-index", "marks"),
            Input("jaal-temporal-frames", "data"),
        )
        app.clientside_callback(
            ClientsideFunction(namespace="jaal_temporal", function_name="speed"),
            Output("jaal-temporal-tick", "interval"),
            Input("jaal-temporal-speed", "value"),
        )

    graph_run_inputs = [
        Input("jaal-original-layout-mode", "value"),
        Input("graph", "data"),
        Input("jaal-original-chinese-labels", "value"),
        Input("jaal-original-ct-translations", "data"),
        Input("jaal-community-membership", "data"),
        Input("jaal-structural-eligible", "data"),
    ]
    if temporal_frames is not None:
        graph_run_inputs.extend([
            Input("jaal-temporal-frame", "data"),
            Input("jaal-temporal-labels", "value"),
            Input("jaal-temporal-community-policy", "value"),
        ])
    graph_run_inputs.append(Input("jaal-original-edge-length", "value"))
    app.clientside_callback(
        ClientsideFunction(namespace="jaal_visible_labels",
                           function_name="apply"),
        Output("graph", "run"),
        *graph_run_inputs,
    )
    return app
