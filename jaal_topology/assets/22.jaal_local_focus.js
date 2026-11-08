/* Browser-only projection of a server-validated k-hop neighborhood.
 * Only original IDs are used; no user-controlled data becomes JS source.
 * Every action is reversible. The authoritative visdcc props.data stays intact.
 */
(function (root) {
  "use strict";
  const state = {ids: null, root: null};

  function setSelection(packet) {
    if (!packet || typeof packet.root !== "string" ||
        !Array.isArray(packet.ids) || packet.ids.length > 20000 ||
        !packet.ids.every(id => typeof id === "string")) {
      state.ids = null;
      state.root = null;
      return;
    }
    const ids = new Set(packet.ids);
    if (!ids.has(packet.root)) {
      state.ids = null;
      state.root = null;
      return;
    }
    state.ids = ids;
    state.root = packet.root;
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
    const nodes = source.nodes.map(n => ({
      ...n, hidden: Boolean(n.hidden) || Boolean(ids && !ids.has(String(n.id))),
    }));
    const edges = source.edges.map(e => ({
      ...e, hidden: Boolean(e.hidden) ||
        Boolean(ids && (!ids.has(String(e.from)) || !ids.has(String(e.to)))),
    }));
    const net = this.net;
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

  root.dash_clientside = root.dash_clientside || {};
  Object.assign(state, {setSelection, scoped, apply});
  root.dash_clientside.jaal_local_focus = state;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = state;
  }
})(typeof window !== "undefined" ? window : globalThis);
