/* Read-only SVG concept demo. This is intentionally NOT the Dash/Jaal runtime,
 * and its departmental grouping is NOT Louvain. Original IDs and directions
 * remain unchanged in the underlying source-derived graph.json. */
const NS = "http://www.w3.org/2000/svg";
const $ = id => document.getElementById(id);
const state = {
  graph: null, mode: "network", zh: true, term: "",
  expanded: new Set(), selected: null,
  view: {x: 0, y: 0, z: 1}, move: null, custom: new Map()
};
const svg = $("graph");

function svgEl(tag, attrs = {}, content = undefined) {
  const element = document.createElementNS(NS, tag);
  for (const [key, val] of Object.entries(attrs)) element.setAttribute(key, String(val));
  if (content !== undefined) element.textContent = String(content);
  return element;
}
function displayName(node) { return state.zh ? node.label : node.id; }
function teamName(node) { return node.team || "Executive"; }
function basePositions(nodes, mode) {
  const positions = new Map();
  if (mode !== "hierarchy") {
    nodes.forEach((node, i) => {
      const angle = i * 2.399963229728653;
      const radius = 42 + 310 * Math.sqrt((i + 0.5) / nodes.length);
      positions.set(node.id, {x: 600 + radius * Math.cos(angle), y: 380 + radius * Math.sin(angle)});
    });
    return positions;
  }
  const graph = state.graph;
  const root = graph.nodes.find(n => n.id === "CEO / Executive Office")?.id || nodes[0]?.id;
  const depth = new Map([[root, 0]]);
  const pending = [root], adj = new Map();
  for (const {from, to} of graph.edges) {
    if (!adj.has(from)) adj.set(from, []);
    adj.get(from).push(to);
  }
  while (pending.length) {
    const id = pending.shift();
    for (const dest of adj.get(id) || []) {
      if (!depth.has(dest)) { depth.set(dest, depth.get(id) + 1); pending.push(dest); }
    }
  }
  const fallbackDepth = Math.max(...depth.values(), 0) + 1;
  const buckets = new Map();
  for (const n of nodes) {
    const d = Math.min(depth.get(n.id) ?? fallbackDepth, 7);
    if (!buckets.has(d)) buckets.set(d, []);
    buckets.get(d).push(n.id);
  }
  for (const [level, bucket] of buckets) {
    bucket.sort((a, b) => a.localeCompare(b));
    bucket.forEach((id, i) => {
      positions.set(id, {x: 95 + level * 145, y: 45 + (i + 0.5) * 660 / bucket.length});
    });
  }
  return positions;
}
function projection() {
  const graph = state.graph;
  if (state.mode !== "teams") {
    const positions = basePositions(graph.nodes, state.mode);
    return {
      nodes: graph.nodes.map(n => ({...n, kind: "person", ...positions.get(n.id)})),
      edges: graph.edges.map(e => ({from: e.from, to: e.to, count: 1}))
    };
  }
  const grouped = new Map();
  for (const node of graph.nodes) {
    const team = teamName(node);
    if (!grouped.has(team)) grouped.set(team, []);
    grouped.get(team).push(node);
  }
  const teams = [...grouped].sort(([a], [b]) => a.localeCompare(b, "en"));
  const positions = new Map(), projectedNodes = [];
  teams.forEach(([team, members], i) => {
    const angle = i * Math.PI * 2 / teams.length - Math.PI / 2;
    const center = {x: 600 + 320 * Math.cos(angle), y: 380 + 235 * Math.sin(angle)};
    const id = "team:" + team;
    if (!state.expanded.has(team)) {
      projectedNodes.push({id, team, label: team, kind: "team", count: members.length, ...center});
      positions.set(team, id);
    } else {
      members.forEach((person, j) => {
        const phi = j * 2.399963229728653;
        const r = 18 + 83 * Math.sqrt((j + .5) / members.length);
        projectedNodes.push({...person, kind: "person", x: center.x + r * Math.cos(phi), y: center.y + r * Math.sin(phi)});
      });
    }
  });
  const membership = new Map(graph.nodes.map(n => [n.id,
    positions.get(teamName(n)) || n.id]));
  const byPair = new Map();
  for (const {from, to} of graph.edges) {
    const a = membership.get(from), b = membership.get(to);
    if (a === b && a.startsWith("team:")) continue; // counted in inspector, not lost from data
    const key = JSON.stringify([a, b]);
    if (!byPair.has(key)) byPair.set(key, {from: a, to: b, count: 0});
    byPair.get(key).count++;
  }
  return {nodes: projectedNodes, edges: [...byPair.values()]};
}
function updateInspector() {
  const selected = state.selected;
  const details = $("detailStats");
  details.replaceChildren();
  if (!selected || !state.graph) return;
  const isTeam = selected.startsWith("team:");
  const team = isTeam ? selected.slice(5) : null;
  const members = isTeam ? state.graph.nodes.filter(n => n.team === team) : [];
  const node = isTeam ? null : state.graph.nodes.find(n => n.id === selected);
  if (!node && !isTeam) return;
  const belongs = id => isTeam ? members.some(n => n.id === id) : id === selected;
  const inbound = state.graph.edges.filter(e => belongs(e.to)).length;
  const outbound = state.graph.edges.filter(e => belongs(e.from)).length;
  $("detailTitle").textContent = isTeam ? team : displayName(node);
  $("detailBody").textContent = isTeam
    ? "部門聚合僅用於示意，不代表 Louvain 社群。點此部門圖節點可展開／收攏。"
    : node.id;
  for (const [name, value] of [["向外關係", outbound], ["向內關係", inbound],
     ...(isTeam ? [["成員數量", members.length]] : [["所屬部門", node.team]])]) {
    const dt = document.createElement("dt"), dd = document.createElement("dd");
    dt.textContent = name; dd.textContent = String(value);
    details.append(dt, dd);
  }
}
function resetView() {
  state.view = {x: 0, y: 0, z: 1};
  state.custom.clear();
  render();
}
function render() {
  if (!state.graph) return;
  const p = projection();
  const m = new Map(p.nodes.map(n => [n.id, {...n, ...(state.custom.get(n.id) || {})}]));
  $("visibleNodes").textContent = String(p.nodes.length);
  const def = svgEl("defs");
  const arrow = svgEl("marker", {id: "arrow", markerWidth: 8, markerHeight: 8,
    refX: 8, refY: 4, orient: "auto", markerUnits: "userSpaceOnUse"});
  arrow.append(svgEl("path", {d: "M 0 0 L 8 4 L 0 8 Z", fill: "#91a8bd"}));
  def.append(arrow);
  const layer = svgEl("g", {transform: "translate(" + state.view.x + " " +
    state.view.y + ") scale(" + state.view.z + ")"});
  const links = svgEl("g", {"class": "edges"}), points = svgEl("g", {"class": "nodes"});
  const term = state.term.trim().toLocaleLowerCase();
  const memberMatches = n =>
    [n.id, n.label, n.team].some(x => String(x).toLocaleLowerCase().includes(term));
  const matches = n => {
    if (!term || memberMatches(n)) return true;
    // A collapsed group must remain searchable by ANY original member ID or
    // translated label, not only by its synthetic department name.
    return n.kind === "team" &&
      state.graph.nodes.some(original =>
        original.team === n.team && memberMatches(original));
  };
  for (const edge of p.edges) {
    const from = m.get(edge.from), to = m.get(edge.to);
    if (!from || !to) continue;
    const a = {x: from.x, y: from.y}, b = {x: to.x, y: to.y};
    const match = matches(from) || matches(to);
    const path = svgEl("path", {"class": "edge" + (term && !match ? " faded" : ""),
      "marker-end": "url(#arrow)"});
    const dx = b.x - a.x, dy = b.y - a.y, length = Math.max(1, Math.hypot(dx, dy));
    const nx = dx / length, ny = dy / length;
    const start = from.kind === "team" ? 23 : 11, end = to.kind === "team" ? 28 : 16;
    if (edge.from === edge.to) {
      path.setAttribute("d", "M " + (a.x + 6) + " " + (a.y - 11) +
        " C " + (a.x + 45) + " " + (a.y - 55) + " " + (a.x - 35) + " " +
        (a.y - 55) + " " + (a.x - 10) + " " + (a.y - 12));
    } else {
      const bend = Math.min(32, length * .12);
      const sx = a.x + nx * start, sy = a.y + ny * start;
      const ex = b.x - nx * end, ey = b.y - ny * end;
      path.setAttribute("d", "M " + sx + " " + sy + " Q " +
        ((sx + ex) / 2 - ny * bend) + " " + ((sy + ey) / 2 + nx * bend) +
        " " + ex + " " + ey);
    }
    path.append(svgEl("title", {}, edge.from + " → " + edge.to +
      " (" + edge.count + " distinct directed pairs)"));
    links.append(path);
  }
  const showLabels = p.nodes.length < 30 || state.mode === "teams";
  for (const n of p.nodes) {
    const pos = m.get(n.id), found = matches(n);
    const g = svgEl("g", {"class": "graph-node" +
      (n.kind === "team" ? " cluster" : "") +
      (term && !found ? " faded" : "") +
      (state.selected === n.id ? " selected" : ""),
      transform: "translate(" + pos.x + " " + pos.y + ")",
      "data-id": n.id, tabindex: 0, role: "button",
      "aria-label": n.kind === "team" ? n.team + "：展開或收合" : displayName(n)});
    g.append(svgEl("circle", {r: n.kind === "team" ? 24 : 10}));
    if (n.kind === "team") g.append(svgEl("text", {"class": "cluster-count", dy: 5}, n.count));
    if (showLabels || (term && found) || state.selected === n.id) {
      const label = n.kind === "team" ? n.team : displayName(n);
      g.append(svgEl("text", {"class": "node-label", x: 16, y: -12}, label.length > 24 ? label.slice(0, 23) + "…" : label));
    }
    g.append(svgEl("title", {}, n.kind === "team" ? n.team + " (" + n.count + " members)" : n.id));
    g.addEventListener("click", () => activateNode(n.id));
    g.addEventListener("keydown", ev => {
      if (ev.key === "Enter" || ev.key === " ") {ev.preventDefault(); activateNode(n.id);}
    });
    points.append(g);
  }
  layer.append(links, points);
  svg.replaceChildren(def, layer);
  updateInspector();
}
function activateNode(id) {
  state.selected = id;
  if (state.mode === "teams" && id.startsWith("team:")) {
    const team = id.slice(5);
    state.expanded.add(team);
  } else if (state.mode === "teams") {
    const node = state.graph.nodes.find(n => n.id === id);
    // Click member to collapse its department on a second click.
    if (state.selected === id && node && state.lastClicked === id) {
      state.expanded.delete(node.team);
      state.selected = "team:" + node.team;
    }
  }
  state.lastClicked = id;
  render();
}
for (const btn of document.querySelectorAll("[data-mode]")) {
  btn.addEventListener("click", () => {
    state.mode = btn.dataset.mode;
    state.expanded.clear(); state.custom.clear();
    state.selected = null; state.lastClicked = null;
    for (const button of document.querySelectorAll("[data-mode]")) {
      button.classList.toggle("active", button === btn);
      button.setAttribute("aria-pressed", String(button === btn));
    }
    render();
    $("liveStatus").textContent = btn.textContent + " 已啟用";
  });
}
$("chinese").addEventListener("change", e => {state.zh = e.target.checked; render();});
$("search").addEventListener("input", e => {state.term = e.target.value; render();});
$("reset").addEventListener("click", resetView);
svg.addEventListener("wheel", ev => {
  ev.preventDefault();
  state.view.z = Math.max(.4, Math.min(3, state.view.z * (ev.deltaY < 0 ? 1.1 : .9)));
  render();
}, {passive: false});
svg.addEventListener("pointerdown", ev => {
  if (ev.target.closest(".graph-node")) return;
  state.move = {x: ev.clientX, y: ev.clientY, tx: state.view.x, ty: state.view.y};
  svg.setPointerCapture(ev.pointerId);
});
svg.addEventListener("pointermove", ev => {
  if (!state.move) return;
  const rect = svg.getBoundingClientRect();
  state.view.x = state.move.tx + (ev.clientX - state.move.x) * 1200 / rect.width;
  state.view.y = state.move.ty + (ev.clientY - state.move.y) * 760 / rect.height;
  render();
});
svg.addEventListener("pointerup", () => {state.move = null;});
svg.addEventListener("pointercancel", () => {state.move = null;});
async function start() {
  try {
    const response = await fetch("./graph.json", {cache: "force-cache"});
    if (!response.ok) throw Error("Data HTTP " + response.status);
    const payload = await response.json();
    if (payload.kind !== "fictional-corporate-communications" ||
        payload.nodes.length !== 77 || payload.edges.length !== 169) {
      throw Error("Unexpected fixture contract");
    }
    state.graph = payload;
    $("nodeTotal").textContent = String(payload.nodes.length);
    $("edgeTotal").textContent = String(payload.edges.length);
    render();
    $("liveStatus").textContent = "示範圖已載入";
  } catch (error) {
    $("detailTitle").textContent = "無法載入示範資料";
    $("detailBody").textContent = String(error.message);
    $("liveStatus").textContent = "資料載入失敗";
  }
}
start();
