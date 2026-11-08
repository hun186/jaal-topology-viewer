"""Opt-in heavy CI smoke: real Jaal/Dash 20k/44k source, not a mock.

Run in a dedicated job rather than every Dash-major test matrix; initial
loading is the very expensive operation the customer wants to evaluate.
"""
from __future__ import annotations
import json
import time

from jaal_topology.scaled_demo import build_scaled_email_demo
from jaal_topology.temporal import TemporalTimeline
from jaal_topology.viewer import build_app

start=time.perf_counter()
dataset=build_scaled_email_demo("20000")
print("20K_BUILT_GRAPH",len(dataset.graph.nodes),len(dataset.graph.edges),
      "departments",dataset.departments,flush=True)
assert len(dataset.graph.nodes)==20_000
assert dataset.components==(20_000,)
assert len(dataset.graph.edges)>40_000
timeline=TemporalTimeline(dataset.graph,dataset.events,allow_large_demo=True)
t1=time.perf_counter()
viewer=build_app(dataset.graph,initial_mode="network-community-collapsed",
                 temporal_timeline=timeline,allow_large_demo=True,
                 initial_positions=dataset.positions)
print("20K_BUILT_REAL_JAAL",round(time.perf_counter()-t1,2),flush=True)
client=viewer.server.test_client()
res=client.get("/_dash-layout")
assert res.status_code==200,res.status_code
payload=res.get_json()
serialized=json.dumps(payload,ensure_ascii=False)
for required in ("jaal-original-layout-mode","jaal-temporal-controls",
                 "jaal-community-membership","jaal-local-root","search_graph",
                 "C01-N20000"):
    assert required in serialized,required
for value in ("network","network-collapsed","network-community-collapsed",
              "hierarchical","hierarchical-collapsed"):
    assert value in serialized,value
assert client.get("/_dash-dependencies").status_code==200
print("20K_REAL_JAAL_DASH_HTTP_PASS",
      "layout_bytes",len(res.data),"elapsed_s",round(time.perf_counter()-start,2),
      flush=True)
