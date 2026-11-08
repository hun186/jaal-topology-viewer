"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const core = require("../jaal_topology/stress_lab/scale_core.js");

test("all four requested full corporate scenarios have exact node counts and realistic hierarchies", () => {
  for (const size of [500, 3000, 5000, 20000]) {
    const graph = core.buildScenario(String(size));
    assert.equal(graph.nodes.length, size);
    assert.equal(graph.components, 1);
    assert.deepEqual(core.weakComponentSizes(graph), [size]);
    assert.ok(graph.edges.length > size, "real peer and management traffic");
    assert.ok(graph.edges.length < core.MAX_EDGES);
    assert.ok(graph.departments.length >= Math.floor(size / 100));
    assert.equal(graph.nodes[0].kind, "executive");
    assert.ok(graph.nodes.some(n => n.kind === "department"));
    assert.ok(graph.nodes.some(n => n.kind === "team"));
    assert.ok(graph.nodes.some(n => n.kind === "staff"));
    assert.equal(new Set(graph.nodes.map(n => n.id)).size, size);
    assert.equal(new Set(graph.edges.map(e => e.source + ":" + e.target)).size,
      graph.edges.length, "unique directed sender/recipient pairs");
    assert.ok(graph.edges.every(e => e.source !== e.target &&
      Number.isSafeInteger(e.weight) && e.weight > 0));
    assert.ok(graph.edges.every(e => graph.nodes[e.source].component ===
      graph.nodes[e.target].component));
    assert.equal(graph.edges.reduce((sum, e) => sum + e.weight, 0),
      graph.weightTotal);
    assert.ok(graph.departments.every(dept => dept.count > 10));
    if (size === 500) assert.ok(graph.maxDepth >= 5);
    if (size === 3000 || size === 5000) assert.ok(graph.maxDepth >= 6);
    if (size === 20000) assert.ok(graph.maxDepth >= 7);
  }
});

test("three disconnected components are genuine weakly isolated companies", () => {
  const graph = core.buildScenario("islands");
  assert.equal(graph.nodes.length, 500);
  assert.equal(graph.components, 3);
  assert.deepEqual(core.weakComponentSizes(graph), [167, 167, 166]);
  assert.equal(new Set(graph.nodes.map(n => n.component)).size, 3);
  for (const edge of graph.edges) {
    assert.equal(graph.nodes[edge.source].component,
      graph.nodes[edge.target].component);
  }
  assert.equal(graph.departments.length >= 9, true);
});

test("synthetic edges are fixed, flow directions are not invented and presets reject arbitrary sizes", () => {
  const first=core.buildScenario("500"), second=core.buildScenario("500");
  assert.deepEqual(first, second);
  assert.ok(first.edges.some(e => e.workflow === "report"));
  assert.ok(first.edges.some(e => e.workflow === "reply"));
  assert.ok(first.edges.some(e => e.workflow === "team"));
  assert.ok(first.edges.some(e => e.workflow === "cross-department"));
  const pair=first.edges.find(e => e.workflow === "report");
  assert.equal(first.nodes[pair.source].manager, pair.target);
  assert.throws(() => core.buildScenario("99999"),/只允許/);
  assert.throws(() => core.buildScenario("__proto__"),/只允許/);
});

test("local view is direction-aware and capped without mutating full data", () => {
  const graph=core.buildScenario("3000"), start=graph.departments[0].head;
  const original=graph.edges.length;
  const incoming=core.selectLocal(graph,start,1,"in");
  const outgoing=core.selectLocal(graph,start,1,"out");
  assert.ok(incoming.indices.size > 1);
  assert.ok(outgoing.indices.size > 1);
  assert.notDeepEqual([...incoming.indices].sort(), [...outgoing.indices].sort());
  const restricted=core.selectLocal(graph,0,3,"both",30);
  assert.ok(restricted.indices.size <= 30);
  assert.equal(restricted.limited, true);
  assert.equal(graph.edges.length,original);
  assert.throws(() => core.selectLocal(graph,-1,2,"both"),/無效/);
  assert.throws(() => core.selectLocal(graph,start,99,"both"),/無效/);
});
