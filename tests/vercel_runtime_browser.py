"""Real Chromium smoke through the very same Flask entry Vercel imports."""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError

ROOT = Path(__file__).resolve().parents[1]


def serve(port):
    # When Python executes tests/script.py, sys.path[0] is the tests folder,
    # not the checkout root containing the Vercel app.py entrypoint.
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from app import app

    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


def check(port):
    from playwright.sync_api import sync_playwright, expect

    log = ROOT / "vercel-runtime-smoke.log"
    with log.open("w", encoding="utf-8") as out:
        child = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()),
             "--serve", "--port", str(port)],
            cwd=ROOT, stdout=out, stderr=subprocess.STDOUT,
        )
        try:
            url = "http://127.0.0.1:" + str(port)
            start = time.monotonic()
            while time.monotonic() - start < 90:
                if child.poll() is not None:
                    raise AssertionError("WSGI entrypoint exited: " + str(child.returncode) + "\n" + log.read_text(encoding="utf-8", errors="replace")[-3500:])
                try:
                    with urlopen(url + "/healthz", timeout=2) as resp:
                        if resp.status == 200:
                            break
                except (OSError, URLError):
                    time.sleep(0.4)
            else:
                raise AssertionError("Real Flask/Dash WSGI did not start")

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 960})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                page.locator(".vis-network canvas").first.wait_for(
                    state="visible", timeout=90000,
                )
                sidebar = page.locator("#jaal-sidebar-toggle")
                panel = page.locator(".jaal-settings-col")
                column = page.locator(".jaal-graph-col")
                help_details = page.locator("#jaal-original-help-details")
                assert sidebar.is_visible() and panel.is_visible()
                assert not help_details.evaluate("(el) => el.open")
                # Regression: temporal Select popups used to inherit an 88px
                # control width, placing each Chinese character vertically.
                # Validate actual Dash 3.4 Chromium DOM, not just stylesheet
                # presence or layout JSON.
                for control_id, expected_label, min_menu_width in (
                    ("jaal-temporal-unit", "1 分鐘", 160),
                    ("jaal-temporal-window", "3 單位", 160),
                    ("jaal-temporal-step", "1 單位", 160),
                    ("jaal-temporal-speed", "標準", 160),
                    ("jaal-temporal-overlap", "互斥（步長＝窗長）", 225),
                ):
                    control = page.locator("#" + control_id)
                    expect(control).to_be_visible(timeout=15000)
                    control.locator(".Select-control").click()
                    menu = control.locator(".Select-menu-outer")
                    expect(menu).to_be_visible(timeout=15000)
                    bounds = menu.bounding_box()
                    assert bounds and bounds["width"] >= min_menu_width, (
                        control_id, bounds)
                    assert bounds["x"] >= -1 and bounds["x"] + bounds["width"] <= 1441, (
                        control_id, bounds)
                    options = menu.locator(".VirtualizedSelectOption, .Select-option")
                    assert options.count() > 0, control_id
                    assert expected_label in menu.inner_text(), (control_id, menu.inner_text())
                    rows = menu.locator(".VirtualizedSelectOption")
                    if rows.count() >= 2:
                        row_boxes = [rows.nth(i).bounding_box()
                                     for i in range(min(rows.count(), 7))]
                        for first, second in zip(row_boxes, row_boxes[1:]):
                            assert first and second
                            assert first["y"] + first["height"] <= second["y"] + 1, (
                                control_id, first, second)
                    # The full text must fit horizontally in a single item row.
                    assert options.first.evaluate(
                        "(el) => getComputedStyle(el).whiteSpace") == "nowrap", control_id
                    if control_id == "jaal-temporal-overlap":
                        proof = ROOT / "browser-evidence" / "temporal-dropdown-fixed.png"
                        proof.parent.mkdir(exist_ok=True)
                        page.screenshot(path=str(proof))
                    page.keyboard.press("Escape")
                    expect(menu).to_be_hidden(timeout=10000)
                width_open = column.bounding_box()["width"]
                canvas_open = page.locator(".vis-network canvas").first.bounding_box()["width"]
                # The timeline adds a compact second control row; other
                # single-graph and non-temporal cases retain the small toolbar.
                assert page.locator("#jaal-compact-toolbar").bounding_box()["height"] < 260
                sidebar.click()
                expect(sidebar).to_have_attribute("aria-expanded", "false", timeout=15000)
                expect(panel).to_be_hidden(timeout=15000)
                page.wait_for_timeout(700)
                assert column.bounding_box()["width"] > width_open + 180
                assert page.locator(".vis-network canvas").first.bounding_box()["width"] > canvas_open + 150
                sidebar.click()
                expect(sidebar).to_have_attribute("aria-expanded", "true", timeout=15000)
                expect(panel).to_be_visible(timeout=15000)
                # Normal scroll may carry the toolbar away; never pin it
                # above the graph when the user wants additional space.
                toolbar = page.locator("#jaal-compact-toolbar")
                assert toolbar.evaluate(
                    "(el) => getComputedStyle(el).position"
                ) not in ("fixed", "sticky")
                normal_canvas_height = page.locator(
                    ".vis-network canvas"
                ).first.bounding_box()["height"]
                assert normal_canvas_height > 650, normal_canvas_height

                focus_button = page.locator("#jaal-focus-toggle")
                focus_button.click()
                focus_shell = page.locator("#jaal-viewer-root")
                expect(focus_shell).to_have_class(
                    "jaal-viewer-shell jaal-focus-mode", timeout=15000
                )
                expect(focus_button).to_have_attribute(
                    "aria-pressed", "true", timeout=15000
                )
                expect(focus_button).to_have_text("退出全版 ✕")
                expect(panel).to_be_hidden()
                expect(page.locator(".jaal-brand-row")).to_be_hidden()
                graph_box = column.bounding_box()
                assert graph_box["width"] > 1350, graph_box
                focused_canvas_height = 0
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    focused_canvas_height = page.locator(
                        ".vis-network canvas"
                    ).first.bounding_box()["height"]
                    if focused_canvas_height > 900:
                        break
                    page.wait_for_timeout(200)
                assert focused_canvas_height > 900, focused_canvas_height
                assert page.locator("#graph").count() == 1
                focus_button.press("Escape")
                expect(focus_shell).to_have_class("jaal-viewer-shell", timeout=15000)
                expect(focus_button).to_have_attribute("aria-pressed", "false")
                expect(panel).to_be_visible()
                assert page.locator("#search_graph").count() == 1
                help_details.locator("summary").click()
                assert page.locator("#jaal-original-structural-hint").is_visible()
                help_details.locator("summary").click()
                assert not help_details.evaluate("(el) => el.open")
                assert page.locator(
                    "#jaal-original-layout-mode input[type=radio]"
                ).count() == 5
                assert page.get_by_label(
                    "網狀（社群收攏・Louvain）", exact=True
                ).is_enabled()
                assert page.get_by_label("網狀（收攏）", exact=True).is_disabled()
                assert page.get_by_label("階層（收攏）", exact=True).is_disabled()
                assert page.locator("#search_graph").count() == 1
                assert page.locator(
                    "#jaal-original-chinese-labels input[type=checkbox]"
                ).count() == 1

                community = page.get_by_label(
                    "網狀（社群收攏・Louvain）", exact=True
                )
                community.check(timeout=20000)
                assert community.is_checked()
                zh = page.locator(
                    "#jaal-original-chinese-labels input[type=checkbox]"
                )
                zh.check()
                assert zh.is_checked()
                page.locator("#search_graph").fill("Finance")
                assert page.locator(".vis-network canvas").first.is_visible()
                page.locator("#search_graph").fill("")
                page.get_by_label("階層（全展開）", exact=True).check()
                page.get_by_label("網狀（全展開）", exact=True).check()
                assert page.locator(".vis-network canvas").first.is_visible()
                # Switching cases reloads a fully independent Jaal app on the
                # same origin: original Search/Filter/Color callbacks, mode
                # eligibility and translated labels must be recomputed.
                picker = page.locator("#jaal-case-picker")
                # Dash can rerender this control after mode/label callbacks.
                # Wait for genuine visibility rather than sampling mid-render.
                expect(picker).to_be_visible(timeout=20000)

                def choose_case(text, url_suffix):
                    page.locator("#jaal-case-picker").click()
                    page.get_by_text(text, exact=True).last.click(timeout=20000)
                    page.wait_for_url(url + url_suffix, timeout=60000)
                    page.locator(".vis-network canvas").first.wait_for(
                        state="visible", timeout=90000
                    )
                    assert page.locator("#search_graph").count() == 1

                choose_case("公司組織階層樹（無環）", "/cases/org-tree/")
                expect(page.get_by_label("階層（收攏）", exact=True)).to_be_checked()
                assert page.get_by_label("階層（收攏）", exact=True).is_enabled()
                assert page.get_by_label("網狀（收攏）", exact=True).is_enabled()
                assert page.locator("#jaal-original-graph-profile").inner_text().find("樹狀階層") >= 0
                # Restores from the old mail-network without leaking its modes.
                choose_case("專案相依網路（多父 DAG）", "/cases/project-dag/")
                expect(page.get_by_label("階層（全展開）", exact=True)).to_be_checked()
                assert "無環 DAG" in page.locator("#jaal-original-graph-profile").inner_text()
                assert page.get_by_label("階層（收攏）", exact=True).is_enabled()
                choose_case("舊版通訊拓樸（類別樹改編）", "/cases/mail-network/")
                assert page.get_by_label("階層（收攏）", exact=True).is_disabled()
                assert page.get_by_label("網狀（社群收攏・Louvain）", exact=True).is_enabled()
                choose_case("企業郵件實務模擬（業務與事件）", "/")
                expect(page.get_by_label(
                    "網狀（社群收攏・Louvain）", exact=True
                )).to_be_checked()
                expect(page.locator("#jaal-case-picker")).to_be_visible(timeout=20000)
                page.locator("#jaal-original-help-details summary").click()
                assert "合成郵件收發量加權" in page.locator(
                    "#jaal-original-structural-hint"
                ).inner_text()
                assert page.get_by_role(
                    "link", name="下載模擬郵件事件 CSV"
                ).get_attribute("href") == "/demo/mail-events.csv"
                page.locator("#jaal-original-help-details summary").click()

                # Real temporal evolution: visible Louvain source DataSets
                # change with the selected interval; the source event series
                # remains intact. Tick animation must stay clientside.
                temporal = page.locator("#jaal-temporal-controls")
                assert temporal.is_visible()
                page.wait_for_function(
                    "() => Boolean(window.dash_clientside?.jaal_temporal?.lastRendered?.date)",
                    timeout=30000,
                )
                initial = page.evaluate(
                    "() => ({...window.dash_clientside.jaal_temporal.frame})"
                )
                assert initial["mode"] == "rolling"
                # Default rolling mode uses disjoint [start,end) bins.
                initial_status = page.locator("#jaal-temporal-status").inner_text()
                assert "互斥分段" in initial_status, initial_status
                assert "封信" in initial_status, initial_status
                assert page.get_by_label(
                    "固定社群（比較流量）", exact=True
                ).is_checked()
                assert not page.locator(
                    "#jaal-temporal-labels input[type=checkbox]"
                ).is_checked()
                # Compare the rolling slice against the cumulative history.
                page.get_by_label("累積至目前", exact=True).check()
                page.wait_for_function(
                    "() => window.dash_clientside?.jaal_temporal?.frame?.mode === 'cumulative'",
                    timeout=30000,
                )
                page.wait_for_function(
                    "() => window.dash_clientside?.jaal_temporal?.lastRendered?.sourceEdges === " +
                    "window.dash_clientside?.jaal_temporal?.frame?.links",
                    timeout=30000,
                )
                full = page.evaluate(
                    "() => ({...window.dash_clientside.jaal_temporal.lastRendered})"
                )
                full_messages = page.locator("#jaal-temporal-status").inner_text()
                assert "累積至目前" in full_messages
                assert "封信" in full_messages
                assert full["sourceEdges"] > 100, full

                page.get_by_label("滑動時間窗", exact=True).check()
                page.locator("#jaal-temporal-window").click()
                # Dash's dropdown virtualizes option rows (often rendered as
                # VirtualizedSelectOption, not the legacy .Select-option).
                # Select by visible text inside this specific control rather
                # than coupling the browser test to an internal CSS class.
                page.locator("#jaal-temporal-window").get_by_text(
                    "1 單位", exact=True
                ).last.click(timeout=15000)
                page.wait_for_function(
                    "() => window.dash_clientside?.jaal_temporal?.frame?.mode === 'rolling' && " +
                    "window.dash_clientside?.jaal_temporal?.frame?.window_minutes === 1440 && " +
                    "window.dash_clientside?.jaal_temporal?.frame?.from !== " +
                    "window.dash_clientside?.jaal_temporal?.frame?.to_exclusive",
                    timeout=30000,
                )
                day = page.evaluate(
                    "() => ({...window.dash_clientside.jaal_temporal.frame})"
                )
                page.wait_for_function(
                    "(d) => window.dash_clientside?.jaal_temporal?.lastRendered?.date === d",
                    arg=day["date"], timeout=30000,
                )
                actual = page.evaluate(
                    "() => ({...window.dash_clientside.jaal_temporal.lastRendered})"
                )
                assert actual["sourceEdges"] == day["links"]
                assert day["window_minutes"] == 1440
                assert "互斥分段" in page.locator("#jaal-temporal-status").inner_text()
                bar_before = page.locator("#jaal-temporal-window-highlight").evaluate(
                    "(el) => el.style.left"
                )
                assert day["messages"] > 0
                assert day["messages"] < 2000
                assert actual["sourceEdges"] < full["sourceEdges"], (actual, full)
                page.locator("#jaal-temporal-back").click()
                page.wait_for_function(
                    "(date) => window.dash_clientside?.jaal_temporal?.frame?.date !== date",
                    arg=day["date"], timeout=30000,
                )
                page.wait_for_function(
                    "() => window.dash_clientside?.jaal_temporal?.lastRendered?.date === " +
                    "window.dash_clientside?.jaal_temporal?.frame?.date",
                    timeout=30000,
                )
                bar_after = page.locator("#jaal-temporal-window-highlight").evaluate(
                    "(el) => el.style.left"
                )
                assert bar_after != bar_before, "current-window blue bar must move with playback"
                before_play = page.evaluate(
                    "() => window.dash_clientside.jaal_temporal.frame.date"
                )
                # After the user changed the analysis window, precomputation
                # ends. Playback ticks must NOT send new Flask/Vercel RPCs.
                page.wait_for_load_state("networkidle", timeout=20000)
                backend_ticks = []
                page.on("request", lambda req: backend_ticks.append(req.url)
                        if "/_dash-update-component" in req.url else None)
                page.locator("#jaal-temporal-play").click()
                expect(page.locator("#jaal-temporal-play")).to_have_text(
                    "⏸ 暫停", timeout=12000
                )
                page.wait_for_function(
                    "(date) => window.dash_clientside?.jaal_temporal?.frame?.date !== date",
                    arg=before_play, timeout=30000,
                )
                page.locator("#jaal-temporal-play").click()
                expect(page.locator("#jaal-temporal-play")).to_have_text(
                    "▶ 播放", timeout=12000
                )
                assert backend_ticks == [], backend_ticks

                # Visual regression from the reported Windows bug: manually
                # expand a real Louvain box, then advance temporal playback.
                # Source data, community ID, world coordinates, camera and
                # static directed edge shape must remain stable.
                page.evaluate("""() => {
                    const api=window.dash_clientside?.jaal_community_collapse;
                    if(!api || typeof api.activate !== 'function')
                        throw Error('Native Jaal community runtime missing');
                    const original=api.activate;
                    api.activate=function(...args) {
                        window.__temporalCommunityNetwork=this;
                        return original.apply(this,args);
                    };
                }""")
                page.locator("#jaal-temporal-back").click()
                page.wait_for_function(
                    "() => Boolean(window.__temporalCommunityNetwork?.__jaalCommunity?.view)",
                    timeout=30000)
                expanded = page.evaluate("""() => {
                    const c=window.__temporalCommunityNetwork;
                    const ids=Object.keys(c.__jaalCommunity.view.clusterToGroup);
                    if(!ids.length)throw Error('No collapsed community to expand');
                    const id=ids[0];
                    c.net.body.emitter.emit('click',{nodes:[id],edges:[]});
                    const state=c.__jaalCommunity;
                    const group=state.view.members ? state.partition[
                        Object.keys(state.partition)[0]] : null;
                    const positions=c.net.getPositions();
                    const nodes=c.nn.get().filter(n=>!n.hidden);
                    const visible=Object.fromEntries(nodes.map(n=>
                        [n.id,positions[n.id]]).filter(([,p])=>p));
                    return {opened:[...state.opened],ids:nodes.map(n=>n.id).sort(),
                        coords:visible,
                        camera:{position:c.net.getViewPosition(),scale:c.net.getScale()},
                        date:window.dash_clientside.jaal_temporal.lastRendered.date};
                }""")
                assert expanded["opened"] and expanded["coords"]
                assert len(expanded["ids"]) >= 3, expanded
                page.screenshot(path=str(ROOT / "browser-evidence" /
                                         "temporal-community-expanded-before-play.png"))
                page.locator("#jaal-temporal-play").click()
                page.wait_for_function(
                    "(date) => window.dash_clientside?.jaal_temporal?.lastRendered?.date !== date",
                    arg=expanded["date"],timeout=30000)
                page.locator("#jaal-temporal-play").click()
                stable = page.evaluate("""() => {
                    const c=window.__temporalCommunityNetwork;
                    const state=c.__jaalCommunity;
                    const pos=c.net.getPositions();
                    const nodes=c.nn.get().filter(n=>!n.hidden);
                    const selected=Object.fromEntries(nodes.map(n=>
                        [n.id,pos[n.id]]).filter(([,p])=>p));
                    const edges=c.ee.get().filter(e=>!e.hidden && e.from!==e.to);
                    return {opened:[...state.opened],ids:nodes.map(n=>n.id).sort(),
                        coords:selected,
                        staticCurves:edges.every(e=>e.smooth?.type==='curvedCW'),
                        camera:{position:c.net.getViewPosition(),scale:c.net.getScale()}};
                }""")
                assert stable["opened"] == expanded["opened"], stable
                assert stable["staticCurves"], "Dynamic edges produce hooks with physics disabled"
                # Some previously hidden nodes appear/disappear as time moves;
                # compare persistent visible IDs rather than demanding a
                # particular rolling window's active vertex count.
                shared = set(expanded["coords"]) & set(stable["coords"])
                assert len(shared) >= 2, (expanded,stable)
                for node in shared:
                    a,b=expanded["coords"][node],stable["coords"][node]
                    assert abs(a["x"]-b["x"]) < 1.1, (node,a,b)
                    assert abs(a["y"]-b["y"]) < 1.1, (node,a,b)
                a,b=expanded["camera"],stable["camera"]
                assert abs(a["scale"]-b["scale"]) < .02,(a,b)
                assert abs(a["position"]["x"]-b["position"]["x"]) < 2,(a,b)
                assert abs(a["position"]["y"]-b["position"]["y"]) < 2,(a,b)
                page.screenshot(path=str(ROOT / "browser-evidence" /
                                         "temporal-community-after-play.png"))
                # A static case never receives timeline controls.
                if errors:
                    raise AssertionError("Dash browser errors: " + repr(errors))
                print("VERCEL_REAL_JAAL_BROWSER_PASS")
                browser.close()
        finally:
            child.terminate()
            try:
                child.wait(timeout=8)
            except subprocess.TimeoutExpired:
                child.kill()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--port", type=int, default=8098)
    args = parser.parse_args()
    if args.serve:
        serve(args.port)
    else:
        check(args.port)
