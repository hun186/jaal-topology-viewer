"""Chromium acceptance for the PUBLIC, CLIENT-ONLY Vercel PoC, with no deployment."""
from __future__ import annotations

from contextlib import contextmanager
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import sync_playwright

DIST = Path(__file__).resolve().parents[1] / "vercel-poc" / "dist"


@contextmanager
def serve_static():
    if not (DIST / "index.html").is_file() or not (DIST / "graph.json").is_file():
        raise AssertionError("Build PoC with node vercel-poc/build.mjs first")
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(DIST), **kwargs)

        def log_message(self, fmt, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def main():
    errors = []
    with serve_static() as url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(viewport={"width": 1365, "height": 930})
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(url, wait_until="networkidle", timeout=45000)
            page.wait_for_function("document.getElementById('nodeTotal').textContent === '77'", timeout=15000)
            assert page.locator("#edgeTotal").inner_text() == "169"
            assert page.locator("#visibleNodes").inner_text() == "77"
            assert page.locator("svg .graph-node").count() == 77

            # English node IDs are immutable; Chinese is only a display toggle.
            page.locator("#search").fill("CEO / Executive Office")
            assert page.locator("svg .graph-node.faded").count() > 0
            node = page.locator('svg .graph-node[data-id="CEO / Executive Office"]')
            node.click()
            assert "執行長" in page.locator("#detailTitle").inner_text()
            assert page.locator("#detailBody").inner_text() == "CEO / Executive Office"
            page.locator("#chinese").uncheck()
            assert page.locator("#detailTitle").inner_text() == "CEO / Executive Office"
            page.locator("#search").fill("")

            # Hierarchy may contain cycles and cross-links: never infer reporting claims.
            page.get_by_role("button", name="階層視圖").click()
            assert page.locator("#visibleNodes").inner_text() == "77"
            page.get_by_role("button", name="部門收攏示意").click()
            collapsed = int(page.locator("#visibleNodes").inner_text())
            assert 0 < collapsed < 77
            cluster = page.locator("svg .graph-node.cluster").first
            cluster.click()
            assert int(page.locator("#visibleNodes").inner_text()) > collapsed
            assert page.locator("#edgeTotal").inner_text() == "169"
            page.get_by_role("button", name="網狀全展開").click()
            assert page.locator("#visibleNodes").inner_text() == "77"
            assert page.locator("svg .edge").count() == 169

            page.locator("#graph").hover()
            page.mouse.wheel(0, -120)
            assert "scale(1.1)" in page.locator("#graph g[transform]").first.get_attribute("transform")
            page.get_by_role("button", name="重設視野").click()
            assert "scale(1)" in page.locator("#graph g[transform]").first.get_attribute("transform")

            assert not errors, "Browser errors: " + repr(errors)
            print("VERCEL_POC_CHROMIUM_ACCEPTANCE_PASS 77 nodes 169 edges")
        finally:
            browser.close()


if __name__ == "__main__":
    main()
