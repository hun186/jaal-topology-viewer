"""Real Windows Chromium acceptance for private CSV import, IndexedDB and backup."""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def serve(port):
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from app import app
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


def check(port, evidence):
    from playwright.sync_api import sync_playwright, expect

    evidence.mkdir(parents=True, exist_ok=True)
    log = evidence / "local-cases-server.log"
    with log.open("w", encoding="utf-8") as output:
        child = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()),
             "--serve", "--port", str(port)],
            cwd=ROOT, stdout=output, stderr=subprocess.STDOUT,
        )
        try:
            base = "http://127.0.0.1:" + str(port)
            deadline = time.monotonic() + 90
            while time.monotonic() < deadline:
                if child.poll() is not None:
                    raise AssertionError("Flask runtime stopped: " + str(child.returncode))
                try:
                    with urlopen(base + "/my-cases/", timeout=3) as response:
                        if response.status == 200:
                            break
                except (OSError, URLError):
                    time.sleep(.5)
            else:
                raise AssertionError("Local workbench did not start")

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1480, "height": 980}, accept_downloads=True)
                errors, writes = [], []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("request", lambda req:
                    writes.append(req.method + " " + req.url)
                    if req.method not in ("GET", "HEAD") else None)
                page.goto(base + "/my-cases/", wait_until="domcontentloaded")
                expect(page.locator("#notice")).to_contain_text("IndexedDB")
                expect(page.locator("#library-count")).to_have_text("0 / 20", timeout=15000)
                page.screenshot(path=str(evidence / "01-empty-workspace.png"),
                                full_page=True)

                edge_data = "from,to,count\nAlice,Bob,3\nBob,Alice,1\nBob,Carol,2\nCarol,Dev,1\n"
                label_data = "ClassLabel,CT\nAlice,業務主管\nBob,營運組\nCarol,客服\nDev,研發\n"
                page.locator("#case-name").fill("跨部門郵件分析")
                page.locator("#edge-files").set_input_files({
                    "name": "edges.csv", "mimeType": "text/csv",
                    "buffer": edge_data.encode("utf-8")})
                page.locator("#labels-file").set_input_files({
                    "name": "labels.csv", "mimeType": "text/csv",
                    "buffer": label_data.encode("utf-8")})
                page.locator("#preview-btn").click()
                expect(page.locator("#count-nodes")).to_have_text("4")
                expect(page.locator("#count-edges")).to_have_text("4")
                expect(page.locator(".node-circle")).to_have_count(4)
                expect(page.locator("#active-name")).to_contain_text("尚未儲存")
                page.screenshot(path=str(evidence / "02-preview-graph.png"),
                                full_page=True)

                page.locator("#root-filter").fill("Alice")
                page.locator("#root-filter").press("Tab")
                page.locator("#direction").select_option("out")
                page.locator("#radius").select_option("1")
                expect(page.locator("#count-visible")).to_have_text("2 / 1")
                page.locator("#reset-view").click()
                expect(page.locator("#count-visible")).to_have_text("4 / 4")
                page.locator("#layout-mode").select_option("hierarchy")
                expect(page.locator(".node-circle")).to_have_count(4)
                page.screenshot(path=str(evidence / "03-hierarchy.png"),
                                full_page=True)

                page.locator("#save-btn").click()
                expect(page.locator("#library-count")).to_have_text("1 / 20")
                expect(page.locator("#save-btn")).to_be_disabled()
                page.reload(wait_until="domcontentloaded")
                expect(page.locator("#library-count")).to_have_text("1 / 20", timeout=15000)
                page.locator(".case-item").first.click()
                expect(page.locator("#count-nodes")).to_have_text("4")

                with page.expect_download() as result:
                    page.locator("#export-all").click()
                download = result.value
                assert download.suggested_filename.endswith(".json")
                backup_path = download.path()
                assert backup_path and backup_path.stat().st_size > 120
                page.get_by_role("button", name="刪除").first.click()
                # Browser confirm is dismissed by default in Playwright;
                # authorize deletion only in this synthetic acceptance case.
                # Use the explicit dialog handler below for the real test.
                expect(page.locator("#library-count")).to_have_text("1 / 20")
                page.once("dialog", lambda dialog: dialog.accept())
                page.get_by_role("button", name="刪除").first.click()
                expect(page.locator("#library-count")).to_have_text("0 / 20")
                page.locator("#restore-file").set_input_files(str(backup_path))
                expect(page.locator("#library-count")).to_have_text("1 / 20")
                page.locator(".case-item").first.click()
                expect(page.locator("#count-edges")).to_have_text("4")

                assert not writes, "Local workbench sent unexpected writes: " + str(writes)
                assert not errors, "Browser JavaScript errors: " + str(errors)
                (evidence / "local-cases-acceptance.txt").write_text(
                    "PASS: Real Chromium CSV import, optional Chinese labels, "
                    "2 layout modes, directed k-hop, graph reset, IndexedDB "
                    "reload persistence, export/delete/restore, zero HTTP writes. "
                    "Private workspace is a native SVG viewer, not the existing "
                    "Jaal five-mode/Louvain/temporal engine.\n", encoding="utf-8",
                )
                browser.close()
        finally:
            child.terminate()
            try:
                child.wait(timeout=8)
            except subprocess.TimeoutExpired:
                child.kill(); child.wait(timeout=8)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--port", type=int, default=8104)
    parser.add_argument("--evidence", type=Path, default=Path("browser-evidence/local-cases"))
    args = parser.parse_args()
    if args.serve:
        serve(args.port)
    else:
        check(args.port, args.evidence)
