"""Public sample-only Vercel entrypoint for the real Jaal/Dash gallery.

All demonstration data are fictional, generated reproducibly or loaded from
checked-in examples. No real emails, personal identities, private files,
live mail service access, arbitrary uploads, or database mutation.
"""
from __future__ import annotations

import os
import json
from collections import Counter
from pathlib import Path

from flask import Response, jsonify

from jaal_topology import load_graph, select_subgraph
from jaal_topology.email_simulation import (
    SEED, WORK_DAYS, WORKFLOW_LABELS, simulate_company_email,
)
from jaal_topology.gallery import GalleryCase, DeferredGalleryCase, create_gallery_app
from jaal_topology.temporal import TemporalTimeline

_ROOT = Path(__file__).resolve().parent
_SOURCE = _ROOT / "examples"


def _sample(edges: str, labels: str, expected_nodes: int, expected_edges: int):
    """Fail closed if a reviewed fixture changes without a new contract."""
    graph = select_subgraph(
        load_graph(_SOURCE / edges, _SOURCE / labels),
        max_nodes=250, max_edges=5000,
    )
    if (len(graph.nodes), len(graph.edges)) != (expected_nodes, expected_edges):
        raise RuntimeError(f"Unexpected fictional PoC fixture: {edges}")
    return graph


# Original taxonomy-derived graph is preserved as an explicit comparison.
_graph = _sample("company_communications.csv", "company_people.csv", 77, 169)
_tree = _sample("org_tree.csv", "org_tree_labels.csv", 52, 51)
_dag = _sample("project_dag.csv", "project_dag_labels.csv", 19, 31)

# The new default example is grounded in explicit workflows and an event log
# (rather than randomly joining fictional roles by position in a taxonomy).
_simulation = simulate_company_email()
_email = select_subgraph(_simulation.graph, max_nodes=250, max_edges=5000)
_timeline = TemporalTimeline(_email, _simulation.events)
if not 1 <= len(_email.edges) <= 5000 or not _email.edge_counts:
    raise RuntimeError("Email workflow demo must have bounded message volumes")

_CASES = (
    GalleryCase(
        "mail-workflow", "企業郵件實務模擬（業務與事件）", _email,
        initial_mode="network-community-collapsed",
        temporal_timeline=_timeline,
        description=(
            "完全虛構、固定種子的 20 個工作日電子郵件事件：以部門內頻繁協作、"
            "主管回報、業務提案、客戶問題、跨部門交付、月底對帳、HR 新人作業及"
            "兩次夜間系統事故產生信件／回信討論串。箭頭為寄件者 → 收件者；"
            "線寬與提示顯示合成收發封數，Louvain 依事件數加權；"
            "社群間的數字仍是獨立寄收件對數。"
            "此模型是教學情境，不是經實際企業資料校準的機率預測。"
        ),
        resources=(
            ("下載模擬郵件事件 CSV", "/demo/mail-events.csv"),
            ("下載收發彙總 CSV", "/demo/mail-edges.csv"),
        ),
    ),
    GalleryCase(
        "mail-network", "舊版通訊拓樸（類別樹改編）", _graph,
        description="77 個節點從 TW Affairs 類別樹改名並追加人工連線；適合對照拓樸演算法，並非真實企業郵件事件模型。",
    ),
    GalleryCase(
        "org-tree", "公司組織階層樹（無環）", _tree,
        initial_mode="hierarchical-collapsed",
    ),
    GalleryCase(
        "project-dag", "專案相依網路（多父 DAG）", _dag,
        initial_mode="hierarchical",
    ),
)

def _large_local_cases_enabled(environment):
    """Default to large demos only for an interactive local Flask CLI run.

    Importing app as WSGI, including from Vercel, preserves the four-case
    gallery; explicit 0 disables the local setting. Large graphs are lazy.
    """
    if environment.get("VERCEL") or environment.get("VERCEL_ENV"):
        return False
    switch = environment.get("JAAL_ENABLE_LARGE_LOCAL")
    if switch is not None:
        return switch == "1"
    return (
        environment.get("FLASK_RUN_FROM_CLI", "").lower() == "true"
        and environment.get("CI", "").lower() not in ("1", "true")
    )


# Local Flask CLI enables large fictional cases by default with load warning.
# Public WSGI/CI remains bounded; explicit JAAL_ENABLE_LARGE_LOCAL=0 disables.
if _large_local_cases_enabled(os.environ):
    from jaal_topology.scaled_demo import build_scaled_email_demo

    def _deferred_scaled_case(slug, title):
        def load():
            model = build_scaled_email_demo(slug)
            timeline = TemporalTimeline(
                model.graph, model.events, allow_large_demo=True)
            return GalleryCase(
                "scale-" + slug, title, model.graph,
                initial_mode=("hierarchical-collapsed"
                              if slug == "3000-dag" else
                              "network-community-collapsed"),
                temporal_timeline=timeline,
                initial_positions=model.positions,
                allow_large_demo=True,
                description=(
                    f"固定規則虛構郵件資料：{len(model.graph.nodes)} 人、"
                    f"{len(model.graph.edges)} 條實際有向收發關係、"
                    f"{model.departments} 部門、{model.depth} 層深度。"
                    f"弱連通分量 {model.components}；分量間絕無邊。"
                    "原版 Jaal 五模式、搜尋、局部子圖、Louvain 與時間軸；"
                    "這是僅限本機的真實容量壓測，不保證巨大圖能流暢渲染。"
                ),
            )
        return load

    _SCALE_CHOICES = (
        ("500", "企業郵件｜500 人（全 Jaal）"),
        ("3000", "企業郵件｜3,000 人（全 Jaal）"),
        ("5000", "企業郵件｜5,000 人（全 Jaal）⚠ 高負載"),
        ("20000", "企業郵件｜20,000 人（全 Jaal）⚠ 極高負載"),
        ("3000-dag", "企業郵件｜3,000 人（無環 DAG／五模式）"),
        ("three-components", "企業郵件｜3 個互不連通群（500 人）"),
    )
    _CASES += tuple(
        DeferredGalleryCase("scale-" + slug, title,
                            _deferred_scaled_case(slug, title))
        for slug, title in _SCALE_CHOICES
    )

def _public_500_enabled(environment):
    """Vercel only: opt-in application mode with an emergency kill switch.

    Never expose other scale scenarios just because local large-demo flag was
    accidentally set. The allowed fixture is a single literal 500-person
    synthetic email graph; custom CSV imports remain browser-local.
    """
    hosted = bool(environment.get("VERCEL") or environment.get("VERCEL_ENV"))
    return hosted and environment.get("JAAL_VERCEL_500_ENABLED", "1") == "1"


if _public_500_enabled(os.environ):
    def _public_500_case():
        from jaal_topology.scaled_demo import build_scaled_email_demo

        dataset = build_scaled_email_demo("500")
        # Public graph is within the unchanged 3000/5000 default caps.
        # A future larger synthetic preset must not inherit this privilege.
        if len(dataset.graph.nodes) != 500 or len(dataset.graph.edges) > 5000:
            raise RuntimeError("Public Jaal case exceeds the exact 500-node boundary")
        return GalleryCase(
            "scale-500",
            "企業郵件｜500 人（公網示範）",
            dataset.graph,
            initial_mode="network-community-collapsed",
            temporal_timeline=TemporalTimeline(dataset.graph, dataset.events),
            initial_positions=dataset.positions,
            allow_large_demo=False,
            description=(
                "500 個完全虛構的企業郵件節點，包含部門、主管與員工、"
                "有向寄收件、Louvain 社群及時間演化。"
                "這是唯一允許於 Vercel 的大型合成案例；"
                "3,000／5,000／20,000 節點仍限本機。"
            ),
        )

    _CASES += (DeferredGalleryCase(
        "scale-500", "企業郵件｜500 人（公網示範）", _public_500_case,
    ),)


dash_app = create_gallery_app(_CASES)
app = dash_app.server  # Flask WSGI entrypoint auto-detected by Vercel.


def _download(text: str, name: str) -> Response:
    response = Response(text, content_type="text/csv; charset=utf-8")
    response.headers["Content-Disposition"] = f'attachment; filename="{name}"'
    response.headers["Cache-Control"] = "public, max-age=600"
    return response


@app.get("/demo/mail-events.csv")
def download_email_events():
    return _download(_simulation.events_csv(), "fictional-mail-events.csv")


@app.get("/demo/mail-edges.csv")
def download_email_edges():
    return _download(_simulation.aggregate_csv(), "fictional-mail-edge-counts.csv")


@app.get("/demo/mail-summary")
def mail_summary():
    workflows = Counter(m.workflow for m in _simulation.events)
    same_dept = sum(
        _simulation.divisions[m.sender] == _simulation.divisions[m.recipient]
        for m in _simulation.events
    )
    reply_count = sum(bool(m.reply_to) for m in _simulation.events)
    return jsonify(
        status="fictional-simulation",
        seed=SEED,
        work_days=WORK_DAYS,
        events=len(_simulation.events),
        people=len(_email.nodes),
        directed_pairs=len(_email.edges),
        intra_department_share=round(same_dept / len(_simulation.events), 4),
        replies=reply_count,
        workflows=dict(sorted(workflows.items())),
        workflow_names=WORKFLOW_LABELS,
        origin="rule-based-business-processes-with-seeded-variation",
        privacy="role-identifiers-only-no-real-mail",
    )


@app.get("/healthz")
def healthz():
    """Minimal non-sensitive health for the actual default gallery page."""
    return jsonify(
        status="ok",
        demo="public-fictional-data",
        viewer="jaal-dash-real-runtime",
        modes=5,
        nodes=len(_email.nodes),
        directed_edges=len(_email.edges),
    )
