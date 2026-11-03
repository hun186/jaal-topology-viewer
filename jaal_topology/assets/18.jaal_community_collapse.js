/* Directed community view using a seeded, server-computed Louvain partition.
 * Synthetic clusters exist ONLY in visdcc DataSets. Original source is read
 * from props.data and never mutated; switching modes restores it exactly.
 */
(function (root) {
  "use strict";
  const MIN_GROUP_SIZE = 3;
  const stateAPI = {partition: {}};
  const INSPECTOR_ID = "jaal-community-edge-inspector";

  function nameFor(id, zh) {
    const labels = root.dash_clientside && root.dash_clientside.jaal_visible_labels;
    return labels && typeof labels.resolve === "function"
      ? labels.resolve(id, zh) : String(id);
  }

  function graphSignature(source) {
    return JSON.stringify([
      source.nodes.map(n => String(n.id)).sort(),
      source.edges.map(e => JSON.stringify([e.from, e.to, e.id])).sort(),
    ]);
  }

  function makeView(source, membership, opened, preferChinese) {
    if (!source || !Array.isArray(source.nodes) || !Array.isArray(source.edges)) {
      throw new Error("Community view expects the original Jaal graph");
    }
    const allIds = new Set(source.nodes.map(node => String(node.id)));
    const allEdgeIds = new Set(source.edges.map(edge => String(edge.id)));
    let nodePrefix = "__jaal_internal_community__";
    let edgePrefix = "__jaal_internal_link__";
    while ([...allIds].some(id => id.startsWith(nodePrefix))) nodePrefix += "_";
    while ([...allEdgeIds].some(id => id.startsWith(edgePrefix))) edgePrefix += "_";
    const members = new Map();
    for (const node of source.nodes) {
      const id = String(node.id);
      const group = membership && Object.prototype.hasOwnProperty.call(membership, id)
        ? String(membership[id]) : null;
      if (group === null) continue;
      if (!members.has(group)) members.set(group, []);
      members.get(group).push(id);
    }
    const collapsed = new Map();
    const clusterToGroup = Object.create(null);
    const sorted = [...members.keys()].sort();
    sorted.forEach((group, index) => {
      if (members.get(group).length < MIN_GROUP_SIZE || opened.has(group)) return;
      const clusterId = nodePrefix + index;
      collapsed.set(group, clusterId);
      clusterToGroup[clusterId] = group;
    });
    const representative = Object.create(null); // allow IDs such as "__proto__"
    const nodes = [];
    for (const node of source.nodes) {
      const id = String(node.id);
      const group = membership && Object.prototype.hasOwnProperty.call(membership, id)
        ? String(membership[id]) : null;
      const replacement = group !== null ? collapsed.get(group) : undefined;
      representative[id] = replacement || id;
      if (!replacement) nodes.push({
        ...node,
        label: nameFor(id, preferChinese),
      });
    }
    for (const group of sorted) {
      const clusterId = collapsed.get(group);
      if (!clusterId) continue;
      const count = members.get(group).length;
      nodes.push({
        id: clusterId, shape: "box",
        label: "社群 " + (sorted.indexOf(group) + 1) + "\n" + count + " 個節點",
        title: "Louvain 社群；" + count + " 個節點（拓樸分群，非上下級）",
        color: {background: "#dbeafe", border: "#3b82f6"},
        margin: 12,
      });
    }
    const pairs = new Map(), internal = new Map();
    const syntheticIds = new Set(collapsed.values());
    for (const edge of source.edges) {
      if (edge.hidden) continue;
      const from = String(edge.from), to = String(edge.to);
      if (!allIds.has(from) || !allIds.has(to)) continue;
      const a = representative[from], b = representative[to];
      if (a === b && syntheticIds.has(a)) {
        // Hide only edges wholly inside a collapsed synthetic community.
        // A real self-loop must remain inspectable when its node is visible.
        internal.set(a, (internal.get(a) || 0) + 1);
        continue;
      }
      const key = JSON.stringify([a, b]);
      if (!pairs.has(key)) pairs.set(key, {from: a, to: b, originals: []});
      pairs.get(key).originals.push(edge);
    }
    let ordinal = 0;
    const edges = [];
    const edgeSources = Object.create(null);
    for (const pair of pairs.values()) {
      const originals = pair.originals, count = originals.length;
      const stillOriginal = count === 1 &&
        representative[String(originals[0].from)] === String(originals[0].from) &&
        representative[String(originals[0].to)] === String(originals[0].to);
      const drawn = stillOriginal ? {...originals[0]} : {
        id: edgePrefix + (ordinal++),
        from: pair.from, to: pair.to, arrows: "to",
        width: Math.min(8, 1 + Math.log2(count + 1)),
        label: count > 1 ? String(count) : undefined,
        title: "原始有向關係數：" + count,
      };
      edges.push(drawn);
      // Every visible quotient edge carries its exact input relations.
      // The two directions of a reciprocal community pair stay separate.
      edgeSources[String(drawn.id)] = originals.map(edge => ({
        id: String(edge.id), from: String(edge.from), to: String(edge.to),
      }));
    }
    return {nodes, edges, internal, clusterToGroup, representative,
            aggregated: pairs, members, edgeSources};
  }


  function explainEdge(view, visibleEdgeId) {
    if (!view || !view.edgeSources ||
        !Object.prototype.hasOwnProperty.call(view.edgeSources, String(visibleEdgeId))) {
      return [];
    }
    return view.edgeSources[String(visibleEdgeId)].map(item => ({...item}));
  }

  function closeInspector() {
    const doc = root.document;
    const panel = doc && doc.getElementById(INSPECTOR_ID);
    if (panel && panel.parentNode) panel.parentNode.removeChild(panel);
  }

  function showEdgeInspector(instance, view, visibleEdgeId, zh) {
    const origins = explainEdge(view, visibleEdgeId);
    // Anchor the inspector inside the real vis-network canvas container.
    // Fixed-to-iframe-viewport bottom can put its close button BELOW the
    // user's visible parent-page viewport when Stage 4 lazily embeds Jaal.
    const host = instance && instance.net && instance.net.body &&
      instance.net.body.container;
    if (!origins.length || !root.document || !host ||
        typeof host.appendChild !== "function") return;
    const doc = root.document;
    closeInspector();
    const panel = doc.createElement("section");
    panel.id = INSPECTOR_ID;
    panel.setAttribute("role", "region");
    panel.setAttribute("aria-label", "社群有向連線原始來源");
    Object.assign(panel.style, {
      position: "absolute", right: "12px", top: "12px", zIndex: "1000",
      maxWidth: "min(450px, calc(100% - 24px))",
      maxHeight: "calc(100% - 24px)",
      overflow: "auto", boxSizing: "border-box", background: "#fff",
      border: "1px solid #6486c5", borderRadius: "8px",
      boxShadow: "0 4px 18px rgba(0, 0, 0, 0.16)",
      font: "13px/1.4 system-ui, sans-serif", color: "#1f2937",
      padding: "10px 12px",
    });
    const header = doc.createElement("div");
    header.style.display = "flex";
    header.style.gap = "8px";
    header.style.justifyContent = "space-between";
    const title = doc.createElement("strong");
    title.textContent = "原始有向關係（" + origins.length + " 條）";
    const close = doc.createElement("button");
    close.type = "button";
    close.textContent = "關閉";
    close.setAttribute("aria-label", "關閉原始關係檢視");
    close.addEventListener("click", closeInspector);
    header.append(title, close);
    panel.appendChild(header);
    const description = doc.createElement("p");
    description.textContent = "箭頭方向逐條來自原圖，不代表社群之間的父子層級。";
    description.style.margin = "6px 0";
    panel.appendChild(description);
    const list = doc.createElement("ol");
    list.style.paddingLeft = "20px";
    list.style.margin = "0";
    // Hard cap on DOM creation; all records remain available in source graph.
    for (const origin of origins.slice(0, 100)) {
      const item = doc.createElement("li");
      // NEVER use innerHTML: node IDs and translated labels are untrusted.
      item.textContent = nameFor(origin.from, zh) + " → " +
        nameFor(origin.to, zh);
      item.title = origin.from + " → " + origin.to;
      list.appendChild(item);
    }
    panel.appendChild(list);
    if (origins.length > 100) {
      const rest = doc.createElement("p");
      rest.textContent = "僅列出前 100 條；其餘 " + (origins.length - 100) +
        " 條可在原始圖逐項檢視。";
      panel.appendChild(rest);
    }
    host.appendChild(panel);
  }

  function reconcile(dataset, rows) {
    const ids = new Set(rows.map(row => String(row.id)));
    const obsolete = dataset.getIds().filter(id => !ids.has(String(id)));
    if (obsolete.length) dataset.remove(obsolete);
    if (rows.length) dataset.update(rows);
  }

  function sourceData(instance) {
    const source = instance.props && instance.props.data;
    const temporal = root.dash_clientside && root.dash_clientside.jaal_temporal;
    return temporal && typeof temporal.projectSource === "function" ?
      temporal.projectSource(source) : source;
  }

  function project(instance) {
    const state = instance.__jaalCommunity;
    if (!state || !state.active || !instance.nn || !instance.ee) return;
    const source = sourceData(instance);
    if (!source || !Array.isArray(source.nodes) || !Array.isArray(source.edges)) return;
    // Search and Filter can change the upstream DataSet. Temporarily display
    // the exact filtered source instead of showing stale synthetic communities.
    const filtered = source.nodes.some(n => n.hidden) ||
      source.edges.some(e => e.hidden);
    if (filtered) closeInspector();
    const view = filtered ? {
      nodes: source.nodes.map(node => ({
        ...node,
        label: nameFor(node.id, state.zh),
        hidden: Boolean(node.hidden),
      })),
      edges: source.edges.map(edge => ({...edge, hidden: Boolean(edge.hidden)})),
      clusterToGroup: {},
    } : makeView(source, state.partition, state.opened, state.zh);
    const net = instance.net;
    const camera = net && typeof net.getViewPosition === "function" &&
      typeof net.getScale === "function"
      ? {position: net.getViewPosition(), scale: net.getScale()} : null;
    const oldPos = Object.assign(Object.create(null),
      net && typeof net.getPositions === "function"
        ? net.getPositions() : {});
    const nodePositions = state.positions || Object.create(null);
    for (const [id, pos] of Object.entries(oldPos)) {
      if (Number.isFinite(pos.x) && Number.isFinite(pos.y) &&
          !id.startsWith("__jaal_internal_community__")) {
        nodePositions[id] = pos;
      }
    }
    // Reuse cached original positions when members are exposed again;
    // new members start near the cluster they came from, without camera fit.
    if (!filtered && view.members) {
      const oldIdSet = new Set(instance.nn.getIds().map(String));
      for (const node of view.nodes) {
        if (oldIdSet.has(String(node.id))) continue;
        const id = String(node.id);
        const cached = nodePositions[id];
        if (cached && Number.isFinite(cached.x) && Number.isFinite(cached.y)) {
          node.x = cached.x; node.y = cached.y;
          continue;
        }
        const group = Object.prototype.hasOwnProperty.call(state.partition, id)
          ? String(state.partition[id]) : null;
        if (group !== null) {
          const clusterId = Object.keys(state.view?.clusterToGroup || {}).find(
            id => state.view.clusterToGroup[id] === group
          );
          const anchor = clusterId && oldPos[clusterId];
          if (anchor && Number.isFinite(anchor.x) && Number.isFinite(anchor.y)) {
            const order = (view.members.get(group) || []).indexOf(id);
            const angle = order * 2.399963229728653; // golden angle
            const radius = 18 * Math.sqrt(order + 1);
            node.x = anchor.x + radius * Math.cos(angle);
            node.y = anchor.y + radius * Math.sin(angle);
          }
        }
      }
      for (const node of view.nodes) {
        const group = view.clusterToGroup[String(node.id)];
        if (!group) continue;
        // Preserve the CURRENT drawn position of an already present cluster.
        // Recomputing its member centroid would undo the user's drag.
        if (oldIdSet.has(String(node.id))) {
          const current = oldPos[String(node.id)];
          if (current && Number.isFinite(current.x) && Number.isFinite(current.y)) {
            node.x = current.x;
            node.y = current.y;
          }
          continue;
        }
        const positions = view.members.get(group).map(id => nodePositions[id])
          .filter(p => p && Number.isFinite(p.x) && Number.isFinite(p.y));
        if (positions.length) {
          node.x = positions.reduce((s, p) => s + p.x, 0) / positions.length;
          node.y = positions.reduce((s, p) => s + p.y, 0) / positions.length;
        }
      }
    }
    // No new fit() call: preserve the user's camera and zoom.
    const presentEdges = instance.ee.getIds();
    if (presentEdges.length) instance.ee.remove(presentEdges);
    reconcile(instance.nn, view.nodes);
    reconcile(instance.ee, view.edges);
    if (camera && net && typeof net.moveTo === "function") {
      net.moveTo({...camera, animation: false});
    }
    state.positions = nodePositions;
    state.view = view;
    state.filtered = filtered;
  }

  function restore() {
    closeInspector();
    const state = this.__jaalCommunity;
    if (!state || !state.active) return;
    state.active = false;
    const source = sourceData(this);
    if (!source || !this.nn || !this.ee) return;
    const edges = this.ee.getIds();
    if (edges.length) this.ee.remove(edges);
    reconcile(this.nn, source.nodes.map(n => ({...n, hidden: Boolean(n.hidden)})));
    reconcile(this.ee, source.edges.map(e => ({...e, hidden: Boolean(e.hidden)})));
    state.view = null;
    state.opened.clear(); // Re-entering the mode always starts collapsed.
  }

  function activate(preferChinese) {
    if (!this.nn || !this.ee || !this.net) return;
    const source = sourceData(this);
    if (!source || !Array.isArray(source.nodes) || !Array.isArray(source.edges)) return;
    const structural = root.dash_clientside && root.dash_clientside.jaal_structural_collapse;
    if (structural && typeof structural.restore === "function") {
      structural.restore.call(this);
    }
    const timeline = root.dash_clientside && root.dash_clientside.jaal_temporal;
    const windowKey = timeline && timeline.frame
      ? JSON.stringify([timeline.frame.from, timeline.frame.to]) : "";
    const currentKey = graphSignature(source) + windowKey;
    const partition = stateAPI.partition && typeof stateAPI.partition === "object"
      ? stateAPI.partition : {};
    let state = this.__jaalCommunity;
    if (!state || state.key !== currentKey) {
      state = {
        key: currentKey, opened: new Set(),
        positions: state && state.positions ? state.positions : Object.create(null),
      };
      this.__jaalCommunity = state;
    }
    state.active = true;
    state.partition = partition;
    state.zh = Boolean(preferChinese);
    if (!this.__jaalCommunityClickHook) {
      const component = this;
      this.net.on("click", function (event) {
        const current = component.__jaalCommunity;
        if (!current || !current.active || current.filtered || !current.view) return;
        const id = event && event.nodes && event.nodes.length
          ? String(event.nodes[0]) : null;
        if (!id) {
          const edge = event && event.edges && event.edges.length
            ? String(event.edges[0]) : null;
          if (edge !== null) showEdgeInspector(component, current.view, edge, current.zh);
          return;
        }
        closeInspector();
        const group = current.view.clusterToGroup[id] ||
          (Object.prototype.hasOwnProperty.call(current.partition, id)
            ? String(current.partition[id]) : null);
        if (group === null) return;
        if (current.opened.has(group)) current.opened.delete(group);
        else current.opened.add(group);
        project(component);
      });
      this.__jaalCommunityClickHook = true;
    }
    project(this);
  }

  root.dash_clientside = root.dash_clientside || {};
  Object.assign(stateAPI, {activate, restore, makeView, explainEdge});
  root.dash_clientside.jaal_community_collapse = stateAPI;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = stateAPI;
  }
})(typeof window !== "undefined" ? window : globalThis);
