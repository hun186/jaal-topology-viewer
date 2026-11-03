"""Windows Chromium acceptance smoke for the *real* standalone Jaal Dash iframe.

Only synthetic fixture data, localhost HTTP and read-only graph operations.
Not a substitute for a human review of screenshots or the Stage 4 consumer.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]


def serve(port: int) -> None:
    from flask import Flask
    from jaal_topology import load_graph, select_subgraph
    from jaal_topology.integration import mount_flask

    edges = ROOT / "examples" / "company_communications.csv"
    labels = ROOT / "examples" / "company_people.csv"
    graph = select_subgraph(load_graph(edges, labels))
    app = Flask("jaal_browser_acceptance")

    @app.get("/")
    def host():
        return (
            '<!doctype html><html><head><meta charset="utf-8"></head>'
            '<body style="margin:0"><h1>Same-port host</h1>'
            '<iframe id="topology-frame" title="Topology" src="/topology/" '
            'style="width:100%;height:1000px;border:0"></iframe></body></html>'
        )

    mount_flask(app, graph, mount_path="/topology")
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


def check(port: int, evidence: Path) -> None:
    from playwright.sync_api import sync_playwright

    evidence.mkdir(parents=True, exist_ok=True)
    log_path = evidence / "localhost-server.log"
    with log_path.open("w", encoding="utf-8") as log:
        proc = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "--serve",
             "--port", str(port)],
            cwd=str(ROOT), stdout=log, stderr=subprocess.STDOUT,
        )
        try:
            target = f"http://127.0.0.1:{port}"
            deadline = time.monotonic() + 75
            while time.monotonic() < deadline:
                if proc.poll() is not None:
                    raise AssertionError(f"Jaal localhost server exited {proc.returncode}")
                try:
                    with urlopen(target + "/topology/_dash-layout", timeout=2) as response:
                        if response.status == 200:
                            break
                except (OSError, URLError):
                    time.sleep(0.4)
            else:
                raise AssertionError("Timed out waiting for mounted Jaal Dash layout")
            with urlopen(target + "/", timeout=5) as response:
                assert b'topology-frame' in response.read()
            for asset in ("16.jaal_visible_labels.js",
                          "17.jaal_structural_collapse.js",
                          "18.jaal_community_collapse.js",
                          "bootstrap.min.css"):
                with urlopen(target + "/topology/assets/" + asset, timeout=5) as response:
                    assert response.status == 200, asset

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 1000})
                errors: list[str] = []
                page.on("pageerror", lambda err: errors.append(str(err)))
                page.goto(target + "/", wait_until="domcontentloaded", timeout=60000)
                frame = page.frame_locator("#topology-frame")
                frame.locator(".vis-network canvas").first.wait_for(
                    state="visible", timeout=90000
                )
                assert frame.locator("#jaal-original-layout-mode input[type=radio]").count() == 5
                assert frame.get_by_label("網狀（收攏）", exact=True).is_disabled()
                assert frame.get_by_label("階層（收攏）", exact=True).is_disabled()
                assert frame.get_by_label("網狀（社群收攏・Louvain）", exact=True).is_enabled()
                assert "已檢測到有向迴路" in frame.locator(
                    "#jaal-original-structural-hint"
                ).inner_text()
                assert "一般有環網路" in frame.locator(
                    "#jaal-original-graph-profile"
                ).inner_text()
                assert frame.locator("#jaal-original-chinese-labels input[type=checkbox]").count() == 1
                assert frame.locator("#search_graph").count() == 1
                # Vis.js really created a nonzero-size canvas inside the embedded Dash app.
                size = frame.locator(".vis-network canvas").first.bounding_box()
                assert size and size["width"] > 100 and size["height"] > 100, size
                page.screenshot(path=str(evidence / "01-network.png"), full_page=True)

                # Observe the actual visdcc Network instance, never a simulated graph.
                # The existing community clientside callback calls api.activate
                # with "this" bound to the mounted Network; capture that reference
                # only in this automated browser, without changing shipped JS.
                frame.locator("body").evaluate("""(element) => {
                    const api = window.dash_clientside?.jaal_community_collapse;
                    if (!api || typeof api.activate !== "function") {
                        throw new Error("Community runtime was not loaded");
                    }
                    const original = api.activate;
                    api.activate = function(...args) {
                        window.__acceptanceNetwork = this;
                        return original.apply(this, args);
                    };
                }""")

                def snapshot():
                    return frame.locator("body").evaluate("""(element) => {
                        const component = window.__acceptanceNetwork;
                        if (!component || !component.nn || !component.ee) return null;
                        return {
                            nodes: component.nn.get(),
                            edges: component.ee.get(),
                            originalCount: component.props.data.nodes.length,
                            active: !!component.__jaalCommunity?.active,
                            filtered: !!component.__jaalCommunity?.filtered,
                        };
                    }""")

                def require_state(description, predicate):
                    latest = None
                    deadline = time.monotonic() + 25
                    while time.monotonic() < deadline:
                        latest = snapshot()
                        if latest is not None and predicate(latest):
                            return latest
                        page.wait_for_timeout(200)
                    raise AssertionError(f"{description} never reached: {latest!r}")

                labels = {
                    "network": "網狀（全展開）",
                    "network-community-collapsed": "網狀（社群收攏・Louvain）",
                    "hierarchical": "階層（全展開）",
                }

                def choose(mode: str) -> None:
                    # Accessible Dash labels are portable across dcc.RadioItems
                    # versions, including versions lacking input[value].
                    radio = frame.get_by_label(labels[mode], exact=True)
                    radio.check(timeout=20000)
                    assert radio.is_checked()

                choose("network-community-collapsed")
                collapsed = require_state(
                    "synthetic community quotient appears in actual browser DataSet",
                    lambda s: s["active"] and not s["filtered"]
                    and len(s["nodes"]) < s["originalCount"]
                    and any(str(n["id"]).startswith("__jaal_internal_community__")
                            for n in s["nodes"]),
                )
                # Use the real visdcc Network event emitter; no mocked graph,
                # static fabricated provenance or source mutations.
                inspected = frame.locator("body").evaluate("""() => {
                    const component = window.__acceptanceNetwork;
                    const edge = component.ee.get().find(item =>
                        String(item.id).startsWith("__jaal_internal_link__"));
                    if (!edge) throw Error("Missing aggregated community edge");
                    const evidence = window.dash_clientside.jaal_community_collapse
                        .explainEdge(component.__jaalCommunity.view, edge.id);
                    if (!evidence.length) throw Error("No original provenance");
                    // Dispatch real vis Network's registered click callback.
                    component.net.body.emitter.emit('click', {nodes: [], edges: [edge.id]});
                    return {id: edge.id, count: evidence.length,
                            from: evidence[0].from, to: evidence[0].to};
                }""")
                details = frame.locator("#jaal-community-edge-inspector")
                details.wait_for(state="visible", timeout=12000)
                assert details.locator("li").count() == min(100, inspected["count"])
                assert "原始有向關係" in details.inner_text()
                assert inspected["from"] in details.locator("li").first.get_attribute("title")
                assert inspected["to"] in details.locator("li").first.get_attribute("title")
                page.screenshot(
                    path=str(evidence / "02a-community-edge-provenance.png"),
                    full_page=True,
                )
                details.get_by_role("button", name="關閉").click()
                details.wait_for(state="detached", timeout=10000)
                checkbox = frame.locator(
                    "#jaal-original-chinese-labels input[type=checkbox]"
                )
                checkbox.check()
                assert checkbox.is_checked()
                # Community-only nodes need not have a Chinese translation; the
                # Search projection below must use CT on original members.
                page.screenshot(path=str(evidence / "02-community-chinese.png"), full_page=True)

                search = frame.locator("#search_graph")
                search.fill("Finance")
                filtered = require_state(
                    "real Search projects original IDs, matched hidden flags and CT",
                    lambda s: s["active"] and s["filtered"]
                    and len(s["nodes"]) == s["originalCount"]
                    and any(n.get("hidden") for n in s["nodes"])
                    and any(not n.get("hidden") for n in s["nodes"])
                    and all(bool(n.get("hidden")) ==
                            ("finance" not in str(n["id"]).casefold())
                            for n in s["nodes"])
                    and any(n.get("label") != n["id"] for n in s["nodes"]
                            if not n.get("hidden")),
                )
                assert filtered["originalCount"] == 77
                assert frame.locator(".vis-network canvas").first.is_visible()
                page.screenshot(path=str(evidence / "03-search-chinese.png"), full_page=True)
                search.fill("")
                require_state(
                    "cleared Search restores community quotient",
                    lambda s: s["active"] and not s["filtered"]
                    and len(s["nodes"]) < s["originalCount"]
                    and any(str(n["id"]).startswith("__jaal_internal_community__")
                            for n in s["nodes"]),
                )
                checkbox.uncheck()
                choose("hierarchical")
                page.screenshot(path=str(evidence / "04-hierarchy-full.png"), full_page=True)
                choose("network")
                restored = require_state(
                    "mode restoration rehydrates 77 unmodified English IDs",
                    lambda s: not s["active"] and len(s["nodes"]) == 77
                    and len(s["edges"]) == 169
                    and all(n["label"] == n["id"] and not n.get("hidden")
                            for n in s["nodes"])
                    and not any(str(n["id"]).startswith("__jaal_internal_community__")
                                for n in s["nodes"]),
                )
                assert frame.locator(".vis-network canvas").first.is_visible()
                if errors:
                    raise AssertionError("Browser JavaScript errors: " + " | ".join(errors))
                (evidence / "acceptance-summary.txt").write_text(
                    "PASS: Hosted Windows Chromium same-port iframe, five radio modes, "
                    "real visdcc DataSet cluster quotient and source edge inspection, cycle-protected structural modes, Search hidden flags, "
                    "Chinese CT labels and 77-node/169-edge restoration. Screenshots "
                    "are inspection evidence; manual Stage 4 drag/camera/Color/Size "
                    "acceptance is NOT asserted.\n",
                    encoding="utf-8",
                )
                browser.close()
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=8)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--port", type=int, default=8097)
    parser.add_argument("--evidence", type=Path, default=Path("browser-evidence"))
    args = parser.parse_args()
    if args.serve:
        serve(args.port)
    else:
        check(args.port, args.evidence)
