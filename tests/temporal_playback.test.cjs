"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const temporal = require("../jaal_topology/assets/21.jaal_temporal_playback.js");

const source = {
  nodes: [
    {id: "A", label: "A", SentEmails: 100},
    {id: "B", label: "B", SentEmails: 100},
    {id: "C", label: "C", SentEmails: 100},
  ],
  edges: [
    {id: "edge0", from: "A", to: "B", title: "old"},
    {id: "edge1", from: "B", to: "C", title: "old"},
  ],
};
const frame = {
  date: "2026-10-05", from: "2026-10-05", to: "2026-10-05",
  messages: 3, nodes: 2, links: 1, mode: "rolling",
  edges: [["A", "B", 3]], partition: {A: "community-0", B: "community-0"},
};

class DataSet {
  constructor(rows) {this.rows = new Map(rows.map(item => [String(item.id), {...item}]));}
  getIds() {return [...this.rows.keys()];}
  get() {return [...this.rows.values()];}
  remove(ids) {for (const id of ids) this.rows.delete(String(id));}
  update(items) {for (const item of items) {
    const id = String(item.id);
    this.rows.set(id, {...this.rows.get(id), ...item});
  }}
}
test("projectSource really removes inactive relationships and derives window counts", () => {
  temporal.setFrame(frame);
  const filtered = temporal.projectSource(source);
  assert.equal(filtered.nodes.length, 2);
  assert.deepEqual(filtered.nodes.map(x => x.id), ["A", "B"]);
  assert.deepEqual([filtered.nodes[0].SentEmails,
    filtered.nodes[1].ReceivedEmails], [3, 3]);
  assert.equal(filtered.edges.length, 1);
  assert.equal(filtered.edges[0].mailCount, 3);
  assert.ok(filtered.edges[0].width > 2);
  assert.match(filtered.edges[0].title, /3 封/);
  assert.equal(source.edges.length, 2);
  assert.equal(source.nodes[0].SentEmails, 100);
  temporal.setFrame(null);
  assert.strictEqual(temporal.projectSource(source), source);
});
test("real DataSets hide inactive graph elements without recreating nodes or moving the camera", () => {
  temporal.setFrame(frame);
  const nn = new DataSet(source.nodes), ee = new DataSet(source.edges);
  let moved = null;
  const instance = {nn, ee, props: {data: source}, net: {
    getViewPosition: () => ({x: 2, y: 3}), getScale: () => 1.25,
    getPositions: () => ({A: {x: 5, y: 7}, B: {x: 8, y: 9}, C: {x: 10, y: 11}}),
    moveTo: args => {moved = args;},
  }};
  temporal.apply.call(instance);
  // Playback keeps a fixed DataSet universe to avoid network physics flashes.
  // Hidden inactive records are not drawn and retain their IDs/positions.
  assert.deepEqual(nn.getIds(), ["A", "B", "C"]);
  assert.deepEqual(ee.getIds(), ["edge0", "edge1"]);
  assert.equal(nn.rows.get("A").hidden, false);
  assert.equal(nn.rows.get("B").hidden, false);
  assert.equal(nn.rows.get("C").hidden, true);
  assert.equal(ee.rows.get("edge0").hidden, false);
  assert.equal(ee.rows.get("edge1").hidden, true);
  assert.equal(nn.rows.get("C").TotalEmails, 0);
  assert.equal(nn.rows.get("A").TotalEmails, 3);
  assert.deepEqual([nn.rows.get("A").x, nn.rows.get("A").y], [5, 7]);
  assert.deepEqual(moved.position, {x: 2, y: 3});
  assert.equal(moved.scale, 1.25);
  assert.deepEqual([temporal.lastRendered.sourceEdges,
    temporal.lastRendered.drawnEdges], [1, 1]);
  temporal.setFrame({...frame, date: "2026-10-06",
    edges: [["B", "C", 5]]});
  temporal.apply.call(instance);
  assert.deepEqual(nn.getIds(), ["A", "B", "C"]);
  assert.deepEqual(ee.getIds(), ["edge0", "edge1"]);
  assert.equal(nn.rows.get("A").hidden, true);
  assert.equal(nn.rows.get("B").hidden, false);
  assert.equal(nn.rows.get("C").hidden, false);
  assert.equal(ee.rows.get("edge0").hidden, true);
  assert.equal(ee.rows.get("edge1").hidden, false);
  assert.equal(nn.rows.get("A").TotalEmails, 0);
  assert.equal(nn.rows.get("C").ReceivedEmails, 5);
  assert.deepEqual([nn.rows.get("C").x, nn.rows.get("C").y], [10, 11]);
  assert.deepEqual([temporal.lastRendered.drawnNodes,
    temporal.lastRendered.drawnEdges], [2, 1]);
  assert.equal(temporal.lastRendered.date, "2026-10-06");
  temporal.setFrame(null);
});
function trigger(id) {
  globalThis.dash_clientside.callback_context =
    {triggered: [{prop_id: id + ".n_clicks"}]};
}
const packet = {
  start_index: 2, end_index: 5, frames: [2, 3, 4, 5].map(i => ({
    date: "2026-10-" + String(i+1).padStart(2, "0"),
    from: "2026-10-01", to: "2026-10-" + String(i+1).padStart(2, "0"),
    messages: i*10, nodes: 2, links: 1,
    edges: [["A", "B", i*10]], partition: {},
  })),
};
test("autoplay, step, manual navigation, stop and loop never fetch", () => {
  trigger("jaal-temporal-frames");
  assert.deepEqual(temporal.playback(0,0,0,0,packet,2,true,1,[]),
    [5, true, "▶ 播放"]);
  trigger("jaal-temporal-play");
  assert.deepEqual(temporal.playback(1,0,0,0,packet,5,true,1,[]),
    [2, false, "⏸ 暫停"]);
  trigger("jaal-temporal-tick");
  assert.deepEqual(temporal.playback(1,0,0,1,packet,2,false,2,[]),
    [4, false, "⏸ 暫停"]);
  assert.deepEqual(temporal.playback(1,0,0,2,packet,4,false,2,[]),
    [5, true, "▶ 播放"]);
  assert.deepEqual(temporal.playback(1,0,0,2,packet,5,false,1,["loop"]),
    [2, false, "⏸ 暫停"]);
  trigger("jaal-temporal-back");
  assert.deepEqual(temporal.playback(1,1,0,2,packet,4,false,1,[]),
    [3, true, "▶ 播放"]);
});
test("frame selection reports actual window boundaries and message counts", () => {
  const [selected, status] = temporal.choose(4, packet);
  assert.equal(selected.messages, 40);
  assert.match(status, /40 封信/);
  assert.match(status, /2026-10-05/);
  assert.equal(temporal.speed(350), 350);
  assert.equal(temporal.speed(-1), 700);
});

test("temporal network only labels stable high-volume participants unless expanded", () => {
  temporal.setLabelUniverse({
    nodes: source.nodes,
    edges: [{id: "ab", from: "A", to: "B", mailCount: 30}],
  });
  temporal.setFrame({...frame, edges: [["A", "B", 3]]});
  temporal.setDisplayOptions([]);
  assert.equal(temporal.displayLabel("A", "Sales / A"), "Sales / A");
  assert.equal(temporal.displayLabel("C", "Finance / C"), "");
  temporal.setFrame({...frame, edges: [["B", "C", 7]]});
  // Incoming activity changes but stable full-period label ranking does not.
  assert.equal(temporal.displayLabel("C", "Finance / C"), "");
  temporal.setDisplayOptions(["all"]);
  assert.equal(temporal.displayLabel("C", "Finance / C"), "Finance / C");
  temporal.setFrame(null);
  temporal.setDisplayOptions([]);
  assert.equal(temporal.displayLabel("C", "Finance / C"), "Finance / C");
});

test("temporal community holds one partition and open state across rolling ticks", () => {
  require("../jaal_topology/assets/16.jaal_visible_labels.js");
  const api = require("../jaal_topology/assets/18.jaal_community_collapse.js");
  const members = ["A", "B", "C", "D", "E", "F"];
  const graph = {
    nodes: members.map(id => ({id, label: id})),
    edges: [
      {id: "ab", from: "A", to: "B"},
      {id: "ad", from: "A", to: "D"},
      {id: "ce", from: "C", to: "E"},
      {id: "de", from: "D", to: "E"},
    ],
  };
  api.partition = Object.fromEntries(members.map((id, i) =>
    [id, i < 3 ? "team-0" : "team-1"]));
  const first = {
    ...frame, edges: [["A", "B", 3], ["A", "D", 2]],
  };
  const second = {
    ...frame, date: "2026-10-06", from: "2026-10-06", to: "2026-10-06",
    edges: [["C", "E", 4], ["D", "E", 1]],
  };
  const positions = Object.fromEntries(members.map((id,i) =>
    [id, {x: i * 10, y: i * 20}]));
  let click = null;
  const instance = {
    nn: new DataSet(graph.nodes), ee: new DataSet(graph.edges),
    props: {data: graph},
    net: {
      on: (name, fn) => {if (name === "click") click = fn;},
      getPositions: () => positions,
      getViewPosition: () => ({x: 10, y: 20}),
      getScale: () => 1.2,
      moveTo: () => {},
      setOptions: () => {},
    },
  };
  temporal.setFrame(first);
  api.activate.call(instance);
  const firstView = instance.__jaalCommunity.view;
  assert.equal(instance.__jaalCommunity.filtered, false);
  assert.equal(temporal.lastRendered.sourceEdges, 2);
  const group = Object.keys(firstView.clusterToGroup).find(
    k => firstView.clusterToGroup[k] === "team-0");
  assert.ok(group);
  click({nodes:[group]});
  assert.ok(instance.__jaalCommunity.opened.has("team-0"));
  const stable = instance.__jaalCommunity;
  const firstIds = [...instance.ee.getIds()].sort();
  temporal.setFrame(second);
  api.activate.call(instance);
  assert.strictEqual(instance.__jaalCommunity, stable);
  assert.ok(instance.__jaalCommunity.opened.has("team-0"));
  assert.deepEqual([...instance.ee.getIds()].sort(), firstIds);
  assert.equal(temporal.lastRendered.sourceEdges, 2);
  assert.equal(instance.nn.rows.get("A").hidden, true);
  assert.equal(instance.nn.rows.get("C").hidden, false);
  const otherGroup = Object.keys(instance.__jaalCommunity.view.clusterToGroup)
    .find(k => instance.__jaalCommunity.view.clusterToGroup[k] === "team-1");
  assert.ok(otherGroup && !instance.nn.rows.get(otherGroup).hidden);
  temporal.setFrame(null);
  api.restore.call(instance);
  assert.deepEqual([...instance.nn.getIds()].sort(), members);
  assert.equal(instance.ee.getIds().length, graph.edges.length);
});

test("playing after expanding a community holds every member at the actual drawn anchor and uses static directed curves", () => {
  const community = require("../jaal_topology/assets/18.jaal_community_collapse.js");
  const nodes = ["A","B","C","D","E","F"].map((id, i) =>
    // Simulate source coordinates that differ from the positions after
    // interactive dragging/expansion. Playback must not write them back.
    ({id, label:id, x:1000+i*50, y:1000-i*10}));
  const graph = {
    nodes,
    edges: [
      {id:"a-d",from:"A",to:"D"},
      {id:"d-a",from:"D",to:"A"},
      {id:"b-e",from:"B",to:"E"},
      {id:"c-f",from:"C",to:"F"},
      {id:"a-b",from:"A",to:"B"},
    ],
  };
  community.partition = {A:"first",B:"first",C:"first",
    D:"second",E:"second",F:"second"};
  // vis.js getPositions reflects the current visible DataSet, as it does
  // after the user drags a cluster. These locations differ from source x/y.
  const nn = new DataSet(nodes);
  const ee = new DataSet(graph.edges);
  const currentPositions = () => Object.fromEntries(nn.get().map(n => [
    n.id, {x:n.x,y:n.y},
  ]));
  let click;
  let cameraUpdates = 0, optionsUpdates = 0;
  const instance = {
    props: {data:graph}, nn, ee,
    net: {
      on: (type, fn) => {if (type==="click") click=fn;},
      getPositions: currentPositions,
      getViewPosition: () => ({x:150,y:80}),
      getScale: () => 1.1,
      moveTo: args => {
        assert.deepEqual(args.position,{x:150,y:80});
        assert.equal(args.scale,1.1);
        cameraUpdates++;
      },
      setOptions: () => {optionsUpdates++;},
    },
  };
  const day1 = {...frame, date:"2026-10-05",
    edges:[["A","D",4],["D","A",2],["A","B",5]]};
  const day2 = {...frame, date:"2026-10-06",
    edges:[["B","E",6],["C","F",3]]};
  temporal.setFrame(day1);
  community.activate.call(instance);
  const cluster = Object.entries(instance.__jaalCommunity.view.clusterToGroup)
    .find(([, group]) => group==="first")[0];
  const anchor = {...currentPositions()[cluster]};
  click({nodes:[cluster]});
  const state = instance.__jaalCommunity;
  assert.ok(state.opened.has("first"));
  const ids = nn.getIds().sort();
  const secondCluster = Object.entries(instance.__jaalCommunity.view.clusterToGroup)
    .find(([, group]) => group==="second")[0];
  assert.equal(ids.length,4);
  assert.deepEqual(ids,["A","B","C",secondCluster].sort());
  // Drag A and the remaining collapsed box before playing. Both should
  // retain their actual current position through subsequent frames.
  nn.update([{id:"A",x:anchor.x+41,y:anchor.y-23},
             {id:secondCluster,x:anchor.x+310,y:anchor.y+140}]);
  const before = currentPositions();
  const eids = ee.getIds().sort();
  const firstEdges = ee.get();
  assert.ok(firstEdges.some(e => e.from==="A" && e.to===secondCluster),
    "expanded member must connect to the still-collapsed second community");
  assert.ok(firstEdges.every(e=>e.from===e.to ||
      e.smooth?.type==="curvedCW"),firstEdges);
  // Replay multiple frames and then return to the first: no force-layout,
  // stale-source coordinates, edge ID changes or camera jumps.
  for(const next of [day2,day1,day2,day1]) {
    temporal.setFrame(next);
    community.activate.call(instance);
    const after = currentPositions();
    for (const id of ids) {
      assert.deepEqual(after[id],before[id],id+" moved during playback");
    }
    assert.deepEqual(nn.getIds().sort(),ids);
    assert.deepEqual(ee.getIds().sort(),eids);
    assert.ok(ee.get().every(e=>e.from===e.to ||
      e.smooth?.type==="curvedCW"));
    assert.strictEqual(instance.__jaalCommunity,state);
    assert.ok(state.opened.has("first"));
    assert.equal(instance.__jaalCommunity.filtered,false);
  }
  assert.ok(cameraUpdates>=5);
  assert.equal(optionsUpdates,1,"physics is frozen once, not reset per tick");
  temporal.setFrame(null);
  community.restore.call(instance);
});

test("temporal community retains quotient IDs even when whole groups go silent", () => {
  const community = require("../jaal_topology/assets/18.jaal_community_collapse.js");
  const nodes = ["A","B","C","D","E","F"].map(id => ({id,hidden:false}));
  const edges = [
    {id:"ad",from:"A",to:"D",hidden:false,mailCount:8},
    {id:"bd",from:"B",to:"D",hidden:true,mailCount:2},
    {id:"de",from:"D",to:"E",hidden:true},
  ];
  const membership = Object.fromEntries(nodes.map((n,i) =>
    [n.id, i<3?"group-0":"group-1"]));
  const first = community.makeView({nodes,edges},membership,new Set(),false,true);
  const quiet = community.makeView({
    nodes:nodes.map(n=>({...n,hidden:["A","B","C"].includes(n.id)})),
    edges:edges.map(e=>({...e,hidden:true})),
  },membership,new Set(),false,true);
  assert.deepEqual(first.nodes.map(n=>n.id),quiet.nodes.map(n=>n.id));
  assert.deepEqual(first.edges.map(e=>e.id),quiet.edges.map(e=>e.id));
  assert.equal(first.edges[0].hidden,false);
  assert.equal(quiet.edges[0].hidden,true);
  assert.equal(quiet.nodes[0].hidden,true);
  assert.match(first.edges[0].title,/8 封信/);
});

test("precise playback advances whole interval frames and moves both blue-bar ends", () => {
  const precise = {
    unit_minutes: 10, overlap: "disjoint", start_index: 0, end_index: 2,
    frames: [0, 1, 2].map(i => ({
      date: "2026-10-05T09:" + String(i*10).padStart(2,"0"),
      from: "2026-10-05T09:" + String(i*10).padStart(2,"0"),
      to: "2026-10-05T09:" + String((i+1)*10).padStart(2,"0"),
      to_exclusive: "2026-10-05T09:" + String((i+1)*10).padStart(2,"0"),
      axis_start: i/3, axis_end: (i+1)/3, mode: "rolling",
      messages: 1, nodes: 2, links: 1,
      edges: [["A","B",1]], partition: {A:"team", B:"team"},
    })),
  };
  const [frame0, label0, style0] = temporal.choose(0, precise);
  const [frame1, label1, style1] = temporal.choose(1, precise);
  assert.match(label0, /互斥分段/);
  assert.match(label0, /\[2026-10-05T09:00, 2026-10-05T09:10\)/);
  assert.equal(frame0.to_exclusive, frame1.from);
  assert.equal(style0.left, "0%");
  assert.ok(Math.abs(parseFloat(style1.left) - 100/3) < 1e-8);
  assert.ok(Math.abs(parseFloat(style0.width) - 100/3) < 1e-8);
  assert.ok(Math.abs(parseFloat(style1.width) - 100/3) < 1e-8);
  assert.equal(temporal.axis(precise)[0], 2);
  assert.deepEqual(temporal.axis(precise)[1], {
    0: "10-05 09:00", 1: "10-05 09:10", 2: "10-05 09:20",
  });
  const cumulative = {...precise, frames: precise.frames.map(f => ({
    ...f, from: "2026-10-05T09:00", mode: "cumulative",
  }))};
  assert.deepEqual(temporal.axis(cumulative)[1], {
    0: "10-05 09:10", 1: "10-05 09:20", 2: "10-05 09:30",
  }, "cumulative marks must show increasing exclusive cutoffs");
  trigger("jaal-temporal-tick");
  assert.deepEqual(temporal.playback(1,0,0,1,precise,0,false,7,[]),
                   [1,false,"⏸ 暫停"],"step selection does not skip precomputed interval frames");
  const error = temporal.choose(0,{frames:[],error:"max 240"});
  assert.deepEqual(error[0].edges,[]);
  assert.match(error[1],/max 240/);
  assert.equal(error[2].width,"0%");
});
