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
                assert frame.locator("#jaal-original-chinese-labels input[type=checkbox]").count() == 1
                assert frame.locator("#search_graph").count() == 1
                # Vis.js really created a nonzero-size canvas inside the embedded Dash app.
                size = frame.locator(".vis-network canvas").first.bounding_box()
                assert size and size["width"] > 100 and size["height"] > 100, size
                page.screenshot(path=str(evidence / "01-network.png"), full_page=True)

                def choose(mode: str) -> None:
                    radio = frame.locator(
                        f'#jaal-original-layout-mode input[type=radio][value="{mode}"]'
                    )
                    radio.check(timeout=20000)
                    assert radio.is_checked()
                    page.wait_for_timeout(900)

                choose("network-community-collapsed")
                checkbox = frame.locator(
                    "#jaal-original-chinese-labels input[type=checkbox]"
                )
                checkbox.check()
                assert checkbox.is_checked()
                page.wait_for_timeout(900)
                assert frame.locator(".vis-network canvas").first.is_visible()
                page.screenshot(path=str(evidence / "02-community-chinese.png"), full_page=True)

                # Real user Search interaction, not a mocked callback or HTTP-only smoke.
                search = frame.locator("#search_graph")
                search.fill("Finance")
                page.wait_for_timeout(1200)
                assert frame.locator(".vis-network canvas").first.is_visible()
                page.screenshot(path=str(evidence / "03-search-chinese.png"), full_page=True)
                search.fill("")
                page.wait_for_timeout(800)
                checkbox.uncheck()
                choose("hierarchical-collapsed")
                page.screenshot(path=str(evidence / "04-hierarchy-collapsed.png"), full_page=True)
                choose("network")
                assert frame.locator(".vis-network canvas").first.is_visible()
                if errors:
                    raise AssertionError("Browser JavaScript errors: " + " | ".join(errors))
                (evidence / "acceptance-summary.txt").write_text(
                    "PASS: Windows Chromium hosted real Dash canvas, same-port iframe, "
                    "five radios, Chinese checkbox, live Search, mode switching and "
                    "all packaged assets. Screenshots are inspection evidence; "
                    "manual Windows Stage 4/drag/camera/Color/Size acceptance is "
                    "NOT asserted.\n",
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
