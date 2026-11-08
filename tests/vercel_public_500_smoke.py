"""Validate the exact public Vercel capacity and response size without deployment.

Run with VERCEL=1. We also force JAAL_ENABLE_LARGE_LOCAL=1 to prove it
cannot expose 3k/5k/20k or the local three-islands case on the public server.
"""
from __future__ import annotations

import json
import os
import time
import sys
from pathlib import Path

# Running python tests/... sets sys.path[0] to tests/, not the repo root
# containing the Vercel WSGI app.py. Match our other standalone smokes.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

assert os.environ.get("VERCEL") == "1", "Vercel environment simulation required"
assert os.environ.get("JAAL_ENABLE_LARGE_LOCAL") == "1"
assert os.environ.get("JAAL_VERCEL_500_ENABLED", "1") == "1"

from app import (app, _CASES, _large_local_cases_enabled, _public_500_enabled)

LIMIT = 4_000_000  # leave margin below the 4.5 MB Vercel response limit
ROUTE = "/cases/scale-500/"
start = time.monotonic()

assert not _large_local_cases_enabled(dict(os.environ))
assert _public_500_enabled(dict(os.environ))
assert [c.key for c in _CASES] == [
    "mail-workflow", "mail-network", "org-tree", "project-dag", "scale-500"
]
mounted = app._jaal_topology_mounts
assert "/cases/scale-500" in mounted
assert mounted["/cases/scale-500"].application is None, "Must defer until visited"
assert not any(path in mounted for path in (
    "/cases/scale-3000", "/cases/scale-5000", "/cases/scale-20000",
    "/cases/scale-3000-dag", "/cases/scale-three-components",
))

client = app.test_client()
root = client.get("/_dash-layout")
assert root.status_code == 200
def find_id(value, sought):
    if isinstance(value, dict):
        if value.get("props", {}).get("id") == sought:
            return value["props"]
        for child in value.values():
            found = find_id(child, sought)
            if found is not None:
                return found
    if isinstance(value, list):
        for child in value:
            found = find_id(child, sought)
            if found is not None:
                return found
    return None

picker = find_id(root.get_json(), "jaal-case-picker")
assert picker is not None
choices = [c["value"] for c in picker["options"]]
assert len(choices) == 5 and ROUTE in choices, choices
assert not any("scale-" in value for value in choices if value != ROUTE)
assert mounted["/cases/scale-500"].application is None
assert client.get("/healthz").status_code == 200

page = client.get(ROUTE)
assert page.status_code == 200, page.status_code
layout = client.get(ROUTE + "_dash-layout")
dependencies = client.get(ROUTE + "_dash-dependencies")
assert layout.status_code == 200
assert dependencies.status_code == 200
assert mounted["/cases/scale-500"].application is not None
assert 0 < len(layout.data) < LIMIT, ("Dash layout exceeds response budget",
                                      len(layout.data), LIMIT)
assert 0 < len(dependencies.data) < LIMIT
layout_data = layout.get_json()
network = find_id(layout_data, "graph")
assert network is not None, "Must use the real native Jaal/visdcc graph"
assert len(network["data"]["nodes"]) == 500
assert len(network["data"]["edges"]) == 1168
assert find_id(layout_data, "jaal-temporal-controls") is not None
assert find_id(layout_data, "jaal-community-membership") is not None
assert find_id(layout_data, "jaal-local-root") is not None
assert find_id(layout_data, "search_graph") is not None
modes = find_id(layout_data, "jaal-original-layout-mode")
assert modes and len(modes["options"]) == 5
assert modes["value"] == "network-community-collapsed"
assert not any(c["value"] != ROUTE and "scale-" in c["value"]
               for c in find_id(layout_data, "jaal-case-picker")["options"])
assert client.get(ROUTE + "assets/18.jaal_community_collapse.js").status_code == 200
assert client.get(ROUTE + "assets/21.jaal_temporal_playback.js").status_code == 200

# Exercise the *actual Vercel Dash callback HTTP response*, not only the
# initial layout. Cumulative 3-hour windows over the full month previously
# generated 208 frames/122004 edges and >5.9 MB of response JSON.
from app import _public_500_case
from jaal_topology.data import GraphInputError

case = _public_500_case()
timeline = case.temporal_timeline
total_minutes = len(timeline.days) * 1440
assert timeline.max_payload_bytes == 3_600_000
try:
    timeline.interval_frames(
        start_minute=0, end_minute=total_minutes,
        mode="cumulative", window_minutes=180, step_minutes=180,
    )
except GraphInputError as exc:
    assert "公網回應上限" in str(exc), str(exc)
else:
    raise AssertionError("Unbounded cumulative 3h callback must fail closed")

def temporal_update(mode, unit, length, overlap):
    body = {
        "output": "jaal-temporal-frames.data",
        "outputs": {"id":"jaal-temporal-frames","property":"data"},
        "inputs": [
            {"id":"jaal-temporal-range","property":"value",
             "value":[0,total_minutes]},
            {"id":"jaal-temporal-mode","property":"value","value":mode},
            {"id":"jaal-temporal-unit","property":"value","value":unit},
            {"id":"jaal-temporal-window","property":"value","value":length},
            {"id":"jaal-temporal-overlap","property":"value","value":overlap},
            {"id":"jaal-temporal-step","property":"value","value":1},
        ],
        "state": [],
        "changedPropIds": ["jaal-temporal-mode.value"],
    }
    response=client.post(ROUTE+"_dash-update-component",json=body)
    assert response.status_code==200,(response.status_code,response.data[:1200])
    assert len(response.data)<LIMIT,("Oversized callback response",len(response.data))
    data=response.get_json()["response"]["jaal-temporal-frames"]["data"]
    return data,len(response.data)

error_packet,error_bytes=temporal_update("cumulative",180,1,"disjoint")
assert error_packet["frames"] == [],error_packet
assert "公網回應上限" in error_packet["error"],error_packet
valid_packet,valid_bytes=temporal_update("rolling",1440,3,"disjoint")
assert len(valid_packet["frames"])>=1 and not valid_packet.get("error")
assert valid_bytes<LIMIT
print("VERCEL_PUBLIC_500_TEMPORAL_BUDGET_PASS",
      json.dumps({"blocked_callback_bytes":error_bytes,
                  "safe_callback_bytes":valid_bytes,
                  "safe_frames":len(valid_packet["frames"])},
                 ensure_ascii=False),flush=True)
print("VERCEL_PUBLIC_500_WSGI_PASS",
      json.dumps({"cases":len(choices),"nodes":len(network["data"]["nodes"]),
                  "edges":len(network["data"]["edges"]),
                  "layout_bytes":len(layout.data),
                  "dependencies_bytes":len(dependencies.data),
                  "elapsed_seconds":round(time.monotonic()-start,2)},
                 ensure_ascii=False),flush=True)
