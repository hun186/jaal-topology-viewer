/* Browser-owned local cases: IndexedDB + native SVG. No upload endpoint or fetch. */
(function (root, doc) {
  "use strict";
  const core = root.JaalLocalCases;
  const $ = id => doc.getElementById(id);
  const NS = "http://www.w3.org/2000/svg";
  const DB_NAME = "jaal-local-cases-v1";
  const STORE = "cases";
  const state = {
    db: null, records: [], active: null, savedId: null,
    camera: {x: 0, y: 0, w: 1100, h: 650}, drag: null,
  };

  function message(text, type) {
    const el = $("notice");
    el.textContent = text;
    el.className = "notice" + (type ? " " + type : "");
  }
  function button(label, className, act) {
    const el = doc.createElement("button");
    el.type = "button"; el.textContent = label; el.className = className;
    el.addEventListener("click", act);
    return el;
  }
  function svg(tag, attrs) {
    const el = doc.createElementNS(NS, tag);
    for (const [name, value] of Object.entries(attrs || {})) {
      el.setAttribute(name, String(value));
    }
    return el;
  }
  function newId() {
    if (root.crypto && typeof root.crypto.randomUUID === "function") {
      return root.crypto.randomUUID();
    }
    return "case-" + Date.now() + "-" + Math.random().toString(36).slice(2);
  }
  function openDatabase() {
    return new Promise((resolve, reject) => {
      if (!root.indexedDB) {reject(Error("此瀏覽器不支援 IndexedDB。")); return;}
      const request = root.indexedDB.open(DB_NAME, 1);
      request.onupgradeneeded = () => {
        if (!request.result.objectStoreNames.contains(STORE)) {
          request.result.createObjectStore(STORE, {keyPath: "id"});
        }
      };
      request.onsuccess = () => {
        request.result.onversionchange = () => request.result.close();
        resolve(request.result);
      };
      request.onerror = () => reject(request.error || Error("無法開啟本機資料庫。"));
      request.onblocked = () => reject(Error("其他分頁正在使用舊資料庫，請先關閉後重新整理。"));
    });
  }
  function dbAction(mode, work) {
    return new Promise((resolve, reject) => {
      if (!state.db) {reject(Error("瀏覽器本機儲存無法使用。")); return;}
      let tx;
      try {tx = state.db.transaction(STORE, mode); work(tx.objectStore(STORE), tx);}
      catch (e) {reject(e); return;}
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error || Error("本機儲存交易失敗。"));
      tx.onabort = () => reject(tx.error || Error("本機儲存交易中止。"));
    });
  }
  function insertBounded(records) {
    // Object-store readwrite transactions serialize across browser tabs.
    // Count and insert share exactly one transaction for an atomic cap.
    return new Promise((resolve, reject) => {
      if (!state.db) {reject(Error("瀏覽器本機儲存不可用。")); return;}
      const tx = state.db.transaction(STORE, "readwrite");
      const store = tx.objectStore(STORE);
      let reason = "";
      const count = store.count();
      count.onsuccess = () => {
        if (count.result + records.length > core.MAX_CASES) {
          reason = "最多保存 20 個案例；請先刪除或備份舊案例。";
          tx.abort();
        } else {
          for (const record of records) store.add(record);
        }
      };
      tx.oncomplete = () => resolve();
      tx.onabort = () => reject(Error(reason ||
        (tx.error && tx.error.message) || "保存案例失敗，請檢查儲存空間。"));
    });
  }
  function renameExisting(id, title) {
    // A stale tab must not recreate an already deleted case via IDB.put().
    return new Promise((resolve, reject) => {
      if (!state.db) {reject(Error("本機儲存不可用。")); return;}
      const tx = state.db.transaction(STORE, "readwrite");
      const store = tx.objectStore(STORE);
      let reason = "";
      const get = store.get(id);
      get.onsuccess = () => {
        if (!get.result) {
          reason = "這個案例已被其他分頁刪除，請重新整理清單。";
          tx.abort();
          return;
        }
        try {
          const validated = core.validateCase(get.result);
          store.put({...validated, id, title, createdAt: get.result.createdAt});
        } catch (e) {
          reason = e.message;
          tx.abort();
        }
      };
      tx.oncomplete = () => resolve();
      tx.onabort = () => reject(Error(reason ||
        (tx.error && tx.error.message) || "更名失敗。"));
    });
  }
  function readRecords() {
    return new Promise((resolve, reject) => {
      if (!state.db) {resolve([]); return;}
      const tx = state.db.transaction(STORE, "readonly");
      const request = tx.objectStore(STORE).getAll();
      request.onsuccess = () => {
        try {
          const records = request.result.map(record => ({
            ...core.validateCase(record),
            id: record.id, createdAt: record.createdAt,
          }));
          records.sort((a, b) => String(b.createdAt).localeCompare(String(a.createdAt)));
          resolve(records);
        } catch (e) {reject(e);}
      };
      request.onerror = () => reject(request.error || Error("讀取案例失敗。"));
    });
  }
  async function refreshLibrary() {
    state.records = await readRecords();
    $("library-count").textContent = state.records.length + " / " + core.MAX_CASES;
    const list = $("case-list");
    list.replaceChildren();
    if (!state.records.length) {
      const empty = doc.createElement("p");
      empty.className = "case-empty";
      empty.textContent = "還沒有儲存案例。先試著建立第一張圖吧！";
      list.append(empty);
    }
    for (const record of state.records) {
      const card = doc.createElement("div");
      const open = button(record.title, "case-item" +
        (state.savedId === record.id ? " active" : ""), () => loadRecord(record));
      const count = doc.createElement("span");
      count.textContent = record.nodes.length + " 節點 · " +
        record.edges.length + " 條連線";
      open.append(count);
      card.append(open);
      const controls = doc.createElement("div");
      controls.className = "case-tools";
      controls.append(
        button("更名", "mini", async () => {
          const name = root.prompt("新的案例名稱", record.title);
          if (name === null) return;
          try {
            const modified = core.validateCase({...record, title: name});
            await renameExisting(record.id, modified.title);
            if (state.savedId === record.id) {
              state.active = modified;
              $("case-name").value = modified.title;
              $("active-name").textContent = modified.title + " · 已儲存";
            }
            await refreshLibrary();
            message("案例已更名。", "success");
          } catch (e) {
            await refreshLibrary().catch(() => {});
            message(e.message, "error");
          }
        }),
        button("匯出", "mini", () => download("jaal-case.json",
          JSON.stringify({format: "jaal-local-cases", schemaVersion: 1,
            cases: [record]}, null, 2))),
        button("刪除", "mini danger", async () => {
          if (!root.confirm("確定刪除「" + record.title + "」？此動作無法復原。")) return;
          try {
            await dbAction("readwrite", s => s.delete(record.id));
            if (state.savedId === record.id) {
              state.active = null; state.savedId = null; draw();
            }
            await refreshLibrary(); message("案例已從此瀏覽器移除。", "success");
          } catch (e) {message(e.message, "error");}
        })
      );
      card.append(controls);
      list.append(card);
    }
    $("export-all").disabled = state.records.length === 0;
  }

  function download(filename, content, mime) {
    const blob = new Blob([content], {type: mime || "application/json;charset=utf-8"});
    const url = URL.createObjectURL(blob);
    const a = doc.createElement("a");
    a.download = filename; a.href = url;
    doc.body.append(a); a.click(); a.remove();
    // A short task allows browser download readers to open the blob URL.
    root.setTimeout(() => URL.revokeObjectURL(url), 30000);
  }
  function resetCamera() {
    state.camera = {x: 0, y: 0, w: 1100, h: 650};
    applyCamera();
  }
  function applyCamera() {
    const c = state.camera;
    $("graph-canvas").setAttribute("viewBox", [c.x, c.y, c.w, c.h].join(" "));
  }
  function zoom(scale) {
    const c = state.camera;
    const w = Math.max(150, Math.min(4400, c.w * scale));
    const h = w * 650 / 1100;
    const cx = c.x + c.w / 2, cy = c.y + c.h / 2;
    state.camera = {x: cx - w/2, y: cy - h/2, w, h};
    applyCamera();
  }
  function loadRecord(record) {
    try {
      state.active = core.validateCase(record);
      state.savedId = record.id;
      $("case-name").value = record.title;
      $("active-name").textContent = record.title + " · 已儲存於此瀏覽器";
      $("root-filter").value = "";
      resetCamera(); draw(); refreshLibrary().catch(e => message(e.message, "error"));
      message("已載入「" + record.title + "」。您可以切換版面、點擊節點或匯出備份。", "success");
    } catch (e) {message(e.message, "error");}
  }
  function randHash(id) {
    let hash = 2166136261;
    for (let i = 0; i < id.length; i++) {
      hash ^= id.charCodeAt(i);
      hash = Math.imul(hash, 16777619);
    }
    return (hash >>> 0) / 4294967295;
  }
  function coordinates(graph, mode) {
    const nodes = graph.nodes;
    const n = nodes.length, points = new Map();
    if (mode === "hierarchy") {
      const incoming = new Map(nodes.map(x => [x.id, 0]));
      const outgoing = new Map(nodes.map(x => [x.id, []]));
      for (const edge of graph.edges) {
        incoming.set(edge.to, incoming.get(edge.to)+1);
        outgoing.get(edge.from).push(edge.to);
      }
      const roots = nodes.filter(x => incoming.get(x.id) === 0).map(x => x.id);
      const level = new Map();
      const queue = [...roots];
      // Cyclic components have no natural root. Pick deterministic seeds.
      for (let i = 0; i < queue.length; i++) {
        const id = queue[i];
        if (level.has(id)) continue;
        const parentLevel = (level.get(id) || 0);
        level.set(id, parentLevel);
        for (const next of outgoing.get(id)) {
          if (!level.has(next)) {
            // First discovery only; preserve a bounded hierarchy with cycles.
            const pending = queue.includes(next);
            if (!pending) queue.push(next);
          }
        }
      }
      const indegreeRoots = roots.length ? roots : [nodes[0].id];
      level.clear(); queue.length=0;
      for (const id of indegreeRoots) {
        level.set(id, 0); queue.push(id);
      }
      for (let i = 0; i < queue.length; i++) {
        const id = queue[i], depth = level.get(id);
        for (const next of outgoing.get(id)) {
          if (!level.has(next)) {
            level.set(next, Math.min(depth + 1, 25));
            queue.push(next);
          }
        }
      }
      for (const node of nodes) {
        if (level.has(node.id)) continue;
        level.set(node.id, 0); queue.push(node.id);
        for (let i = queue.length-1; i < queue.length; i++) {
          const id = queue[i], depth = level.get(id);
          for (const next of outgoing.get(id)) if (!level.has(next)) {
            level.set(next, Math.min(depth + 1, 25));
            queue.push(next);
          }
        }
      }
      const groups = new Map();
      for (const node of nodes) {
        const d = level.get(node.id);
        if (!groups.has(d)) groups.set(d, []);
        groups.get(d).push(node.id);
      }
      const keys = [...groups.keys()].sort((a,b) => a-b);
      const gapY = keys.length <= 1 ? 0 : Math.min(100, 555/(keys.length-1));
      for (const [index, key] of keys.entries()) {
        const ids = groups.get(key);
        for (let i = 0; i < ids.length; i++) {
          points.set(ids[i], {x: 75 + 950*(i+1)/(ids.length+1),
            y: keys.length === 1 ? 320 : 50 + index*gapY});
        }
      }
      return points;
    }
    const radius = Math.min(265, 65 + Math.sqrt(n) * 14);
    nodes.forEach((node, i) => {
      const theta = 2*Math.PI*(i+randHash(node.id)*0.18)/n;
      points.set(node.id, {x:550+radius*Math.cos(theta),
        y:325+radius*Math.sin(theta)});
    });
    const repulse = 1900;
    for (let tick = 0; tick < 65; tick++) {
      const forces = new Map(nodes.map(node => [node.id, {x:0,y:0}]));
      for (let i = 0; i < n; i++) for (let j = i+1; j < n; j++) {
        const a = points.get(nodes[i].id), b = points.get(nodes[j].id);
        const dx = a.x-b.x, dy = a.y-b.y;
        const d2 = Math.max(80, dx*dx + dy*dy);
        const f = repulse/d2;
        forces.get(nodes[i].id).x += dx*f;
        forces.get(nodes[i].id).y += dy*f;
        forces.get(nodes[j].id).x -= dx*f;
        forces.get(nodes[j].id).y -= dy*f;
      }
      for (const e of graph.edges) {
        const a=points.get(e.from), b=points.get(e.to);
        const dx=b.x-a.x, dy=b.y-a.y;
        const d=Math.max(1,Math.hypot(dx,dy));
        const force=(d-115)*0.006;
        forces.get(e.from).x += dx/d*force;
        forces.get(e.from).y += dy/d*force;
        forces.get(e.to).x -= dx/d*force;
        forces.get(e.to).y -= dy/d*force;
      }
      const rate = 1 - 0.68*tick/65;
      for (const node of nodes) {
        const p=points.get(node.id), f=forces.get(node.id);
        p.x = Math.max(45,Math.min(1055,p.x + Math.max(-20,Math.min(20,f.x+(.55e3-p.x)*.004))*rate));
        p.y = Math.max(35,Math.min(605,p.y + Math.max(-20,Math.min(20,f.y+(325-p.y)*.004))*rate));
      }
    }
    return points;
  }
  function draw() {
    const layer = $("graph-layer"); layer.replaceChildren();
    const active = state.active;
    const empty = $("empty-state");
    $("save-btn").disabled = !active || !state.db || Boolean(state.savedId);
    $("export-one").disabled = !active;
    if (!active) {
      empty.hidden = false;
      $("count-nodes").textContent = "—"; $("count-edges").textContent = "—";
      $("graph-type").textContent = "—"; $("count-visible").textContent = "—";
      $("active-name").textContent = "尚未選取案例。可先下載範例 CSV 試用。";
      $("root-options").replaceChildren();
      return;
    }
    empty.hidden = true;
    const info = core.topology(active);
    $("count-nodes").textContent = String(info.nodes);
    $("count-edges").textContent = String(info.edges);
    $("graph-type").textContent = info.hasCycle ? "有環網路" : "無環有向圖";
    const selector = $("root-filter").value.trim();
    let rootId = "", rootWarning = "";
    if (selector) {
      const exact = active.nodes.find(n => n.id === selector);
      const aliases = active.nodes.filter(n => n.label === selector);
      if (exact) rootId = exact.id;
      else if (aliases.length === 1) rootId = aliases[0].id;
      else rootWarning = aliases.length > 1
        ? "有多個節點使用相同名稱，請輸入完整 ID；目前顯示全圖。"
        : "找不到指定節點，請從提示中選擇完整 ID；目前顯示全圖。";
    }
    const radiusVal = $("radius").value;
    const radius = radiusVal === "all" ? "all" : Number(radiusVal);
    const graph = core.neighborhood(active, rootId, radius, $("direction").value);
    $("count-visible").textContent = graph.nodes.length + " / " + graph.edges.length;
    const mode = $("layout-mode").value;
    $("graph-help").textContent = rootWarning || (mode === "hierarchy"
      ? "階層按有向關係排列，循環圖會選取顯示起點，不把循環誤判為上下級。點節點可做局部分析。"
      : "提示：點選節點可以只看它幾步內的關係；滾輪縮放、拖曳空白處平移。箭頭保留原始方向。");
    const options = $("root-options");
    options.replaceChildren();
    for (const node of active.nodes) {
      const opt = doc.createElement("option");
      opt.value = node.id;
      opt.label = node.label === node.id ? node.id : node.label;
      options.append(opt);
    }
    const locations = coordinates(graph, mode);
    const degree = new Map(graph.nodes.map(n => [n.id,0]));
    for (const edge of graph.edges) {
      degree.set(edge.from, degree.get(edge.from)+edge.weight);
      degree.set(edge.to, degree.get(edge.to)+edge.weight);
    }
    const shownNames = new Set([...degree.entries()]
      .sort((a,b) => b[1]-a[1]).slice(0, 32).map(x=>x[0]));
    for (const edge of graph.edges) {
      const from=locations.get(edge.from), to=locations.get(edge.to);
      if (!from || !to) continue;
      const dx=to.x-from.x, dy=to.y-from.y;
      const distance=Math.max(1,Math.hypot(dx,dy));
      const ux=dx/distance, uy=dy/distance;
      const line = edge.from === edge.to
        ? svg("path", {
          d: "M "+(from.x-11)+" "+(from.y-12)+
            " C "+(from.x-82)+" "+(from.y-94)+
            " "+(from.x+82)+" "+(from.y-94)+
            " "+(from.x+13)+" "+(from.y-11),
          class: "edge-line" + (edge.weight>1 ? " weighted" : ""),
          "marker-end": "url(#arrowhead)",
        })
        : svg("line", {
          x1: from.x+ux*17, y1: from.y+uy*17,
          x2: to.x-ux*23, y2: to.y-uy*23,
          class: "edge-line" + (edge.weight>1 ? " weighted" : ""),
          "marker-end": "url(#arrowhead)",
        });
      const tip=svg("title"); tip.textContent=edge.from+" → "+edge.to+
        (edge.weight>1 ? "（件數："+edge.weight+"）" : "");
      line.append(tip);layer.append(line);
    }
    for (const node of graph.nodes) {
      const p = locations.get(node.id);
      if (!p) continue;
      const group = svg("g");
      const circle = svg("circle", {cx:p.x, cy:p.y, r:16,
        class:"node-circle" + (rootId===node.id ? " node-root" : ""),
        tabindex:"0", role:"button", "aria-label":"以 "+node.label+" 為局部起點"});
      const tip = svg("title"); tip.textContent=node.id===node.label
        ? node.id : node.label+"（"+node.id+"）";
      circle.append(tip);
      function chooseRoot() {
        $("root-filter").value=node.id;
        resetCamera(); draw();
      }
      circle.addEventListener("click", chooseRoot);
      circle.addEventListener("keydown", e => {
        if (e.key === "Enter" || e.key === " ") {e.preventDefault();chooseRoot();}
      });
      group.append(circle);
      if (graph.nodes.length <= 32 || $("all-labels").checked || shownNames.has(node.id)) {
        const short=node.label.length>18 ? node.label.slice(0,17)+"…" : node.label;
        const label=svg("text", {x:p.x,y:p.y+34,class:"node-text","text-anchor":"middle"});
        label.textContent=short;
        group.append(label);
      }
      layer.append(group);
    }
  }

  async function readText(file) {
    if (!file || file.size > core.MAX_FILE_CHARS) {
      throw Error("檔案不得超過 2 MB。");
    }
    const bytes=await file.arrayBuffer();
    try {return new TextDecoder("utf-8",{fatal:true}).decode(bytes);}
    catch (_) {throw Error("檔案不是有效的 UTF-8。請用 UTF-8 格式重新存成 CSV。");}
  }
  async function createCase(event) {
    event.preventDefault();
    try {
      const files = [...$("edge-files").files];
      if (!files.length || files.length>5) throw Error("請選擇 1 至 5 份關係 CSV。");
      const texts=await Promise.all(files.map(readText));
      const labels=$("labels-file").files[0];
      const graph=core.importGraph($("case-name").value,texts,
        labels ? await readText(labels) : "");
      state.active=core.validateCase(graph);
      state.savedId=null;
      $("root-filter").value="";
      resetCamera();draw();await refreshLibrary();
      $("active-name").textContent=graph.title+" · 尚未儲存";
      message("已完成預覽："+graph.nodes.length+" 個節點、"+
        graph.edges.length+" 條有向連線。滿意後請按「儲存這個案例」。","success");
      $("analysis-panel").scrollIntoView({behavior:"smooth",block:"start"});
    } catch (e) {message("無法建立案例："+e.message,"error");}
  }
  async function saveActive() {
    if (!state.active || !state.db) return;
    try {
      const record={...core.validateCase(state.active), id:newId(),
        createdAt:new Date().toISOString()};
      await insertBounded([record]);
      state.savedId=record.id;
      await refreshLibrary();draw();
      $("active-name").textContent=record.title+" · 已儲存於此瀏覽器";
      message("案例已儲存！建議用「備份全部案例」下載 JSON 保存。","success");
    } catch(e) {message("儲存失敗："+e.message,"error");}
  }
  function exportActive() {
    if (!state.active) return;
    download("jaal-case.json",JSON.stringify({
      format:"jaal-local-cases",schemaVersion:1,
      cases:[state.active]},null,2));
  }
  async function backupAll() {
    try {
      // Another tab can save/delete at any moment; NEVER back up the stale
      // state.records snapshot. Read persisted data immediately before export.
      const records = await readRecords();
      if (!records.length) {
        await refreshLibrary();
        message("目前沒有已儲存案例可備份。");
        return;
      }
      download("jaal-cases-backup.json", JSON.stringify({
        format: "jaal-local-cases", schemaVersion: 1,
        cases: records,
      }, null, 2));
      await refreshLibrary();
      message("已備份最新 " + records.length +
        " 個案例。JSON 含原始關係資料，請妥善保管。", "success");
    } catch (e) {message("備份失敗：" + e.message, "error");}
  }
  async function restoreBackup() {
    const file=$("restore-file").files[0];
    if (!file) return;
    try {
      if (!state.db) throw Error("本機儲存不可用，無法還原備份。");
      if (file.size > 96*1024*1024) throw Error("備份檔不可超過 96 MB。");
      const text=await file.text();
      let value;
      try {value=JSON.parse(text);}
      catch (_) {throw Error("JSON 格式錯誤。");}
      if (!value || value.format!=="jaal-local-cases" ||
          value.schemaVersion!==1 || !Array.isArray(value.cases) ||
          value.cases.length <1 || value.cases.length>core.MAX_CASES) {
        throw Error("不是支援的 Jaal 案例備份。");
      }
      const records=value.cases.map(item=>({...core.validateCase(item),
        id:newId(),createdAt:new Date().toISOString()}));
      await insertBounded(records);
      await refreshLibrary();
      message("成功還原 "+records.length+" 個案例。原有案例未被覆蓋。","success");
    } catch (e) {message("還原失敗："+e.message,"error");}
    finally {$("restore-file").value="";}
  }

  function bindInteraction() {
    const canvas=$("graph-canvas");
    canvas.addEventListener("pointerdown", event=>{
      if (event.button!==0 || event.target.closest(".node-circle")) return;
      canvas.setPointerCapture(event.pointerId);
      state.drag={x:event.clientX,y:event.clientY,
        atX:state.camera.x,atY:state.camera.y};
      canvas.classList.add("dragging");
    });
    canvas.addEventListener("pointermove", event=>{
      if (!state.drag) return;
      const rect=canvas.getBoundingClientRect();
      const ratioX=state.camera.w/rect.width, ratioY=state.camera.h/rect.height;
      state.camera.x=state.drag.atX-(event.clientX-state.drag.x)*ratioX;
      state.camera.y=state.drag.atY-(event.clientY-state.drag.y)*ratioY;
      applyCamera();
    });
    function stopDrag(){state.drag=null;canvas.classList.remove("dragging");}
    canvas.addEventListener("pointerup",stopDrag);
    canvas.addEventListener("pointercancel",stopDrag);
    canvas.addEventListener("wheel",event=>{
      if (!state.active) return;
      event.preventDefault();
      zoom(event.deltaY<0 ? .88 : 1.12);
    },{passive:false});
    $("zoom-in").addEventListener("click",()=>zoom(.83));
    $("zoom-out").addEventListener("click",()=>zoom(1.2));
    $("reset-view").addEventListener("click",()=>{
      $("root-filter").value="";resetCamera();draw();
    });
    for (const id of ["layout-mode","root-filter","radius","direction","all-labels"]) {
      $(id).addEventListener("change",()=>{resetCamera();draw();});
    }
  }
  async function init() {
    $("create-form").addEventListener("submit",createCase);
    $("save-btn").addEventListener("click",saveActive);
    $("export-one").addEventListener("click",exportActive);
    $("export-all").addEventListener("click",backupAll);
    $("refresh-list").addEventListener("click", async () => {
      try {await refreshLibrary(); message("已更新此瀏覽器中的案例清單。","success");}
      catch (e) {message(e.message,"error");}
    });
    $("restore-file").addEventListener("change",restoreBackup);
    $("sample-btn").addEventListener("click",()=>{
      download("jaal-example-edges.csv",
        "\ufeffparent,child,count\r\n總經理,研發部,1\r\n總經理,業務部,1\r\n研發部,專案A,2\r\n業務部,專案A,3\r\n專案A,交付成果,1\r\n",
        "text/csv;charset=utf-8");
      message("已下載範例 CSV。您也可自行製作從 A 指向 B 的關係清單。","success");
    });
    bindInteraction();
    draw();
    try {
      state.db=await openDatabase();await refreshLibrary();draw();
    } catch(e) {
      state.db=null;$("save-btn").disabled=true;
      message("此瀏覽器無法使用本機儲存（"+e.message+"）。仍可預覽及匯出單一案例，但不能保存或還原。","error");
    }
  }
  doc.addEventListener("DOMContentLoaded",()=>{init().catch(e=>message(e.message,"error"));});
})(window, document);
