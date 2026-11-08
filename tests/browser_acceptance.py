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
    from playwright.sync_api import sync_playwright, expect

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
                          "22.jaal_local_focus.js",
                           "23.jaal_label_intelligence.js",
                          "bootstrap.min.css", "19.jaal_compact_layout.css"):
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
                # The original Jaal settings are independently collapsible;
                # graph/canvas must expand to the released width and restore.
                sidebar_toggle = frame.locator("#jaal-sidebar-toggle")
                panel = frame.locator(".jaal-settings-col")
                graph_column = frame.locator(".jaal-graph-col")
                help_details = frame.locator("#jaal-original-help-details")
                assert sidebar_toggle.is_visible()
                assert sidebar_toggle.get_attribute("aria-expanded") == "true"
                assert panel.is_visible()
                assert not help_details.evaluate("(el) => el.open")
                before_width = graph_column.bounding_box()["width"]
                before_canvas = frame.locator(".vis-network canvas").first.bounding_box()["width"]
                before_height = frame.locator("#jaal-compact-toolbar").bounding_box()["height"]
                assert before_height < 105, before_height
                sidebar_toggle.click()
                expect(sidebar_toggle).to_have_attribute("aria-expanded", "false", timeout=15000)
                expect(panel).to_be_hidden(timeout=15000)
                page.wait_for_timeout(700)
                grown_width = graph_column.bounding_box()["width"]
                grown_canvas = frame.locator(".vis-network canvas").first.bounding_box()["width"]
                assert grown_width > before_width + 180, (before_width, grown_width)
                assert grown_canvas > before_canvas + 150, (before_canvas, grown_canvas)
                # Settings were never unmounted; restore all existing inputs.
                assert frame.locator("#search_graph").count() == 1
                sidebar_toggle.click()
                expect(sidebar_toggle).to_have_attribute("aria-expanded", "true", timeout=15000)
                expect(panel).to_be_visible(timeout=15000)
                # No sticky top controls; focus mode fills the same-port
                # iframe viewport without remounting the visdcc Network.
                toolbar = frame.locator("#jaal-compact-toolbar")
                assert toolbar.evaluate(
                    "(el) => getComputedStyle(el).position"
                ) not in ("fixed", "sticky")
                normal_canvas_height = frame.locator(
                    ".vis-network canvas"
                ).first.bounding_box()["height"]
                assert normal_canvas_height > 700, normal_canvas_height
                focus_toggle = frame.locator("#jaal-focus-toggle")
                focus_toggle.click()
                expect(frame.locator("#jaal-viewer-root")).to_have_class(
                    "jaal-viewer-shell jaal-focus-mode jaal-focus-compact",
                    timeout=15000
                )
                expect(focus_toggle).to_have_attribute("aria-pressed", "true")
                expect(frame.locator(".jaal-settings-col")).to_be_hidden()
                # Non-temporal Jaal: focus shows only a tiny original
                # graph-count overlay instead of inflating the toolbar.
                summary = frame.locator("#jaal-focus-static-status")
                expect(summary).to_be_visible()
                expect(summary).to_contain_text("77 節點")
                small = summary.bounding_box()
                assert small and small["height"] < 75,small
                expect(frame.locator("#jaal-focus-panel-toggle")).to_be_visible()
                # The class callback and graph.options resize callback run
                # independently; wait for the actual vis.js Canvas redraw.
                focused_canvas_height = 0
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    focused_canvas_height = frame.locator(
                        ".vis-network canvas"
                    ).first.bounding_box()["height"]
                    if focused_canvas_height > 940:
                        break
                    page.wait_for_timeout(200)
                assert focused_canvas_height > 940, focused_canvas_height
                page.screenshot(path=str(evidence / "05-full-viewport.png"),
                                full_page=True)
                focus_toggle.press("Escape")
                expect(frame.locator("#jaal-viewer-root")).to_have_class(
                    "jaal-viewer-shell", timeout=15000
                )
                expect(focus_toggle).to_have_attribute("aria-pressed", "false")
                expect(frame.locator(".jaal-settings-col")).to_be_visible()
                help_details.locator("summary").click()
                assert help_details.evaluate("(el) => el.open")
                assert frame.locator("#jaal-original-structural-hint").is_visible()
                assert "已檢測到有向迴路" in frame.locator(
                    "#jaal-original-structural-hint"
                ).inner_text()
                help_details.locator("summary").click()
                assert not help_details.evaluate("(el) => el.open")
                assert frame.locator("#jaal-original-layout-mode input[type=radio]").count() == 5
                assert frame.get_by_label("網狀（收攏）", exact=True).is_disabled()
                assert frame.get_by_label("階層（收攏）", exact=True).is_disabled()
                assert frame.get_by_label("網狀（社群收攏・Louvain）", exact=True).is_enabled()
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
                # Searchable bilingual root picker: scope is a reversible
                # rendering projection, not a mutation of the 77/169 source.
                local_details = frame.locator(".jaal-local-details")
                local_details.locator("summary").click()
                assert local_details.evaluate("(el) => el.open")
                frame.locator("#jaal-local-hops").click()
                # Dash/react-select may portal the option menu into the iframe
                # body rather than under the dropdown wrapper itself.
                frame.get_by_text("0 步", exact=True).last.click(timeout=15000)
                expect(frame.locator("#jaal-local-hops")).to_contain_text(
                    "0 步", timeout=10000
                )
                candidate = frame.locator("body").evaluate("""() =>
                    window.__acceptanceNetwork.props.data.nodes.find(
                        n => String(n.id).includes("Executive"))?.id ||
                    window.__acceptanceNetwork.props.data.nodes[0].id
                """)
                # Inspect the actual React Select element if a Windows Dash
                # variant changes input nesting; never mutate Dash state.
                root_picker = frame.locator("#jaal-local-root")
                root_picker.click()
                # A Chinese/ID root option must never occupy a 60px wide
                # vertical strip: actual React-Select dropdown geometry.
                root_box = root_picker.bounding_box()
                assert root_box and root_box["width"] >= 300, root_box
                # Dash 3 uses .Select-menu-outer; Dash 4/modern react-select
                # uses .Select__menu, sometimes outside the dropdown wrapper.
                root_menu = root_picker.locator(".Select-menu-outer, .Select__menu")
                if not root_menu.count():
                    # Dash 4 renders a <button class="dash-dropdown"> plus
                    # a Radix portal outside the button with role=listbox.
                    root_menu = frame.locator(
                        '[role="listbox"]:visible, '
                        '[data-radix-popper-content-wrapper]:visible'
                    ).last
                expect(root_menu).to_be_visible(timeout=15000)
                menu_box = root_menu.bounding_box()
                assert menu_box and menu_box["width"] >= 300, menu_box
                options = root_menu.locator(
                    '.VirtualizedSelectOption, .Select-option, .Select__option, '
                    '[role="option"]')
                assert options.count() > 0 or root_menu.inner_text().strip(), (
                    "Root listbox must have actual selectable content")
                if options.count():
                    assert options.first.evaluate(
                        "(el) => getComputedStyle(el).whiteSpace") == "nowrap"
                rows = root_menu.locator(".VirtualizedSelectOption")
                if rows.count() >= 2:
                    first, second = rows.nth(0).bounding_box(), rows.nth(1).bounding_box()
                    assert first and second and first["y"] + first["height"] <= second["y"] + 1
                page.screenshot(path=str(evidence / "06-root-picker-readable.png"))
                print("TRACE_ROOT_PICKER=" + ascii(root_picker.evaluate(
                    "(el) => el.outerHTML.slice(0, 1400)"
                )), flush=True)
                search_input = root_picker.locator("input")
                if search_input.count():
                    search_input.fill(candidate)
                else:
                    page.keyboard.insert_text(candidate)
                print("TRACE_ROOT_SEARCH=" + ascii(root_picker.evaluate(
                    "(el) => el.outerHTML.slice(0, 1400)"
                )), flush=True)
                # Select the visible menu option rather than assuming the
                # Enter key chooses the intended (possibly virtualized) row.
                frame.get_by_text(candidate, exact=False).last.click(
                    timeout=15000
                )
                expect(frame.locator("#jaal-local-status")).to_contain_text(
                    "局部子圖", timeout=15000
                )
                latest = None
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    latest = frame.locator("body").evaluate("""() => {
                        const instance = window.__acceptanceNetwork;
                        return {
                            root: window.dash_clientside?.jaal_local_focus?.root,
                            shown: instance.nn.get().filter(n => !n.hidden).length,
                            total: instance.props.data.nodes.length,
                        };
                    }""")
                    if latest["root"] == candidate and latest["shown"] == 1:
                        break
                    page.wait_for_timeout(200)
                assert latest and latest["shown"] == 1, latest
                assert latest["total"] == 77
                # The 0-hop root must enter the actual camera viewport.
                # FrameLocator has no wait_for_function API in Playwright.
                # Read the embedded frame's real vis-network coordinates
                # repeatedly until its optional fit animation settles.
                deadline = time.monotonic() + 20
                camera = None
                while time.monotonic() < deadline:
                    camera = frame.locator("body").evaluate("""(id) => {
                        const c=window.__acceptanceNetwork;
                        // vis-network can report a temporarily null
                        // getPositions() value for an isolated 0-hop node,
                        // even while its active internal index and DataSet
                        // have a finite, drawable x/y world coordinate.
                        const active=c.nn.get().filter(n=>!n.hidden).map(n=>n.id);
                        const live=c.net.getPositions()[id];
                        const internal=c.net.body?.nodes?.[id];
                        const saved=c.nn.get(id);
                        const finite=p=>p&&Number.isFinite(p.x)&&Number.isFinite(p.y);
                        const p=finite(live)?live:
                            finite(internal)?{x:internal.x,y:internal.y}:
                            finite(saved)?{x:saved.x,y:saved.y}:null;
                        const center=c.net.getViewPosition();
                        return {p,center,pending:
                            window.dash_clientside?.jaal_local_focus?.pendingFit,
                            visible:active,
                            activeIndices:c.net.body?.nodeIndices?.slice(0,8),
                            candidate:id,
                            source:finite(live)?"live":finite(internal)?"internal":
                                finite(saved)?"dataset":"none"};
                    }""",candidate)
                    if (camera["p"] and camera["center"] and
                            camera["visible"] == [candidate] and
                            candidate in (camera["activeIndices"] or []) and
                            not camera["pending"] and
                            ((camera["p"]["x"]-camera["center"]["x"])**2 +
                             (camera["p"]["y"]-camera["center"]["y"])**2) < 900):
                        break
                    page.wait_for_timeout(200)
                else:
                    raise AssertionError("New local subgraph remained out of view: " +
                                         str(camera))
                assert frame.locator(".vis-network canvas").first.is_visible()
                # Clear in-place and recover the full source graph.
                # Dash 4 renders an <a> with an accessible Clear selection
                # label (NOT a button); Dash 2/3 use react-select's clear zone.
                modern_clear = frame.locator(
                    '#jaal-local-root [aria-label="Clear selection"]'
                )
                if modern_clear.count():
                    modern_clear.click()
                else:
                    legacy_clear = frame.locator(
                        "#jaal-local-root .Select-clear-zone"
                    )
                    assert legacy_clear.count() == 1, ascii(
                        root_picker.evaluate("(el) => el.outerHTML.slice(0, 1800)")
                    )
                    legacy_clear.click()
                restored_scope = None
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    restored_scope = frame.locator("body").evaluate("""() => {
                        const instance = window.__acceptanceNetwork;
                        return {
                            root: window.dash_clientside?.jaal_local_focus?.root,
                            shown: instance.nn.get().filter(n => !n.hidden).length,
                        };
                    }""")
                    if restored_scope["root"] is None and restored_scope["shown"] == 77:
                        break
                    page.wait_for_timeout(200)
                assert restored_scope == {"root": None, "shown": 77}, restored_scope
                if errors:
                    raise AssertionError("Browser JavaScript errors: " + " | ".join(errors))
                (evidence / "acceptance-summary.txt").write_text(
                    "PASS: Hosted Windows Chromium same-port iframe, five radio modes, "
                    "real visdcc DataSet cluster quotient and source edge inspection, cycle-protected structural modes, Search hidden flags, "
                    "Chinese CT labels, searchable root 0-hop narrowing to one visible node "
                    "and clearing to restore 77 nodes / 169 source edges. Screenshots "
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
