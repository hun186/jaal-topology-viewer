/* Large-graph Canvas stress laboratory. No network, persistence or uploads. */
(function (root, doc) {
  "use strict";
  const core = root.JaalStressCore, $ = id => doc.getElementById(id);
  const COLORS = ["#2676ae", "#c26d35", "#7652a8"];
  const state = {
    graph: null, mode: "summary", focus: null, indices: null,
    selectedEdges: 0, limited: false, view: {scale: 1, x: 0, y: 0},
    drag: null, scheduled: false, buildMs: 0, drawMs: 0,
  };
  const integer = x => Number(x).toLocaleString("en-US");

  function status(message) {
    $("status").textContent = message;
  }

  function selectedNodes() {
    const graph = state.graph;
    const mode = $("view-mode").value;
    state.limited = false;
    if (mode === "summary") {
      return new Set(graph.nodes.map((n, i) =>
        n.kind === "executive" || n.kind === "region" ||
        n.kind === "department" ? i : -1).filter(i => i >= 0));
    }
    if (mode === "full") {
      return new Set(graph.nodes.map((_, i) => i));
    }
    const rootIndex = state.focus === null ? graph.departments[0].head : state.focus;
    const local = core.selectLocal(graph, rootIndex, Number($("hops").value),
      $("direction").value, 2000);
    state.limited = local.limited;
    return local.indices;
  }

  function updateSelection() {
    if (!state.graph) return;
    state.mode = $("view-mode").value;
    $("stat-draw-ms").textContent = "—";
    state.indices = selectedNodes();
    const mask = new Uint8Array(state.graph.nodes.length);
    for (const i of state.indices) mask[i] = 1;
    state.selectedEdges = 0;
    for (const e of state.graph.edges) {
      if (mask[e.source] && mask[e.target]) state.selectedEdges++;
    }
    $("stat-visible").textContent = integer(state.indices.size) + " / " +
      integer(state.selectedEdges);
    let detail = state.mode === "summary"
      ? "管理層摘要：僅繪製總經理、區域主管與各部門主管及其相互郵件（非全量圖）。"
      : state.mode === "full"
      ? "全量繪圖：包含所有 " + integer(state.graph.nodes.length) +
        " 節點和 " + integer(state.graph.edges.length) + " 條有向連線。"
      : "局部誘導圖：依指定方向與步數保留真正可達的員工與連線。";
    if (state.limited) detail += " 已達 2,000 節點安全上限，局部顯示被截斷。";
    status(detail);
    $("graph-title").textContent = state.graph.label + "／" +
      $("view-mode").selectedOptions[0].textContent;
    fit();
  }

  function canvasSize() {
    const canvas = $("network");
    const rect = canvas.getBoundingClientRect();
    const ratio = Math.min(2, root.devicePixelRatio || 1);
    const width = Math.max(1, Math.round(rect.width * ratio));
    const height = Math.max(1, Math.round(rect.height * ratio));
    if (canvas.width !== width) canvas.width = width;
    if (canvas.height !== height) canvas.height = height;
    return {cssWidth: rect.width, cssHeight: rect.height, ratio};
  }

  function fit() {
    if (!state.graph || !state.indices) return;
    const {cssWidth,cssHeight} = canvasSize();
    let minX = Infinity,minY = Infinity,maxX = -Infinity,maxY = -Infinity;
    for (const i of state.indices) {
      const n=state.graph.nodes[i];
      minX=Math.min(minX,n.x);maxX=Math.max(maxX,n.x);
      minY=Math.min(minY,n.y);maxY=Math.max(maxY,n.y);
    }
    if (!Number.isFinite(minX)) return;
    const width=Math.max(80,maxX-minX+150),height=Math.max(80,maxY-minY+150);
    const scale=Math.min(cssWidth/width,cssHeight/height);
    const x=(cssWidth-(minX+maxX)*scale)/2;
    const y=(cssHeight-(minY+maxY)*scale)/2;
    state.view={scale,x,y};
    requestDraw();
  }

  function requestDraw() {
    if (state.scheduled) return;
    state.scheduled=true;
    root.requestAnimationFrame(() => {state.scheduled=false;draw();});
  }

  function draw() {
    if (!state.graph || !state.indices) return;
    const start = root.performance.now();
    const graph=state.graph, {scale,x,y}=state.view;
    const canvas=$("network"), {cssWidth,cssHeight,ratio}=canvasSize();
    const ctx=canvas.getContext("2d");
    ctx.setTransform(ratio,0,0,ratio,0,0);
    ctx.clearRect(0,0,cssWidth,cssHeight);
    ctx.fillStyle="#f9fcff";ctx.fillRect(0,0,cssWidth,cssHeight);
    ctx.translate(x,y);ctx.scale(scale,scale);
    const mask=new Uint8Array(graph.nodes.length);
    for(const i of state.indices)mask[i]=1;
    const fullLarge=state.mode==="full" && graph.nodes.length >= 5000;
    ctx.lineWidth=Math.max(0.5, Math.min(2, 1.3/Math.max(scale,0.3)));
    ctx.strokeStyle=fullLarge?"rgba(54,80,110,.085)":"rgba(75,105,139,.30)";
    ctx.beginPath();
    const pad=25/Math.max(scale,0.06);
    const vx=(-x/scale)-pad,vy=(-y/scale)-pad;
    const vw=cssWidth/scale+2*pad,vh=cssHeight/scale+2*pad;
    for (const edge of graph.edges) {
      if (!mask[edge.source] || !mask[edge.target]) continue;
      const a=graph.nodes[edge.source],b=graph.nodes[edge.target];
      if ((a.x<vx && b.x<vx)||(a.x>vx+vw && b.x>vx+vw)||
          (a.y<vy && b.y<vy)||(a.y>vy+vh && b.y>vy+vh)) continue;
      ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);
    }
    ctx.stroke();
    const radius=state.mode==="summary"?7:(graph.nodes.length>5000?3.2:4.6);
    for (const index of state.indices) {
      const n=graph.nodes[index];
      if(n.x<vx || n.x>vx+vw || n.y<vy || n.y>vy+vh)continue;
      ctx.fillStyle=COLORS[(n.component-1)%COLORS.length];
      ctx.beginPath();ctx.arc(n.x,n.y,
        n.kind==="executive"?radius*2:n.kind==="department"?radius*1.3:radius,
        0,Math.PI*2);ctx.fill();
    }
    // Only management labels at a readable zoom level. This prevents
    // 20,000 overlapping text labels from overwhelming the graph.
    if (state.indices.size<=150 || (scale>=1.1 && state.indices.size<=2000)) {
      ctx.font=(11/Math.max(scale,0.65))+"px system-ui";
      ctx.fillStyle="#27455f";ctx.textAlign="center";
      for(const i of state.indices) {
        const n=graph.nodes[i];
        if (state.indices.size>150 && n.kind==="staff") continue;
        if(n.x<vx || n.x>vx+vw || n.y<vy || n.y>vy+vh)continue;
        ctx.fillText(n.kind==="department"?n.label.slice(-9):n.id,
          n.x,n.y+16/Math.max(scale,0.65));
      }
    }
    state.drawMs=Math.max(0,root.performance.now()-start);
    $("stat-draw-ms").textContent=state.drawMs.toFixed(1);
  }

  function regenerate() {
    const key=$("scenario").value, start=root.performance.now();
    state.graph=core.buildScenario(key);
    state.buildMs=root.performance.now()-start;
    state.focus=null;
    $("node-query").value="";
    $("stat-build-ms").textContent=state.buildMs.toFixed(1);
    const graph=state.graph;
    $("stat-nodes").textContent=integer(graph.nodes.length);
    $("stat-edges").textContent=integer(graph.edges.length);
    $("stat-departments").textContent=integer(graph.departments.length);
    $("stat-layers").textContent=String(graph.maxDepth);
    const components=core.weakComponentSizes(graph);
    $("stat-components").textContent=String(components.length);
    $("component-breakdown").textContent="連通分量：" +
      components.map((v,i)=>"第"+(i+1)+"組 "+integer(v)+" 人").join(" · ");
    const options=$("dept-select");options.replaceChildren();
    for(const dept of graph.departments) {
      const opt=doc.createElement("option");opt.value=String(dept.head);
      opt.textContent="集團 "+dept.component+" ／ "+dept.title+
        "（"+integer(dept.count)+" 人）";options.append(opt);
    }
    updateSelection();
  }

  function findFocus(index) {
    if (!Number.isInteger(index)||index<0||index>=state.graph.nodes.length)return;
    state.focus=index;
    $("node-query").value=state.graph.nodes[index].id;
    $("view-mode").value="local";
    updateSelection();
  }

  function bind() {
    $("scenario").addEventListener("change",regenerate);
    $("view-mode").addEventListener("change",updateSelection);
    $("hops").addEventListener("change",()=> {
      if ($("view-mode").value==="local")updateSelection();
    });
    $("direction").addEventListener("change",()=> {
      if ($("view-mode").value==="local")updateSelection();
    });
    $("dept-select").addEventListener("change",()=>findFocus(Number($("dept-select").value)));
    $("find-node").addEventListener("click",()=>{
      const query=$("node-query").value.trim();
      if(!query){status("請輸入員工 ID 或完整姓名片段。");return;}
      const i=state.graph.nodes.findIndex(n=>
        n.id.toLowerCase()===query.toLowerCase() || n.label.includes(query));
      if(i<0){status("找不到員工："+query);return;}
      findFocus(i);
    });
    $("fit").addEventListener("click",fit);
    function zoom(mult,px,py) {
      const v=state.view;
      const next=Math.min(25,Math.max(.035,v.scale*mult));
      const worldX=(px-v.x)/v.scale,worldY=(py-v.y)/v.scale;
      state.view={scale:next,x:px-worldX*next,y:py-worldY*next};
      requestDraw();
    }
    const canvas=$("network");
    $("zoom-in").addEventListener("click",()=>{
      const {cssWidth,cssHeight}=canvasSize();zoom(1.25,cssWidth/2,cssHeight/2);
    });
    $("zoom-out").addEventListener("click",()=>{
      const {cssWidth,cssHeight}=canvasSize();zoom(.8,cssWidth/2,cssHeight/2);
    });
    canvas.addEventListener("wheel",event=>{
      event.preventDefault();
      const rect=canvas.getBoundingClientRect();
      zoom(event.deltaY<0?1.15:.87,event.clientX-rect.left,event.clientY-rect.top);
    },{passive:false});
    canvas.addEventListener("pointerdown",event=>{
      if(event.button!==0)return;
      canvas.setPointerCapture(event.pointerId);
      state.drag={id:event.pointerId,x:event.clientX,y:event.clientY};
      canvas.classList.add("dragging");
    });
    canvas.addEventListener("pointermove",event=>{
      if(!state.drag||state.drag.id!==event.pointerId)return;
      state.view.x+=event.clientX-state.drag.x;
      state.view.y+=event.clientY-state.drag.y;
      state.drag.x=event.clientX;state.drag.y=event.clientY;
      requestDraw();
    });
    function endDrag(){state.drag=null;canvas.classList.remove("dragging");}
    canvas.addEventListener("pointerup",endDrag);
    canvas.addEventListener("pointercancel",endDrag);
    root.addEventListener("resize",()=>fit());
  }

  doc.addEventListener("DOMContentLoaded",()=>{
    bind();
    try{regenerate();}
    catch(e){status("產生案例失敗："+e.message);}
  });
})(window,document);
