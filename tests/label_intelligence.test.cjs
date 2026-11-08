"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const engine = require("../jaal_topology/assets/23.jaal_label_intelligence.js");
const focus = require("../jaal_topology/assets/22.jaal_local_focus.js");

test("smart density avoids collisions but important pins and root always survive", () => {
  engine.state.pinned.clear();
  engine.state.pinned.add("P");
  const sample = [
    {node:{id:"P"},id:"P",critical:true,onScreen:true,
     priority:1000000,bounds:{l:0,r:100,t:0,b:30}},
    {node:{id:"B"},id:"B",critical:false,onScreen:true,
     priority:900,bounds:{l:5,r:110,t:0,b:30}},
    {node:{id:"C"},id:"C",critical:false,onScreen:true,
     priority:800,bounds:{l:150,r:240,t:0,b:30}},
    {node:{id:"D"},id:"D",critical:false,onScreen:true,
     priority:700,bounds:{l:160,r:250,t:0,b:30}}
  ];
  const chosen = engine.choose(sample,10,false);
  assert.deepEqual([...chosen],["P","C"]);
  engine.state.pinned.clear();
  assert.deepEqual([...engine.choose(sample,10,true)],["P","B","C","D"]);
});

test("one real local-scope change triggers one fit of visible quotient IDs; timeline does not pan", () => {
  const nn = ["A","B","C","D"].map(id=>({id,hidden:id==="D"}));
  let fit=[];
  const net = {fit:options=>fit.push(options)};
  const instance={nn:{get:()=>nn},net};
  focus.setSelection({root:"A",ids:["A","B","C"],hops:2,direction:"out"});
  focus.afterProjection.call(instance);
  assert.equal(fit.length,1);
  assert.deepEqual(fit[0].nodes,["A","B","C"]);
  assert.equal(focus.pendingFit,false);
  focus.afterProjection.call(instance); // temporal tick
  focus.setSelection({root:"A",ids:["A","B","C"],hops:2,direction:"out"});
  focus.afterProjection.call(instance);
  assert.equal(fit.length,1,"identical frame/scope must not refit");
  focus.setSelection({root:"A",ids:["A"],hops:0,direction:"out"});
  nn[1].hidden=true; nn[2].hidden=true;
  focus.afterProjection.call(instance);
  assert.equal(fit.length,2);
  assert.deepEqual(fit[1].nodes,["A"]);
  focus.setSelection({root:null});
  focus.afterProjection.call(instance);
  assert.equal(fit.length,2,"clearing scope does not steal camera");
});

test("adaptive engine projects smart labels in vis DataSet, never rewrites original IDs", () => {
  const original = Array.from({length:140},(_,i)=>({
    id:"USER-"+i, label:"USER-"+i, x:100+(i%10)*4,
    y:200+(Math.floor(i/10)%10)*4, hidden:false
  }));
  const map=new Map(original.map(n=>[n.id,{...n}]));
  const nn={
    get:()=>Array.from(map.values()).map(n=>({...n})),
    update:rows=>rows.forEach(r=>map.set(r.id,{...map.get(r.id),...r}))
  };
  const ee={get:()=>[{id:"e",from:"USER-0",to:"USER-2"}]};
  const callbacks={};
  const net={
    getScale:()=>0.5,
    getPositions:()=>Object.fromEntries(original.map(n=>[n.id,{x:n.x,y:n.y}])),
    canvasToDOM:p=>({x:p.x,y:p.y}),
    on:(name,fn)=>{callbacks[name]=fn},
    setOptions:()=>{},
    body:{container:{getBoundingClientRect:()=>({width:600,height:450})}}
  };
  engine.state.density="smart";
  engine.state.pinned.clear();
  engine.state.remembered.clear();
  engine.state.net=null; engine.state.instance=null;
  engine.sync.call({nn,ee,net});
  const shown=[...map.values()].filter(n=>n.label).map(n=>n.id);
  assert.ok(shown.length>0 && shown.length<140,shown.length);
  assert.equal(map.get("USER-0").id,"USER-0");
  assert.equal(map.size,140);
  assert.equal(typeof callbacks.zoom,"function");
  engine.togglePin("USER-119");
  assert.ok(map.get("USER-119").label,"pinned should remain labeled when crowded");
  engine.togglePin("USER-119");
  engine.state.net=null; engine.state.instance=null;
});


test("subgraph fit includes full 3000-node visible extent and farthest root", () => {
  const ids=Array.from({length:3000},(_,i)=>"N"+i);
  let fitted;
  focus.setSelection({root:"N2999",ids,hops:10,direction:"out"});
  focus.afterProjection.call({nn:{get:()=>ids.map(id=>({id,hidden:false}))},
    net:{fit:args=>{fitted=args.nodes;}}});
  assert.equal(fitted.length,3000);
  assert.ok(fitted.includes("N0") && fitted.includes("N2999"));
  assert.equal(focus.pendingFit,false);
});

test("temporal fullLabels overrides smart-density label hiding", () => {
  const temporal=require("../jaal_topology/assets/21.jaal_temporal_playback.js");
  globalThis.dash_clientside=globalThis.dash_clientside||{};
  globalThis.dash_clientside.jaal_temporal=temporal;
  temporal.fullLabels=true;
  const nodes=Array.from({length:105},(_,i)=>({id:"T"+i,label:"T"+i,
    hidden:false,x:100+i,y:100}));
  const data=new Map(nodes.map(n=>[n.id,{...n}]));
  const nn={get:()=>[...data.values()].map(n=>({...n})),
    update:rows=>rows.forEach(row=>data.set(row.id,{...data.get(row.id),...row}))};
  const net={getScale:()=>0.1,
    getPositions:()=>Object.fromEntries(nodes.map(n=>[n.id,{x:n.x,y:n.y}])),
    canvasToDOM:p=>p,on:()=>{},setOptions:()=>{},
    body:{container:{getBoundingClientRect:()=>({width:1000,height:600})}}};
  engine.state.density="smart";
  engine.state.instance=null;engine.state.net=null;engine.state.pinned.clear();
  engine.state.remembered.clear();
  focus.setSelection({root:null});
  engine.sync.call({nn,ee:{get:()=>[]},net});
  assert.equal([...data.values()].filter(n=>n.label).length,105);
  temporal.fullLabels=false;
  engine.state.net=null;engine.state.instance=null;
});


test("language toggle invalidates hidden temporal name cache", () => {
  const labels=globalThis.dash_clientside.jaal_visible_labels;
  const oldResolve=labels.resolve, oldChinese=labels.preferChinese;
  labels.resolve=(id,chinese)=>chinese?"員工-"+id:String(id);
  const data=new Map(Array.from({length:105},(_,i)=>[
    "USER-"+i,{id:"USER-"+i,label:i<12?"USER-"+i:"",x:120+i,y:150,hidden:false}
  ]));
  const nn={get:()=>[...data.values()].map(v=>({...v})),
    update:rows=>rows.forEach(x=>data.set(x.id,{...data.get(x.id),...x}))};
  const net={getScale:()=>0.5,
    getPositions:()=>Object.fromEntries([...data.values()].map(v=>[v.id,{x:v.x,y:v.y}])),
    canvasToDOM:p=>p,on:()=>{},setOptions:()=>{},
    body:{container:{getBoundingClientRect:()=>({width:1000,height:500})}}};
  engine.state.density="all";engine.state.remembered.clear();
  engine.state.net=null;engine.state.instance=null;
  labels.preferChinese=false;
  engine.sync.call({nn,ee:{get:()=>[]},net});
  assert.equal(data.get("USER-104").label,"USER-104");
  labels.preferChinese=true;
  engine.sync.call({nn,ee:{get:()=>[]},net});
  assert.equal(data.get("USER-104").label,"員工-USER-104");
  labels.preferChinese=oldChinese;
  labels.resolve=oldResolve;
  engine.state.net=null;engine.state.instance=null;
});
