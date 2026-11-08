/* Adaptive vis-network node labels, actual hover detail and user pins.
 * Operates on the ORIGINAL visdcc DataSet only; no additional graph renderer,
 * server requests, untrusted code generation or source Graph mutations.
 * The original mode/temporal/community/local-focus projections run first.
 */
(function (root) {
  "use strict";
  const state = {
    net: null, instance: null, pinned: new Set(), density: "smart",
    remembered: new Map(), shown: new Set(), pending: false,
    tooltip: null, hovered: null, count: 0, preferChinese: false,
  };
  const doc = root.document || null;
  const ownedPrefix = "__jaal_internal_community__";
  function isPoint(p) {
    return p && Number.isFinite(p.x) && Number.isFinite(p.y);
  }
  function translatedName(id) {
    const labels = root.dash_clientside && root.dash_clientside.jaal_visible_labels;
    if (labels && typeof labels.resolve === "function") {
      return labels.resolve(id, Boolean(labels.preferChinese));
    }
    return String(id);
  }
  function originalName(id, fallback) {
    // A collapsed box has a meaningful two-line aggregate label and must
    // never be replaced with its opaque internal node ID.
    if (String(id).startsWith(ownedPrefix)) return fallback || "社群";
    const name = translatedName(id);
    return typeof name === "string" && name.trim() ? name : String(id);
  }
  function collision(a, b) {
    return a.l < b.r && b.l < a.r && a.t < b.b && b.t < a.b;
  }
  function candidates(nodes, edges, positions, screen, scale, focus) {
    const degree = new Map();
    for (const edge of edges) {
      if (edge.hidden) continue;
      const a = String(edge.from), b = String(edge.to);
      degree.set(a, (degree.get(a) || 0) + 1);
      degree.set(b, (degree.get(b) || 0) + 1);
    }
    const viewport = screen && screen.viewport;
    const top = nodes.filter(node => !node.hidden).map(node => {
      const id = String(node.id);
      const box = id.startsWith(ownedPrefix);
      const pinned = state.pinned.has(id) || id === focus;
      const critical = pinned || box;
      const priority = (pinned ? 1000000 : 0) + (box ? 600000 : 0) +
        (degree.get(id) || 0) * 60;
      const pos = positions[id];
      const px = isPoint(pos) && screen && typeof screen.toDOM === "function"
        ? screen.toDOM(pos) : null;
      const name = originalName(id, state.remembered.get(id));
      const width = Math.min(360, 12 + [...name].reduce(
        (s, ch) => s + (ch.codePointAt(0) > 255 ? 12 : 7), 0));
      const bounds = px && isPoint(px) ? {
        l: px.x - width / 2 - 5, r: px.x + width / 2 + 5,
        t: px.y + 10, b: px.y + 32
      } : null;
      const onScreen = !viewport || !px ||
        (px.x > -80 && px.x < viewport.width + 80 &&
         px.y > -60 && px.y < viewport.height + 60);
      return {node, id, name, critical, pinned, priority, bounds, onScreen};
    });
    top.sort((a,b) => b.priority-a.priority || a.id.localeCompare(b.id));
    // At far zoom levels only show a few representatives. A selected root
    // and manually pinned IDs are NEVER suppressed by density selection.
    const cap = scale < 0.22 ? 20 : scale < 0.45 ? 48 :
      scale < 0.85 ? 95 : 165;
    return {top, cap};
  }
  function choose(items, cap, all) {
    const shown = new Set(), boxes = [];
    let count = 0;
    for (const item of items) {
      if (!item.onScreen && !item.critical) continue;
      if (item.critical) {
        shown.add(item.id);
        if (item.bounds) boxes.push(item.bounds);
        continue;
      }
      if (all) {shown.add(item.id); continue;}
      if (count >= cap) continue;
      if (item.bounds && boxes.some(box => collision(box,item.bounds))) continue;
      shown.add(item.id);
      if (item.bounds) boxes.push(item.bounds);
      count += 1;
    }
    return shown;
  }
  function refresh() {
    state.pending = false;
    const instance = state.instance, net = state.net;
    if (!instance || !instance.nn || !net ||
        typeof instance.nn.get !== "function" ||
        typeof instance.nn.update !== "function") return;
    const nodes = instance.nn.get(), edges = instance.ee?.get?.() || [];
    if (!Array.isArray(nodes) || !nodes.length) return;
    const visible = nodes.filter(n => !n.hidden);
    const focus = root.dash_clientside?.jaal_local_focus;
    if (!focus?.root && visible.length <= 90 && !state.pinned.size &&
        state.density === "smart") return;
    const rootId = focus?.root || null;
    const scale = typeof net.getScale === "function" ? net.getScale() : 1;
    const positions = typeof net.getPositions === "function"
      ? net.getPositions() : {};
    const el = net.body?.container;
    const rect = el && typeof el.getBoundingClientRect === "function"
      ? el.getBoundingClientRect() : null;
    const screen = {
      viewport: rect ? {width:rect.width,height:rect.height} : null,
      toDOM: typeof net.canvasToDOM === "function"
        ? p => net.canvasToDOM(p) : null
    };
    const {top,cap} = candidates(visible,edges,positions,screen,scale,rootId);
    // Preserve unchanged behavior for original small cases (regression
    // expectations of real Jaal), unless an explicit local focus is active.
    const all = state.density === "all" || (!rootId && visible.length <= 90);
    const selected = choose(top,cap,all);
    state.shown = selected;
    const changes = [];
    for (const node of nodes) {
      const id = String(node.id);
      if (typeof node.label === "string" && node.label &&
          (node.label !== state.remembered.get(id) ||
           !state.remembered.has(id))) {
        state.remembered.set(id,node.label);
      }
      const base = id.startsWith(ownedPrefix)
        ? (state.remembered.get(id) || "社群")
        : (state.remembered.get(id) || originalName(id, id));
      const text = node.hidden ? (node.label || "") :
        selected.has(id) ? base : "";
      if (String(node.label ?? "") !== text) changes.push({id:node.id,label:text});
    }
    if (changes.length) instance.nn.update(changes);
  }
  function schedule() {
    if (state.pending) return;
    state.pending = true;
    if (typeof root.requestAnimationFrame === "function")
      root.requestAnimationFrame(refresh);
    else refresh();
  }
  function ensureTooltip() {
    if (!doc || !doc.body) return null;
    if (state.tooltip && state.tooltip.isConnected) return state.tooltip;
    const pop = doc.createElement("div");
    pop.id = "jaal-node-float-detail";
    pop.setAttribute("role","status");
    pop.hidden = true;
    const title = doc.createElement("div");
    title.className = "jaal-node-float-title";
    const caption = doc.createElement("div");
    caption.className = "jaal-node-float-id";
    const hint = doc.createElement("div");
    hint.className = "jaal-node-float-hint";
    hint.textContent = "右鍵節點可快速釘選／取消釘選";
    const button = doc.createElement("button");
    button.type = "button";
    button.className = "jaal-node-pin-button";
    button.addEventListener("click", e => {
      e.stopPropagation();
      if (state.hovered !== null) togglePin(state.hovered);
      pop.hidden = true;
    });
    pop.append(title,caption,hint,button);
    // Do not leave a dangling tooltip when host embeds this Jaal in iframe.
    doc.body.appendChild(pop);
    state.tooltip = pop;
    return pop;
  }
  function showHover(id, domPoint) {
    const pop = ensureTooltip();
    if (!pop) return;
    const key = String(id);
    state.hovered = key;
    const title = pop.querySelector(".jaal-node-float-title");
    const caption = pop.querySelector(".jaal-node-float-id");
    const button = pop.querySelector(".jaal-node-pin-button");
    const fallback = state.remembered.get(key) || key;
    title.textContent = originalName(key, fallback);
    caption.textContent = title.textContent !== key ? "節點 ID：" + key : key;
    button.textContent = state.pinned.has(key) ? "取消釘選名稱" : "釘選重要名稱";
    const rect = state.net?.body?.container?.getBoundingClientRect?.();
    const x = (rect?.left || 0) + (domPoint?.x || 0);
    const y = (rect?.top || 0) + (domPoint?.y || 0);
    pop.style.left = Math.max(8,Math.min(x+16,(root.innerWidth||1100)-285))+"px";
    pop.style.top = Math.max(8,Math.min(y+16,(root.innerHeight||700)-145))+"px";
    pop.hidden = false;
  }
  function togglePin(id) {
    const key = String(id);
    if (state.pinned.has(key)) state.pinned.delete(key);
    else if (state.pinned.size < 100) state.pinned.add(key);
    schedule();
  }
  function attach(instance) {
    const net = instance.net;
    if (!net || state.net === net) return;
    state.net = net;
    state.remembered.clear();
    state.hovered = null;
    if (typeof net.setOptions === "function") {
      net.setOptions({interaction:{hover:true}});
    }
    if (typeof net.on !== "function") return;
    net.on("zoom",schedule);
    net.on("dragEnd",schedule);
    net.on("stabilized",schedule);
    net.on("hoverNode",event => showHover(event.node,event.pointer?.DOM));
    net.on("blurNode",() => {
      // Allow a user to move from the canvas to the detail button.
      if (state.tooltip) {
        if (typeof root.setTimeout === "function") root.setTimeout(() => {
          if (state.tooltip && !state.tooltip.matches(":hover"))
            state.tooltip.hidden = true;
        },650);
        else state.tooltip.hidden = true;
      }
    });
    net.on("oncontext",event => {
      const nodeId = typeof net.getNodeAt === "function"
        ? net.getNodeAt(event.pointer?.DOM) : null;
      if (nodeId === null || nodeId === undefined) return;
      event.event?.preventDefault?.();
      togglePin(nodeId);
      showHover(nodeId,event.pointer?.DOM);
    });
  }
  function sync() {
    if (!this || !this.nn || !this.net) return;
    if (state.instance && state.instance !== this) state.remembered.clear();
    state.instance = this;
    attach(this);
    schedule();
  }
  if (doc && typeof doc.addEventListener === "function") {
    doc.addEventListener("click", e => {
      const button = e.target?.closest?.("#jaal-label-density-toggle");
      if (!button) return;
      state.density = state.density === "smart" ? "all" : "smart";
      button.textContent = state.density === "smart"
        ? "標籤：智慧顯示" : "標籤：全部顯示";
      button.setAttribute("aria-pressed", String(state.density === "all"));
      schedule();
    });
  }
  root.dash_clientside = root.dash_clientside || {};
  root.dash_clientside.jaal_label_intelligence = {sync,schedule,togglePin,choose,candidates,state};
  if (typeof module !== "undefined" && module.exports) {
    module.exports = {sync,schedule,togglePin,choose,candidates,state};
  }
})(typeof window !== "undefined" ? window : globalThis);
