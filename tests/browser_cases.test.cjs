"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const core = require("../jaal_topology/browser_cases/case_core.js");

test("CSV handles BOM, escaped quotes, CRLF and embedded commas", () => {
  const rows = core.parseDelimited('\ufeffparent,child\r\n"CEO, Alice","Team ""A"""\r\n');
  assert.deepEqual(rows, [["parent","child"],["CEO, Alice",'Team "A"']]);
  assert.deepEqual(core.parseDelimited("from\tto\nA\tB\n"),[["from","to"],["A","B"]]);
  assert.deepEqual(core.parseDelimited('from,to\n"root\nnode",child'),[
    ["from","to"],["root\nnode","child"]]);
});

test("CSV with and without header loads real directed graph, de-duplicates pairs", () => {
  const result=core.importGraph("郵件互動",[
    "\ufeffsender,recipient\nA,B\nB,A\nA,B\n",
    "C,D\nD,C\n"],"ClassLabel,CT\nA,甲\nB,乙\n");
  assert.equal(result.nodes.length,4);
  assert.equal(result.edges.length,4);
  assert.equal(result.edges.find(e=>e.from==="A"&&e.to==="B").weight,1);
  assert.equal(result.nodes.find(n=>n.id==="A").label,"甲");
  assert.equal(core.topology(result).hasCycle,true);
  assert.deepEqual(core.validateCase(result),result);
});

test("explicit weight adds repeated records without silently modifying direction", () => {
  const g=core.importGraph("weighted",[
    "from,to,count\nA,B,3\nA,B,2\nB,A,1\n"],"");
  assert.deepEqual(g.edges,[
    {from:"A",to:"B",weight:5},{from:"B",to:"A",weight:1}]);
});

test("TSV ignores quoted commas and weighted files preserve order-independent totals", () => {
  const graph=core.importGraph("tab",['"Smith, John"\tBob\nBob\tCarol\n'],"");
  assert.deepEqual(graph.edges.map(e=>[e.from,e.to]),[
    ["Smith, John","Bob"],["Bob","Carol"]]);
  const parts=["from,to,count\nA,B,7\n","from,to\nA,B\nA,B\n"];
  assert.equal(core.importGraph("mixed",parts,"").edges[0].weight,8);
  assert.equal(core.importGraph("mixed",parts.slice().reverse(),"").edges[0].weight,8);
});

test("root scope keeps directed reachability and original induced links", () => {
  const g=core.importGraph("scope",["from,to\nA,B\nB,C\nC,A\nD,A\n"],"");
  assert.deepEqual(core.neighborhood(g,"A",1,"out").nodes.map(n=>n.id),["A","B"]);
  assert.deepEqual(core.neighborhood(g,"A",1,"in").nodes.map(n=>n.id),["A","C","D"]);
  const all=core.neighborhood(g,"A",2,"both");
  assert.equal(all.nodes.length,4);
  assert.equal(all.edges.length,4);
  assert.equal(core.neighborhood(g,"A",0,"out").edges.length,0);
  assert.deepEqual(g.edges.map(e=>[e.from,e.to]),[
    ["A","B"],["B","C"],["C","A"],["D","A"]]);
});

test("invalid CSV errors are actionable and never result in a partial saved case", () => {
  for(const source of ["from,to\nA,\n", 'from,to\n"A,B', "parent,\nA,B\n",
                      "source,target\nA,B\nA\n"]) {
    assert.throws(()=>core.importGraph("bad",[source],""), Error);
  }
  assert.throws(()=>core.importGraph(" ",["A,B"],""),/案例名稱/);
  assert.throws(()=>core.importGraph("bad",["from,to,count\nA,B,0\n"],""),/權重/);
  assert.throws(()=>core.importGraph("bad",["from,to,count\nA,B,NaN\n"],""),/權重/);
  assert.throws(()=>core.importGraph("bad",["A,B"],"ClassLabel,CT\nA,甲\nA,乙\n"),/不同顯示名稱/);
  assert.throws(()=>core.parseDelimited("a".repeat(core.MAX_FILE_CHARS+1)),/2 MB/);
});

test("graph limits, invalid backups and forged graph objects fail closed", () => {
  const rows=["parent,child"];
  for(let i=0;i<251;i++) rows.push("A,N"+i);
  assert.throws(()=>core.importGraph("large",[rows.join("\n")],""),/250/);
  const tooManyEdges=["parent,child"];
  for(let i=0;i<2001;i++) tooManyEdges.push("N"+Math.floor(i/100)+",N"+i%100);
  assert.throws(()=>core.importGraph("large",[tooManyEdges.join("\n")],""),/2,000/);
  const g=core.importGraph("clean",["parent,child\nA,B\n"],"");
  assert.throws(()=>core.validateCase({...g,nodes:[...g.nodes,g.nodes[0]]}),/重複節點/);
  assert.throws(()=>core.validateCase({...g,edges:[{from:"A",to:"C",weight:1}]}),/不存在/);
  assert.throws(()=>core.validateCase({...g,schemaVersion:2}),/版本/);
  assert.throws(()=>core.neighborhood(g,"A",99,"out"),/步數/);
});

test("HTML-looking IDs and prototype names remain literal data, not executable code", () => {
  const payload="<img src=x onerror=alert(1)>";
  const graph=core.importGraph(payload,[
    "source,target\n__proto__,constructor\nconstructor,"+payload+"\n"],"");
  assert.equal(graph.title,payload);
  assert.equal(graph.nodes.find(n=>n.id===payload).label,payload);
  assert.equal(core.neighborhood(graph,"__proto__",2,"out").nodes.length,3);
  assert.equal(core.topology(graph).hasCycle,false);
  assert.equal(core.validateCase(JSON.parse(JSON.stringify(graph))).edges.length,2);
});
