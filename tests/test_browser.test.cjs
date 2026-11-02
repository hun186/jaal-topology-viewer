"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const {apply} = require("../jaal_topology/assets/16.jaal_visible_labels.js");
const collapsed = require("../jaal_topology/assets/17.jaal_structural_collapse.js");

test("portable engine exports four active layout commands", () => {
  const g = {nodes: [{id: "Root"}, {id: "Leaf"}],
             edges: [{id: "e1", from: "Root", to: "Leaf"}]};
  for (const mode of ["network", "hierarchical",
                      "network-collapsed", "hierarchical-collapsed"]) {
    const command = apply(mode, g, ["zh"], {Root: "根"});
    assert.equal(typeof command, "string");
    assert.ok(command.includes("this"));
    assert.ok(!command.includes("根"), "CSV text must never enter JS source");
  }
});

test("multi-parent directed graph remains an exact unique-descendant graph", () => {
  const graph = collapsed.graphModel({
    nodes: ["A","B","C","D"].map(id => ({id})),
    edges: [["A","B"],["A","C"],["B","D"],["C","D"]]
      .map(([from,to],i) => ({id:String(i),from,to}))
  });
  assert.equal(graph.uniqueDescendants("A"), 3);
  assert.equal(graph.uniqueDescendants("B"), 1);
  assert.equal(graph.uniqueDescendants("D"), 0);
});

const community = require("../jaal_topology/assets/18.jaal_community_collapse.js");

test("community quotient retains both directed totals, self-internal edges and original IDs", () => {
  const nodes = ["A", "B", "C", "D", "E", "F", "G",
    "__jaal_internal_community__0"].map(id => ({id, label: id}));
  const edges = [
    ["A", "D"], ["B", "D"], ["D", "A"], ["C", "B"],
    ["G", "A"], ["E", "F"], ["D", "E"]
  ].map(([from, to], i) => ({id: "e" + i, from, to}));
  const input = {nodes, edges};
  const membership = {
    A:"community-0", B:"community-0", C:"community-0",
    D:"community-1", E:"community-1", F:"community-1",
    G:"community-2"
  };
  const view = community.makeView(input, membership, new Set(), false);
  const group0 = Object.keys(view.clusterToGroup).find(
    id => view.clusterToGroup[id] === "community-0"
  );
  const group1 = Object.keys(view.clusterToGroup).find(
    id => view.clusterToGroup[id] === "community-1"
  );
  assert.ok(group0 && group1);
  assert.ok(!input.nodes.some(n => n.id === group0));
  assert.ok(!input.nodes.some(n => n.id === group1));
  const from0to1 = [...view.aggregated.values()].find(
    p => p.from === group0 && p.to === group1
  );
  const from1to0 = [...view.aggregated.values()].find(
    p => p.from === group1 && p.to === group0
  );
  assert.equal(from0to1.originals.length, 2);
  assert.equal(from1to0.originals.length, 1);
  const total = [...view.aggregated.values()].reduce(
    (n, p) => n + p.originals.length, 0
  ) + [...view.internal.values()].reduce((a,b) => a+b,0);
  assert.equal(total, edges.length);
  assert.deepEqual(input.nodes, nodes);
  assert.deepEqual(input.edges, edges);
  const opened = community.makeView(input, membership, new Set(["community-0"]), true);
  assert.ok(opened.nodes.some(n => n.id === "A"));
  assert.ok(!opened.nodes.some(n => n.id === group0));
});

test("community activation and restoration preserve original DataSets and camera", () => {
  const source = {
    nodes: ["A","B","C","D","E","F"].map(id => ({id, label: id})),
    edges: [["A","D"],["B","D"],["D","A"],["C","B"]]
      .map(([from,to],i) => ({id:"edge-"+i,from,to, arrows:"to"})),
  };
  const dataset = rows => {
    const cache = new Map(rows.map(row => [row.id, {...row}]));
    return {
      getIds: () => [...cache.keys()],
      get: () => [...cache.values()],
      remove: ids => ids.forEach(id => cache.delete(id)),
      update: rows => rows.forEach(row => cache.set(row.id, {...cache.get(row.id), ...row})),
    };
  };
  let moved = 0, click;
  const positions = Object.fromEntries(source.nodes.map((n,i) =>
    [n.id,{x:i*10,y:0}]));
  const instance = {
    props: {data: source},
    nn: dataset(source.nodes), ee: dataset(source.edges),
    net: {
      on: (type, fn) => {if (type === "click") click = fn;},
      getPositions: () => ({...positions}),
      getViewPosition: () => ({x: 10, y: 10}),
      getScale: () => 0.9,
      moveTo: () => {moved++;},
    },
  };
  community.partition = {
    A:"community-0",B:"community-0",C:"community-0",
    D:"community-1",E:"community-1",F:"community-1",
  };
  community.activate.call(instance);
  assert.equal(instance.nn.getIds().length, 2);
  assert.ok(moved > 0);
  const firstCluster = Object.keys(instance.__jaalCommunity.view.clusterToGroup)
    .find(id => instance.__jaalCommunity.view.clusterToGroup[id] === "community-0");
  const secondCluster = Object.keys(instance.__jaalCommunity.view.clusterToGroup)
    .find(id => instance.__jaalCommunity.view.clusterToGroup[id] === "community-1");
  positions[secondCluster] = {x:800, y:800}; // User drags this cluster
  click({nodes:[firstCluster]});
  assert.equal(instance.nn.getIds().length, 4);
  const stable = instance.nn.get().find(node => node.id === secondCluster);
  assert.equal(stable.x, 800);
  assert.equal(stable.y, 800);
  community.restore.call(instance);
  // Display x/y are intentionally retained for camera stability; identity,
  // label, hidden state and exact directed edges must be restored.
  const withoutCoordinates = rows => rows.map(({x, y, ...row}) => row);
  assert.deepEqual(withoutCoordinates(instance.nn.get().sort((a,b)=>a.id.localeCompare(b.id))),
    source.nodes.map(n => ({...n, hidden:false})));
  assert.deepEqual(instance.ee.get().sort((a,b)=>a.id.localeCompare(b.id)),
    source.edges.map(e => ({...e, hidden:false})));
  // A new Search payload with hidden flags must never retain stale clusters.
  source.nodes[0].hidden = true;
  community.activate.call(instance);
  assert.equal(instance.nn.getIds().length, 6);
  source.nodes[0].hidden = false;
  community.activate.call(instance);
  assert.equal(instance.nn.getIds().length, 2);
  community.restore.call(instance);
  assert.equal(instance.nn.get().find(n => n.id === "A").hidden, false);
});

test("real self-loops survive and prototype-like node IDs stay literal", () => {
  const ids = ["__proto__", "constructor", "toString", "A", "B", "C"];
  const graph = {
    nodes: ids.map(id => ({id, label:id})),
    edges: [
      {id:"self", from:"__proto__", to:"__proto__"},
      {id:"incoming", from:"A", to:"__proto__"},
      {id:"outgoing", from:"__proto__", to:"constructor"},
      {id:"internal", from:"A", to:"B"},
    ],
  };
  const memberships = Object.create(null);
  for (const id of ["A", "B", "C"]) memberships[id] = "community-1";
  memberships.__proto__ = "community-2";
  memberships.constructor = "community-3";
  memberships.toString = "community-4";
  const result = community.makeView(graph, memberships, new Set(), false);
  assert.equal(result.representative["__proto__"], "__proto__");
  assert.equal(result.representative["constructor"], "constructor");
  assert.ok(result.edges.some(edge =>
    edge.from === "__proto__" && edge.to === "__proto__"));
  assert.ok(result.edges.some(edge =>
    edge.from === "__proto__" && edge.to === "constructor"));
  assert.ok(result.edges.every(edge =>
    typeof edge.from === "string" && typeof edge.to === "string"));
  const uncollapsed = community.makeView(
    graph, memberships, new Set(["community-1"]), false
  );
  assert.ok(uncollapsed.edges.some(edge => edge.id === "self"));
  assert.ok(uncollapsed.edges.some(edge => edge.id === "internal"));
});


test("filtered community views keep Chinese labels through Search/Filter and language toggles", () => {
  const source = {
    nodes: ["A", "B", "C"].map(id => ({id, label: id})),
    edges: [{id:"eAB", from:"A", to:"B", arrows:"to"}],
  };
  const dataset = rows => {
    const cache = new Map(rows.map(row => [row.id, {...row}]));
    return {
      getIds: () => [...cache.keys()],
      get: () => [...cache.values()],
      remove: ids => ids.forEach(id => cache.delete(id)),
      update: rows => rows.forEach(row =>
        cache.set(row.id, {...cache.get(row.id), ...row})),
    };
  };
  const instance = {
    props: {data: source}, nn: dataset(source.nodes), ee: dataset(source.edges),
    net: {
      on: () => {},
      getPositions: () => ({}),
      getViewPosition: () => ({x:0, y:0}),
      getScale: () => 1,
      moveTo: () => {},
    },
  };
  const membership = {A:"group-0", B:"group-0", C:"group-0"};
  const translated = {A:"甲", B:"乙", C:"丙"};
  function render(mode, languages) {
    const command = apply(mode, source, languages, translated, membership);
    // Exercise the actual static visdcc command created by apply().
    Function(command).call(instance);
  }
  // Search/Filter flags originate from the upstream graph and must be kept.
  source.nodes[0].hidden = true;
  source.edges[0].hidden = true;
  render("network-community-collapsed", ["zh"]);
  assert.equal(instance.__jaalCommunity.filtered, true);
  assert.deepEqual(instance.nn.get().map(n => [n.id, n.label, n.hidden]), [
    ["A", "甲", true], ["B", "乙", false], ["C", "丙", false],
  ]);
  assert.equal(instance.ee.get()[0].hidden, true);
  render("network-community-collapsed", []);
  assert.deepEqual(instance.nn.get().map(n => n.label), ["A", "B", "C"]);
  render("network-community-collapsed", ["zh"]);
  assert.deepEqual(instance.nn.get().map(n => n.label), ["甲", "乙", "丙"]);
  // Clearing the filter should restore the community quotient (not stale nodes).
  source.nodes[0].hidden = false;
  source.edges[0].hidden = false;
  render("network-community-collapsed", ["zh"]);
  assert.equal(instance.__jaalCommunity.filtered, false);
  assert.equal(instance.nn.getIds().length, 1);
  // Filtering again must restore original IDs with Chinese display labels.
  source.nodes[1].hidden = true;
  render("network-community-collapsed", ["zh"]);
  assert.equal(instance.nn.getIds().length, 3);
  assert.equal(instance.nn.get().find(n => n.id === "B").label, "乙");
  assert.equal(instance.nn.get().find(n => n.id === "B").hidden, true);
  render("network", ["zh"]);
  assert.deepEqual(instance.nn.get().map(n => n.label), ["甲", "乙", "丙"]);
  assert.equal(instance.__jaalCommunity.active, false);
  assert.deepEqual(source.nodes.map(n => n.label), ["A", "B", "C"]);
});
