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

test("cyclic graph injection cannot emit a descendant-collapse visdcc command", () => {
  const graph = {
    nodes: ["A", "B", "C"].map(id => ({id, label: id})),
    edges: [["A", "B"], ["B", "C"], ["C", "A"]]
      .map(([from, to], i) => ({id: String(i), from, to})),
  };
  for (const mode of ["network-collapsed", "hierarchical-collapsed"]) {
    const blocked = apply(mode, graph, [], {}, {}, false);
    assert.ok(blocked.includes("var ds = this.nn"));
    assert.ok(!blocked.includes("jaal_structural_collapse.activate"));
    const allowed = apply(mode, graph, [], {}, {}, true);
    assert.ok(allowed.includes("jaal_structural_collapse.activate"));
    // Older five-argument call sites continue to receive the old behavior.
    assert.ok(apply(mode, graph, [], {}, {}).includes(
      "jaal_structural_collapse.activate"
    ));
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
  const drawn01 = view.edges.find(e => e.from === group0 && e.to === group1);
  const drawn10 = view.edges.find(e => e.from === group1 && e.to === group0);
  assert.deepEqual(
    community.explainEdge(view, drawn01.id).map(e => [e.from, e.to]),
    [["A", "D"], ["B", "D"]],
  );
  assert.deepEqual(
    community.explainEdge(view, drawn10.id).map(e => [e.from, e.to]),
    [["D", "A"]],
  );
  assert.deepEqual(community.explainEdge(view, "missing"), []);
  assert.match(view.nodes.find(n => n.id === group0).label, /個節點/);
  assert.ok(!view.nodes.find(n => n.id === group0).label.includes(" 人"));
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

test("quotient edge provenance keeps HTML-looking IDs literal", () => {
  const original = {
    nodes: ["<img src=x onerror=alert(1)>", "X", "Y", "Z", "P", "Q"]
      .map(id => ({id, label: id})),
    edges: [
      {id:"e1",from:"<img src=x onerror=alert(1)>",to:"Z"},
      {id:"e2",from:"X",to:"Z"},
    ],
  };
  const membership = Object.assign(Object.create(null), {
    "<img src=x onerror=alert(1)>":"a", X:"a",Y:"a",
    Z:"b",P:"b",Q:"b",
  });
  const view = community.makeView(original, membership, new Set(), false);
  const edge = view.edges.find(x => String(x.id).startsWith("__jaal_internal_link__"));
  assert.ok(edge);
  assert.equal(community.explainEdge(view, edge.id)[0].from,
               "<img src=x onerror=alert(1)>");
  assert.deepEqual(original.nodes.map(n => n.id), [
    "<img src=x onerror=alert(1)>", "X", "Y", "Z", "P", "Q",
  ]);
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

test("expanded community nodes stay near the previously drawn box and re-collapse in place", () => {
  const source = {
    nodes: ["A","B","C","D","E","F"].map(id => ({id,label:id})),
    edges: [
      ["A","D"],["B","E"],["C","F"],["A","B"],["D","E"],
    ].map(([from,to],i) => ({id:"edge"+i,from,to})),
  };
  const memory = new Map(source.nodes.map((node,i) =>
    [node.id,{...node,x:i*250-750,y:(i%2)*200}]));
  const nn = {
    getIds:()=>[...memory.keys()], get:()=>[...memory.values()],
    remove:ids=>ids.forEach(id=>memory.delete(id)),
    update:items=>items.forEach(n=>memory.set(String(n.id),{...memory.get(String(n.id)),...n})),
  };
  const links = new Map(source.edges.map(e=>[e.id,{...e}]));
  const ee = {
    getIds:()=>[...links.keys()], get:()=>[...links.values()],
    remove:ids=>ids.forEach(id=>links.delete(id)),
    update:items=>items.forEach(e=>links.set(String(e.id),{...links.get(String(e.id)),...e})),
  };
  let click;
  const net = {
    on:(type,cb)=>{if(type==="click")click=cb;},
    getPositions:()=>Object.fromEntries(nn.get().map(n=>
      [n.id,{x:n.x??0,y:n.y??0}])),
    getViewPosition:()=>({x:100,y:50}),
    getScale:()=>0.9, moveTo:()=>{},
  };
  const instance={nn,ee,props:{data:source},net};
  community.partition={
    A:"team-0",B:"team-0",C:"team-0",
    D:"team-1",E:"team-1",F:"team-1",
  };
  community.setEdgeLength(120);
  community.activate.call(instance);
  const first=instance.__jaalCommunity.view;
  const box=Object.keys(first.clusterToGroup)
    .find(id=>first.clusterToGroup[id]==="team-0");
  const origin=net.getPositions()[box];
  assert.ok(origin);
  click({nodes:[box]});
  for(const id of ["A","B","C"]) {
    const p=net.getPositions()[id];
    assert.ok(Math.hypot(p.x-origin.x,p.y-origin.y)<140,
      id+" launched far from its original group");
  }
  click({nodes:["A"]});
  const restored=net.getPositions()[box];
  assert.ok(Math.hypot(restored.x-origin.x,restored.y-origin.y)<0.01,
    "closed box must recover its original anchor");
  community.setEdgeLength(240);
  community.activate.call(instance);
  const spread=net.getPositions()[box];
  assert.ok(Number.isFinite(spread.x)&&Number.isFinite(spread.y));
  assert.ok(Math.hypot(spread.x-origin.x,spread.y-origin.y)>0,
    "edge spacing should change the frozen quotient geometry");
  community.setEdgeLength(120);
  community.restore.call(instance);
});
