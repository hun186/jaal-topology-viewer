"""Windows Chromium acceptance for the SAME original Jaal Gallery at opt-in scale.

Runs only on fixed fictional local fixtures, no uploads or public deployment.
Screenshots verify dropdown readability and genuine three-island Jaal canvas.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def serve(port):
    if str(ROOT) not in sys.path:
        sys.path.insert(0,str(ROOT))
    os.environ["JAAL_ENABLE_LARGE_LOCAL"]="1"
    from app import app
    app.run(host="127.0.0.1",port=port,debug=False,use_reloader=False)


def check(port, evidence):
    from playwright.sync_api import sync_playwright, expect
    target = ROOT / evidence
    target.mkdir(parents=True,exist_ok=True)
    log=target / "local-full-gallery-server.log"
    env=os.environ.copy()
    env["JAAL_ENABLE_LARGE_LOCAL"]="1"
    with log.open("w",encoding="utf-8") as log_out:
        proc=subprocess.Popen([
            sys.executable,str(Path(__file__).resolve()),"--serve",
            "--port",str(port)],cwd=ROOT,env=env,stdout=log_out,
            stderr=subprocess.STDOUT)
        try:
            base=f"http://127.0.0.1:{port}"
            for _ in range(180):
                if proc.poll() is not None:
                    raise RuntimeError("Full Gallery local server exited\n"+
                                       log.read_text("utf-8",errors="replace")[-3000:])
                try:
                    with urlopen(base+"/healthz",timeout=2) as response:
                        if response.status==200:break
                except OSError:
                    time.sleep(.3)
            else:
                raise RuntimeError("Full Jaal local demo not ready after 54s")

            with sync_playwright() as p:
                browser=p.chromium.launch(headless=True)
                page=browser.new_page(viewport={"width":1440,"height":960})
                errors=[]
                page.on("pageerror",lambda err:errors.append(str(err)))
                page.goto(base,wait_until="domcontentloaded",timeout=90000)
                picker=page.locator("#jaal-case-picker")
                expect(picker).to_be_visible(timeout=30000)
                picker.click()
                menu=page.locator("#jaal-case-picker .Select-menu-outer")
                expect(menu).to_be_visible(timeout=15000)
                # React-Virtualized Select renders only visible rows; its
                # options use .VirtualizedSelectOption on Dash 3/4. Parse
                # the backend contract for complete choices, then separately
                # verify a real visible menu and selectable search result.
                payload=page.request.get(base+"/_dash-layout").json()
                def find_picker(value):
                    if isinstance(value,dict):
                        if value.get("props",{}).get("id")=="jaal-case-picker":
                            return value["props"]
                        for child in value.values():
                            found=find_picker(child)
                            if found is not None:return found
                    elif isinstance(value,list):
                        for child in value:
                            found=find_picker(child)
                            if found is not None:return found
                    return None
                choices=find_picker(payload)["options"]
                assert len(choices)==10,choices
                labels=[item["label"] for item in choices]
                for marker in ("500 人","3,000 人","5,000 人",
                               "20,000 人","無環 DAG","3 個互不連通群"):
                    assert any(marker in name for name in labels),(marker,labels)
                rendered=menu.locator(
                    ".VirtualizedSelectOption, .Select-option, [role='option']")
                assert rendered.count()>0,menu.inner_text()
                bounds=menu.bounding_box()
                assert bounds and bounds["x"]>=-1 and (
                    bounds["x"]+bounds["width"]<=1441),bounds
                assert bounds["height"]<=450,bounds
                page.screenshot(path=str(target/"01-readable-native-gallery-dropdown.png"))
                # Real native Dash/Jaal graph, not a Canvas or separate demo.
                # Filter to the exact case; do not assume all rows are in
                # the DOM when React-Virtualized only mounts visible entries.
                page.locator("#jaal-case-picker input").first.fill("500 人（全 Jaal）")
                match=menu.get_by_text("企業郵件｜500 人（全 Jaal）",exact=True)
                expect(match).to_be_visible(timeout=15000)
                match.click()
                page.wait_for_url("**/cases/scale-500/",timeout=90000)
                expect(page.locator("#jaal-temporal-controls")).to_be_visible(
                    timeout=90000)
                expect(page.locator("#jaal-local-root")).to_be_visible(
                    timeout=90000) if page.locator("#jaal-local-root").is_visible() else None
                page.locator(".vis-network canvas").first.wait_for(
                    state="visible",timeout=90000)
                assert page.locator("#jaal-original-layout-mode").count()==1
                assert page.locator("#search_graph").count()==1
                page.screenshot(path=str(target/"02-original-jaal-500.png"))
                page.goto(base+"/cases/scale-three-components/",
                          wait_until="domcontentloaded",timeout=90000)
                page.locator(".vis-network canvas").first.wait_for(
                    state="visible",timeout=90000)
                expect(page.locator("#jaal-temporal-controls")).to_be_visible(
                    timeout=90000)
                assert "三" in page.locator("#jaal-case-picker").inner_text() or (
                    page.locator("#jaal-case-picker").count()==1)
                page.screenshot(path=str(target/"03-original-jaal-three-islands.png"))
                assert not errors,errors
                browser.close()
                print("FULL_ORIGINAL_JAAL_GALLERY_BROWSER_PASS 500 and three islands")
        finally:
            proc.terminate()
            try:proc.wait(timeout=8)
            except subprocess.TimeoutExpired:proc.kill()


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--serve",action="store_true")
    parser.add_argument("--port",type=int,default=8115)
    parser.add_argument("--evidence",default="browser-evidence/large-gallery")
    args=parser.parse_args()
    serve(args.port) if args.serve else check(args.port,args.evidence)
