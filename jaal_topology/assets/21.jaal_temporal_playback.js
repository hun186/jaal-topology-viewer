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
  const state = {frame: null};

  function key(a, b) { return JSON.stringify([String(a), String(b)]); }

  function setFrame(frame) {
    state.frame = frame && Array.isArray(frame.edges) ? frame : null;
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
      sourceNodes: source.nodes.length,
      sourceEdges: source.edges.length,
      drawnNodes: instance.nn.getIds().length,
      drawnEdges: instance.ee.getIds().length,
    };
  }

  function apply() {
    if (!state.frame || !this || !this.nn || !this.ee) return;
    const source = projectSource(this.props && this.props.data);
    if (!source) return;
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
    const viewNodes = source.nodes.map(node => {
      const coord = saved[String(node.id)];
      return coord && Number.isFinite(coord.x) && Number.isFinite(coord.y)
        ? {...node, x: coord.x, y: coord.y} : node;
    });
    const oldEdges = this.ee.getIds();
    if (oldEdges.length) this.ee.remove(oldEdges);
    reconcile(this.nn, viewNodes);
    reconcile(this.ee, source.edges);
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
    const summary = frame.from + " ～ " + frame.to + "　" +
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
    setFrame, projectSource, apply, noteRender, playback, choose, speed,
  });
  root.dash_clientside.jaal_temporal = state;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = state;
  }
})(typeof window !== "undefined" ? window : globalThis);
