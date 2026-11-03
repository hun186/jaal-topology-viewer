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
test("real DataSets mutate on playback and preserve the same canvas camera", () => {
  temporal.setFrame(frame);
  const nn = new DataSet(source.nodes), ee = new DataSet(source.edges);
  let moved = null;
  const instance = {nn, ee, props: {data: source}, net: {
    getViewPosition: () => ({x: 2, y: 3}), getScale: () => 1.25,
    getPositions: () => ({A: {x: 5, y: 7}, B: {x: 8, y: 9}, C: {x: 10, y: 11}}),
    moveTo: args => {moved = args;},
  }};
  temporal.apply.call(instance);
  assert.deepEqual(nn.getIds(), ["A", "B"]);
  assert.deepEqual(ee.getIds(), ["edge0"]);
  assert.equal(nn.rows.get("A").TotalEmails, 3);
  assert.deepEqual(moved.position, {x: 2, y: 3});
  assert.equal(moved.scale, 1.25);
  assert.deepEqual([temporal.lastRendered.sourceEdges,
    temporal.lastRendered.drawnEdges], [1, 1]);
  temporal.setFrame({...frame, date: "2026-10-06",
    edges: [["B", "C", 5]]});
  temporal.apply.call(instance);
  assert.deepEqual(nn.getIds(), ["B", "C"]);
  assert.deepEqual(ee.getIds(), ["edge1"]);
  assert.equal(nn.rows.get("C").ReceivedEmails, 5);
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
