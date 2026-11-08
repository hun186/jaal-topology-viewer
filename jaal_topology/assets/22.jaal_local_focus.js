/* Browser-only projection of a server-validated k-hop neighborhood.
 * Only original IDs are used; no user-controlled data becomes JS source.
 * Every action is reversible. The authoritative visdcc props.data stays intact.
 */
(function (root) {
  "use strict";
  const state = {ids: null, root: null, pendingFit: false, signature: "",
    fitQueued: false, fitAttempts: 0, anchorPositions: Object.create(null)};

  function setSelection(packet) {
    const previous = state.signature;
    if (!packet || typeof packet.root !== "string" ||
        !Array.isArray(packet.ids) || packet.ids.length > 20000 ||
        !packet.ids.every(id => typeof id === "string")) {
      state.ids = null;
      state.root = null;
      state.signature = "";
      state.pendingFit = false;
      return;
    }
    const ids = new Set(packet.ids);
    if (!ids.has(packet.root)) {
      state.ids = null;
      state.root = null;
      state.signature = "";
      state.pendingFit = false;
      return;
    }
    state.ids = ids;
    state.root = packet.root;
    state.signature = JSON.stringify([packet.root,packet.ids]);
    if (previous !== state.signature) {
      state.pendingFit = true;
      state.fitAttempts = 0;
    }
  }

  function scoped(source) {
    if (!source || !Array.isArray(source.nodes) ||
        !Array.isArray(source.edges) || !state.ids) return source;
    const ids = state.ids;
    return {
      nodes: source.nodes.filter(n => ids.has(String(n.id))),
      edges: source.edges.filter(e =>
        ids.has(String(e.from)) && ids.has(String(e.to))),
    };
  }

  function apply() {
    if (!this || !this.nn || !this.ee) return;
    const original = this.props && this.props.data;
    if (!original || !Array.isArray(original.nodes) ||
        !Array.isArray(original.edges)) return;
    const temporal = root.dash_clientside &&
      root.dash_clientside.jaal_temporal;
    const source = temporal && typeof temporal.stableSource === "function"
      ? temporal.stableSource(original) : original;
    const ids = state.ids;
    const net = this.net;
    if (state.pendingFit && ids && net &&
        typeof net.getPositions === "function") {
      // Remember the last actually visible coordinates BEFORE reducing to
      // the local subset. Isolated 0-hop nodes can temporarily have no
      // getPositions() entry after their surrounding edges are hidden.
      const before = net.getPositions();
      for (const id of ids) {
        const p = before[id];
        if (p && Number.isFinite(p.x) && Number.isFinite(p.y)) {
          state.anchorPositions[id] = {x:p.x,y:p.y};
        }
      }
    }
    const nodes = source.nodes.map(n => {
      const visible = !Boolean(n.hidden) && (!ids || ids.has(String(n.id)));
      const old = state.pendingFit && ids && ids.has(String(n.id))
        ? state.anchorPositions[String(n.id)] : null;
      return {
        ...n, hidden: !visible,
        ...(old ? {x:old.x,y:old.y} : {}),
      };
    });
    const edges = source.edges.map(e => ({
      ...e, hidden: Boolean(e.hidden) ||
        Boolean(ids && (!ids.has(String(e.from)) || !ids.has(String(e.to)))),
    }));
    const camera = net && typeof net.getViewPosition === "function" &&
      typeof net.getScale === "function" ? {
        position: net.getViewPosition(), scale: net.getScale(),
    } : null;
    // Retain node IDs and previous x/y coordinates, even when outside scope.
    // This prevents regrouping or camera fit() at every timeline tick.
    if (nodes.length) this.nn.update(nodes);
    if (edges.length) this.ee.update(edges);
    if (camera && typeof net.moveTo === "function") {
      net.moveTo({...camera, animation: false});
    }
  }

  function afterProjection() {
    if (!state.pendingFit || !state.root || !this?.net || !this?.nn ||
        state.fitQueued) return;
    const component = this;
    const net = component.net;
    if (typeof net.fit !== "function") return;
    state.fitQueued = true;
    function tryFit() {
      if (!state.pendingFit || !state.root) {
        state.fitQueued = false;
        return;
      }
      // visdcc's DataSet is updated synchronously, but vis-network does not
      // necessarily reindex active nodes until its next redraw. Fitting on
      // the same graph.run call can therefore target *zero* drawn nodes.
      const visible = (component.nn.get?.() || [])
        .filter(n => !n.hidden).map(n => n.id);
      const positions = typeof net.getPositions === "function"
        ? net.getPositions(visible) : null;
      const drawable = !positions || visible.some(id => {
        const p = positions[id];
        return p && Number.isFinite(p.x) && Number.isFinite(p.y);
      });
      if ((!visible.length || !drawable) && state.fitAttempts < 45 &&
          typeof root.requestAnimationFrame === "function") {
        state.fitAttempts++;
        root.requestAnimationFrame(tryFit);
        return;
      }
      state.fitQueued = false;
      // Last-resort isolated-root positioning: vis-network may temporarily
      // return null from getPositions despite its DataSet and nodeIndices
      // showing the selected node. Use its pre-filter world position rather
      // than snapping the camera to an unrelated full-graph cluster.
      if (visible.length === 1 && !drawable &&
          typeof net.moveTo === "function") {
        const anchor = state.anchorPositions[String(visible[0])];
        if (anchor && Number.isFinite(anchor.x) && Number.isFinite(anchor.y)) {
          net.moveTo({
            position: {x:anchor.x,y:anchor.y}, scale:1,
            animation:{duration:260,easingFunction:"easeInOutQuad"}
          });
          state.pendingFit = false;
          return;
        }
      }
      // Never silently clear pendingFit if no usable world position exists.
      if (!visible.length || !drawable) return;
      state.pendingFit = false;
      // Fit every visible original/quotient member. Using the initial
      // dataset-order 2500 IDs can exclude an outlying selected root.
      net.fit({
        nodes: visible,
        animation: {duration:260,easingFunction:"easeInOutQuad"},
        maxZoomLevel:1.3
      });
    }
    if (typeof root.requestAnimationFrame === "function")
      root.requestAnimationFrame(tryFit);
    else tryFit();
  }

  root.dash_clientside = root.dash_clientside || {};
  Object.assign(state, {setSelection, scoped, apply, afterProjection});
  root.dash_clientside.jaal_local_focus = state;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = state;
  }
})(typeof window !== "undefined" ? window : globalThis);
