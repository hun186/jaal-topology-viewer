/* Bounded temporal playback directly on the real visdcc/vis-network DataSets.
 * The browser receives PRECOMPUTED frames once on selection changes; autoplay
 * ticks never fetch from Python/Vercel. Original Jaal props.data stays intact
 * for Search/Filter/Color/Size callbacks and for correct restore.
 *
 * Nothing from event records is compiled into executable source. Only this
 * trusted bundled JS runs inside the graph.run bridge.
 */
(function (root) {
  "use strict";
  const state = {frame: null, fullLabels: false, keyLabels: new Set()};

  function key(a, b) { return JSON.stringify([String(a), String(b)]); }

  function setFrame(frame) {
    state.frame = frame && Array.isArray(frame.edges) ? frame : null;
  }

  function setLabelUniverse(source) {
    // Pick leaders from the immutable full-period graph, not the current
    // rolling slice. Otherwise label identities flicker every animation tick.
    if (!source || !Array.isArray(source.edges)) return;
    const totals = new Map();
    for (const edge of source.edges) {
      const count = Number.isSafeInteger(edge.mailCount) && edge.mailCount > 0
        ? edge.mailCount : 1;
      for (const id of [String(edge.from), String(edge.to)]) {
        totals.set(id, (totals.get(id) || 0) + count);
      }
    }
    state.keyLabels = new Set([...totals].sort(
      (a, b) => b[1] - a[1] || a[0].localeCompare(b[0])
    ).slice(0, 12).map(pair => pair[0]));
  }

  function setDisplayOptions(values) {
    state.fullLabels = Array.isArray(values) && values.includes("all");
  }

  function displayLabel(id, label) {
    if (!state.frame || state.fullLabels ||
        state.keyLabels.has(String(id))) return String(label);
    return "";
  }

  function projectSource(source) {
    if (!source || !Array.isArray(source.nodes) || !Array.isArray(source.edges)) {
      return source;
    }
    if (!state.frame) return source;
    const pairCounts = new Map();
    const nodes = new Set();
    const sent = new Map(), received = new Map();
    for (const item of state.frame.edges) {
      if (!Array.isArray(item) || item.length !== 3) continue;
      const a = String(item[0]), b = String(item[1]), count = item[2];
      if (!Number.isSafeInteger(count) || count <= 0 || count > 1000000) continue;
      pairCounts.set(key(a, b), count);
      nodes.add(a); nodes.add(b);
      sent.set(a, (sent.get(a) || 0) + count);
      received.set(b, (received.get(b) || 0) + count);
    }
    const projectedNodes = source.nodes.filter(n => nodes.has(String(n.id)))
      .map(n => {
        const id = String(n.id);
        const out = sent.get(id) || 0, incoming = received.get(id) || 0;
        return {...n, SentEmails: out, ReceivedEmails: incoming,
          TotalEmails: out + incoming};
      });
    const projectedEdges = source.edges.filter(e =>
      pairCounts.has(key(e.from, e.to))
    ).map(e => {
      const count = pairCounts.get(key(e.from, e.to));
      return {...e, mailCount: count,
        width: Math.min(8, 1 + Math.log2(count + 1)),
        title: "合成郵件：" + count + " 封（選取時間窗）"};
    });
    return {nodes: projectedNodes, edges: projectedEdges};
  }

  // The displayed graph is a fixed-universe graph.  Absent participants
  // remain in the actual vis DataSet with hidden=true, retaining their ID,
  // x/y and all original metadata.  No new physics layout is triggered when
  // an event window adds/removes an active relationship.
  function stableSource(source) {
    if (!source || !Array.isArray(source.nodes) ||
        !Array.isArray(source.edges) || !state.frame) return source;
    const active = projectSource(source);
    const activeNodes = new Map(active.nodes.map(n => [String(n.id), n]));
    const activeEdges = new Map(active.edges.map(e => [String(e.id), e]));
    return {
      nodes: source.nodes.map(n => {
        const live = activeNodes.get(String(n.id));
        return {
          ...n,
          ...(live ? {
            SentEmails: live.SentEmails,
            ReceivedEmails: live.ReceivedEmails,
            TotalEmails: live.TotalEmails,
          } : {
            SentEmails: 0, ReceivedEmails: 0, TotalEmails: 0,
          }),
          hidden: Boolean(n.hidden) || !live,
        };
      }),
      edges: source.edges.map(e => {
        const live = activeEdges.get(String(e.id));
        return {
          ...e, ...(live || {}),
          hidden: Boolean(e.hidden) || !live,
        };
      }),
    };
  }

  function freezePhysics(instance) {
    // Physics keeps re-running if links are deleted/reinserted each frame.
    // Once the initial full layout is present, freeze it for this playback
    // session. Users can still drag nodes; the next frame remembers that.
    if (!instance || !instance.net) return;
    if (!instance.__jaalTemporalLayoutLocked &&
        typeof instance.net.setOptions === "function") {
      instance.net.setOptions({physics: {enabled: false}});
      instance.__jaalTemporalLayoutLocked = true;
    }
  }

  function reconcile(ds, rows) {
    if (!ds || !Array.isArray(rows)) return;
    const wanted = new Set(rows.map(row => String(row.id)));
    const old = ds.getIds().filter(id => !wanted.has(String(id)));
    if (old.length) ds.remove(old);
    if (rows.length) ds.update(rows);
  }

  function noteRender(instance, source) {
    if (!state.frame || !instance || !instance.nn || !instance.ee) return;
    state.lastRendered = {
      date: state.frame.date,
      from: state.frame.from,
      to: state.frame.to,
      sourceNodes: source.nodes.filter(n => !n.hidden).length,
      sourceEdges: source.edges.filter(e => !e.hidden).length,
      drawnNodes: instance.nn.get().filter(n => !n.hidden).length,
      drawnEdges: instance.ee.get().filter(e => !e.hidden).length,
    };
  }

  function apply() {
    if (!state.frame || !this || !this.nn || !this.ee) return;
    const fullSource = this.props && this.props.data;
    const source = projectSource(fullSource);
    const universe = stableSource(fullSource);
    if (!source || !universe) return;
    freezePhysics(this);
    const net = this.net;
    const camera = net && typeof net.getViewPosition === "function" &&
      typeof net.getScale === "function"
      ? {position: net.getViewPosition(), scale: net.getScale()} : null;
    const saved = this.__jaalTemporalPositions || Object.create(null);
    const oldPositions = net && typeof net.getPositions === "function"
      ? net.getPositions() : {};
    for (const [id, pos] of Object.entries(oldPositions)) {
      if (Number.isFinite(pos.x) && Number.isFinite(pos.y) &&
          !id.startsWith("__jaal_internal_")) saved[id] = pos;
    }
    const viewNodes = universe.nodes.map(node => {
      const coord = saved[String(node.id)];
      return coord && Number.isFinite(coord.x) && Number.isFinite(coord.y)
        ? {...node, x: coord.x, y: coord.y} : node;
    });
    // Keep the same node IDs and edge IDs permanently in the DataSets.
    // Setting hidden/visible is one bounded in-place update per frame.
    // Removing/reinserting every edge caused a flash and a layout restart.
    if (viewNodes.length) this.nn.update(viewNodes);
    if (universe.edges.length) this.ee.update(universe.edges);
    if (camera && typeof net.moveTo === "function") {
      net.moveTo({...camera, animation: false});
    }
    this.__jaalTemporalPositions = saved;
    noteRender(this, source);
  }

  function triggerName() {
    const d = root.dash_clientside;
    const ctx = d && d.callback_context;
    const changed = ctx && ctx.triggered && ctx.triggered[0] &&
      ctx.triggered[0].prop_id;
    return String(changed || "").split(".")[0];
  }

  function playback(playClicks, backClicks, forwardClicks, ticks, selection,
                    index, isDisabled, step, doLoop) {
    const d = root.dash_clientside;
    const unchanged = d && d.no_update;
    if (!selection || !Array.isArray(selection.frames) || !selection.frames.length) {
      return [0, true, "▶ 播放"];
    }
    const lo = Number(selection.start_index);
    const hi = Number(selection.end_index);
    const cur = Number.isInteger(index) ? Math.max(lo, Math.min(index, hi)) : hi;
    const advance = [1, 2, 5, 7].includes(step) ? step : 1;
    const loop = Array.isArray(doLoop) && doLoop.includes("loop");
    const trigger = triggerName();
    if (trigger === "jaal-temporal-frames" || !trigger) {
      return [hi, true, "▶ 播放"];
    }
    if (trigger === "jaal-temporal-play") {
      const nextDisabled = !isDisabled;
      return [!nextDisabled && cur === hi ? lo : cur,
        nextDisabled, nextDisabled ? "▶ 播放" : "⏸ 暫停"];
    }
    if (trigger === "jaal-temporal-back" ||
        trigger === "jaal-temporal-forward") {
      return [Math.max(lo, Math.min(hi, cur +
        (trigger === "jaal-temporal-back" ? -advance : advance))),
        true, "▶ 播放"];
    }
    if (trigger === "jaal-temporal-tick" && isDisabled === false) {
      const next = cur + advance;
      if (next > hi) {
        return loop ? [lo, false, "⏸ 暫停"] : [hi, true, "▶ 播放"];
      }
      if (next === hi && !loop) return [hi, true, "▶ 播放"];
      return [next, false, "⏸ 暫停"];
    }
    return [unchanged, unchanged, unchanged];
  }

  function choose(index, packet) {
    if (!packet || !Array.isArray(packet.frames) || !packet.frames.length) {
      return [null, "沒有符合條件的時間片"];
    }
    const lo = packet.start_index, hi = packet.end_index;
    const selected = Number.isInteger(index) ?
      Math.max(lo, Math.min(index, hi)) : hi;
    const frame = packet.frames[selected - lo];
    if (!frame) return [null, "時間片不存在"];
    const period = frame.mode === "rolling" ? "滑動時間窗" : "累積至目前";
    const summary = period + "｜" + frame.from + " ～ " + frame.to + "　" +
      frame.messages + " 封信、" + frame.nodes + " 位參與者、" +
      frame.links + " 條有向關係";
    return [frame, summary];
  }

  function speed(value) {
    const allowed = [350, 700, 1400, 2500];
    return allowed.includes(value) ? value : 700;
  }

  root.dash_clientside = root.dash_clientside || {};
  Object.assign(state, {
    setFrame, setLabelUniverse, setDisplayOptions, displayLabel,
    projectSource, stableSource, freezePhysics,
    apply, noteRender, playback, choose, speed,
  });
  root.dash_clientside.jaal_temporal = state;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = state;
  }
})(typeof window !== "undefined" ? window : globalThis);
