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
    from app import app

    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)


def check(port):
    from playwright.sync_api import sync_playwright

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
                    raise AssertionError("WSGI entrypoint exited: " + str(child.returncode))
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
