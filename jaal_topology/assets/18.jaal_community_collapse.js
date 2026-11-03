/* Directed community view using a seeded, server-computed Louvain partition.
 * Synthetic clusters exist ONLY in visdcc DataSets. Original source is read
 * from props.data and never mutated; switching modes restores it exactly.
 */
(function (root) {
  "use strict";
  const MIN_GROUP_SIZE = 3;
  const stateAPI = {partition: {}, edgeLength: 120};

  function setEdgeLength(value) {
    if (Number.isInteger(value) && value >= 60 && value <= 300) {
      stateAPI.edgeLength = value;
    }
  }

  function point(p) {
    return p && Number.isFinite(p.x) && Number.isFinite(p.y);
  }

  function anchoredMember(group, id, members, anchor, otherAnchors) {
    const ordered = [...members].sort();
    const index = ordered.indexOf(id);
    const closest = otherAnchors.filter(point).reduce((distance, other) =>
      Math.min(distance, Math.hypot(other.x - anchor.x, other.y - anchor.y)), Infinity);
    const separation = stateAPI.edgeLength / 120;
    const limit = Number.isFinite(closest) ? Math.max(32, closest * 0.38) : Infinity;
    const radius = Math.min(limit, (28 + 22 * Math.sqrt(index + 1)) * separation);
    const angle = index * 2.399963229728653;
    return {x: anchor.x + radius * Math.cos(angle),
            y: anchor.y + radius * Math.sin(angle)};
  }
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

  function makeView(source, membership, opened, preferChinese, retainHidden = false) {
    if (!source || !Array.isArray(source.nodes) || !Array.isArray(source.edges)) {
      throw new Error("Community view expects the original Jaal graph");
    }
    const allIds = new Set(source.nodes.map(node => String(node.id)));
    const allEdgeIds = new Set(source.edges.map(edge => String(edge.id)));
    let nodePrefix = "__jaal_internal_community__";
    let edgePrefix = "__jaal_internal_link__";
    while ([...allIds].some(id => id.startsWith(nodePrefix))) nodePrefix += "_";
    while ([...allEdgeIds].some(id => id.startsWith(edgePrefix))) edgePrefix += "_";
    const activeIds = new Set(source.nodes.filter(n => !n.hidden).map(n => String(n.id)));
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
      const live = members.get(group).filter(id => activeIds.has(id)).length;
      nodes.push({
        id: clusterId, shape: "box",
        label: "社群 " + (sorted.indexOf(group) + 1) + "\n" +
          (retainHidden ? live + " 活躍 / " : "") + count + " 個節點",
        title: "Louvain 社群；" + count + " 個節點（拓樸分群，非上下級）",
        color: {background: "#dbeafe", border: "#3b82f6"},
        margin: 12,
        hidden: retainHidden && live === 0,
      });
    }
    const pairs = new Map(), internal = new Map();
    const syntheticIds = new Set(collapsed.values());
    for (const edge of source.edges) {
      // Keep the complete edge universe while animating. A rolling window
      // only hides edges; changing endpoints/IDs every tick causes re-layout.
      if (edge.hidden && !retainHidden) continue;
      const from = String(edge.from), to = String(edge.to);
      if (!allIds.has(from) || !allIds.has(to)) continue;
      const a = representative[from], b = representative[to];
      if (a === b && syntheticIds.has(a)) {
        // Hide only edges wholly inside a collapsed synthetic community.
        // A real self-loop must remain inspectable when its node is visible.
        if (!edge.hidden) internal.set(a, (internal.get(a) || 0) + 1);
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
      const originals = pair.originals;
      const active = originals.filter(edge => !edge.hidden);
      const count = retainHidden ? active.length : originals.length;
      const volume = active.reduce((sum, edge) =>
        sum + (Number.isSafeInteger(edge.mailCount) ? edge.mailCount : 1), 0);
      const stillOriginal = originals.length === 1 &&
        representative[String(originals[0].from)] === String(originals[0].from) &&
        representative[String(originals[0].to)] === String(originals[0].to);
      const drawn = stillOriginal ? {...originals[0]} : {
        // A pair-derived ID is stable across temporal frames even when
        // another pair has zero activity, unlike a changing ordinal.
        id: retainHidden
          ? edgePrefix + JSON.stringify([pair.from, pair.to])
          : edgePrefix + (ordinal++),
        from: pair.from, to: pair.to, arrows: "to",
        width: Math.min(8, 1 + Math.log2((retainHidden ? volume : count) + 1)),
        label: count > 1 ? String(count) : undefined,
        title: retainHidden
          ? "本時間窗：" + volume + " 封信、" + count + " 條有向關係"
          : "原始有向關係數：" + count,
        hidden: retainHidden && count === 0,
      };
      edges.push(drawn);
      // The inspector identifies source relations, not invented reversals.
      edgeSources[String(drawn.id)] = (retainHidden ? active : originals)
        .map(edge => ({
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
    // A temporal slice is NOT a Search/Filter. Its inactive nodes and edges
    // stay present with hidden=true so communities keep their identities.
    const stable = temporal && typeof temporal.stableSource === "function"
      ? temporal.stableSource(source) : source;
    const focus = root.dash_clientside && root.dash_clientside.jaal_local_focus;
    return focus && typeof focus.scoped === "function"
      ? focus.scoped(stable) : stable;
  }

  function project(instance) {
    const state = instance.__jaalCommunity;
    if (!state || !state.active || !instance.nn || !instance.ee) return;
    const source = sourceData(instance);
    if (!source || !Array.isArray(source.nodes) || !Array.isArray(source.edges)) return;
    // Search and Filter can change the upstream DataSet. Temporarily display
    // the exact filtered source instead of showing stale synthetic communities.
    const original = instance.props && instance.props.data;
    const filtered = Boolean(original && (
      original.nodes.some(n => n.hidden) ||
      original.edges.some(e => e.hidden)
    ));
    const timeline = root.dash_clientside && root.dash_clientside.jaal_temporal;
    const temporalActive = Boolean(timeline && timeline.frame);
    if (filtered) closeInspector();
    const view = filtered ? {
      nodes: source.nodes.map(node => ({
        ...node,
        label: nameFor(node.id, state.zh),
        hidden: Boolean(node.hidden),
      })),
      edges: source.edges.map(edge => ({...edge, hidden: Boolean(edge.hidden)})),
      clusterToGroup: {},
    } : makeView(source, state.partition, state.opened, state.zh, temporalActive);
    const net = instance.net;
    const camera = net && typeof net.getViewPosition === "function" &&
      typeof net.getScale === "function"
      ? {position: net.getViewPosition(), scale: net.getScale()} : null;
    const oldPos = Object.assign(Object.create(null),
      net && typeof net.getPositions === "function"
        ? net.getPositions() : {});
    const nodePositions = state.positions || Object.create(null);
    state.clusterPositions = state.clusterPositions || Object.create(null);
    for (const clusterId of Object.keys(state.view?.clusterToGroup || {})) {
      if (point(oldPos[clusterId])) state.clusterPositions[clusterId] = oldPos[clusterId];
    }
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
        const group = Object.prototype.hasOwnProperty.call(state.partition, id)
          ? String(state.partition[id]) : null;
        const clusterId = group !== null &&
          Object.keys(state.view?.clusterToGroup || {}).find(
            key => state.view.clusterToGroup[key] === group);
        const anchor = clusterId &&
          (point(oldPos[clusterId]) ? oldPos[clusterId] : state.clusterPositions[clusterId]);
        if (point(anchor)) {
          // Expanding a box MUST place its newly exposed members around that
          // box, not at their distant positions from the original full graph.
          const otherAnchors = Object.entries(state.clusterPositions)
            .filter(([key]) => key !== clusterId).map(([,pos]) => pos);
          const placed = anchoredMember(group, id, view.members.get(group) || [],
                                        anchor, otherAnchors);
          node.x = placed.x; node.y = placed.y;
        } else {
          const cached = nodePositions[id];
          if (point(cached)) {node.x = cached.x; node.y = cached.y;}
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
        const cachedCluster = state.clusterPositions[String(node.id)];
        if (point(cachedCluster)) {
          // Re-collapse around the old box anchor; never teleport to a
          // far-away member centroid or the initial constellation origin.
          node.x = cachedCluster.x; node.y = cachedCluster.y;
        } else if (temporalActive) {
          // Stable, legible constellation for the mail demo. A member centroid
          // often places every synthetic group on top of the same dense core.
          const groups = [...view.members.keys()].sort();
          const angle = 2 * Math.PI * groups.indexOf(group) / groups.length;
          const radius = Math.max(290, groups.length * 65) *
            (stateAPI.edgeLength / 120);
          node.x = radius * Math.cos(angle);
          node.y = radius * Math.sin(angle);
        } else {
          const positions = view.members.get(group).map(id => nodePositions[id])
            .filter(p => p && Number.isFinite(p.x) && Number.isFinite(p.y));
          if (positions.length) {
            node.x = positions.reduce((s, p) => s + p.x, 0) / positions.length;
            node.y = positions.reduce((s, p) => s + p.y, 0) / positions.length;
          }
        }
      }
    }
    // The explicit edge-length control scales the visible frozen geometry,
    // not just vis physics (which is deliberately disabled during playback).
    const previous = state.spacing || stateAPI.edgeLength;
    if (previous !== stateAPI.edgeLength) {
      const ratio = stateAPI.edgeLength / previous;
      const coords = view.nodes.map(n => point(n) ? {x:n.x,y:n.y} : oldPos[String(n.id)])
        .filter(point);
      if (coords.length) {
        const center = {x: coords.reduce((v,p)=>v+p.x,0)/coords.length,
                        y: coords.reduce((v,p)=>v+p.y,0)/coords.length};
        const scale = p => ({x:center.x+(p.x-center.x)*ratio,
                             y:center.y+(p.y-center.y)*ratio});
        for (const node of view.nodes) {
          const current = point(node) ? node : oldPos[String(node.id)];
          if (point(current)) Object.assign(node, scale(current));
        }
        for (const [key,p] of Object.entries(state.clusterPositions)) {
          if (point(p)) state.clusterPositions[key] = scale(p);
        }
        for (const [key,p] of Object.entries(nodePositions)) {
          if (point(p)) nodePositions[key] = scale(p);
        }
      }
    }
    state.spacing = stateAPI.edgeLength;
    // No new fit() call. The temporal quotient keeps all IDs and only
    // updates hidden/weight fields. Normal static mode retains legacy reset.
    if (!temporalActive) {
      const presentEdges = instance.ee.getIds();
      if (presentEdges.length) instance.ee.remove(presentEdges);
    }
    reconcile(instance.nn, view.nodes);
    reconcile(instance.ee, view.edges);
    if (camera && net && typeof net.moveTo === "function") {
      net.moveTo({...camera, animation: false});
    }
    state.positions = nodePositions;
    state.view = view;
    state.filtered = filtered;
    const temporal = root.dash_clientside && root.dash_clientside.jaal_temporal;
    if (temporal && typeof temporal.noteRender === "function") {
      temporal.noteRender(instance, source);
    }
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
    if (timeline && timeline.frame && typeof timeline.freezePhysics === "function") {
      timeline.freezePhysics(this);
    }
    const partition = stateAPI.partition && typeof stateAPI.partition === "object"
      ? stateAPI.partition : {};
    // An unchanged grouping must NOT close an expanded community at every
    // date tick. Only a deliberate dynamic repartition changes the key.
    const currentKey = graphSignature(source) +
      JSON.stringify(Object.entries(partition).sort());
    let state = this.__jaalCommunity;
    if (!state || state.key !== currentKey) {
      state = {
        key: currentKey, opened: new Set(),
        positions: state && state.positions ? state.positions : Object.create(null),
        clusterPositions: state && state.clusterPositions
          ? state.clusterPositions : Object.create(null),
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
  Object.assign(stateAPI, {activate, restore, makeView, explainEdge, setEdgeLength,
    anchoredMember});
  root.dash_clientside.jaal_community_collapse = stateAPI;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = stateAPI;
  }
})(typeof window !== "undefined" ? window : globalThis);
