/* Synthetic corporate communication stress dataset; deterministic and offline.
 * All identities and messages are fictional. No external data or server calls.
 * Browser-only Canvas renderer is separate from the bounded Jaal/Dash gallery. */
(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.JaalStressCore = api;
})(typeof window !== "undefined" ? window : globalThis, function () {
  "use strict";
  const PRESETS = Object.freeze({
    "500": {nodes: 500, components: 1, label: "500 人 · 中型企業"},
    "3000": {nodes: 3000, components: 1, label: "3,000 人 · 大型企業"},
    "5000": {nodes: 5000, components: 1, label: "5,000 人 · 集團"},
    "20000": {nodes: 20000, components: 1, label: "20,000 人 · 超大型集團"},
    "islands": {nodes: 500, components: 3, label: "500 人 · 3 個獨立連通分量"},
  });
  const MAX_NODES = 20000;
  const MAX_EDGES = 100000;

  function buildScenario(key) {
    if (!Object.prototype.hasOwnProperty.call(PRESETS, key)) {
      throw Error("只允許預先定義的虛構壓測規模。");
    }
    const preset = PRESETS[key];
    const nodes = [], edges = [], departments = [], edgeIndex = new Map();
    let maxDepth = 0, weightTotal = 0, componentX = 0;

    function addEdge(source, target, weight, workflow) {
      if (source === target) return;
      const id = source + ":" + target;
      if (edgeIndex.has(id)) {
        const old = edges[edgeIndex.get(id)];
        old.weight += weight;
      } else {
        edgeIndex.set(id, edges.length);
        edges.push({source, target, weight, workflow});
      }
      weightTotal += weight;
      if (edges.length > MAX_EDGES) throw Error("合成連線超過安全上限。");
    }

    for (let component = 0; component < preset.components; component++) {
      const count = Math.floor(preset.nodes / preset.components) +
        (component < preset.nodes % preset.components ? 1 : 0);
      const deptCount = Math.min(200, Math.max(3, Math.floor(count / 82)));
      const regionCount = Math.max(1, Math.ceil(deptCount / 12));
      const cols = Math.ceil(Math.sqrt(deptCount * 1.6));
      const rows = Math.ceil(deptCount / cols);
      const compWidth = cols * 195 + 150;
      const compY = 95;
      const begin = nodes.length;
      const labelPrefix = "集團 " + (component + 1);
      let serial = 0;

      function addPerson(title, dept, manager, kind, level, ordinal) {
        serial++;
        const node = {
          id: "C" + String(component + 1).padStart(2, "0") +
              "-N" + String(serial).padStart(5, "0"),
          label: labelPrefix + "／" + title,
          component: component + 1, dept, kind, level, manager,
          x: 0, y: 0, ordinal: ordinal || 0,
        };
        const index = nodes.length;
        nodes.push(node);
        maxDepth = Math.max(maxDepth, level);
        if (manager !== null) {
          addEdge(index, manager, 2 + (serial * 13) % 11, "report");
          if (serial % 4 === 0) addEdge(manager, index, 1 + serial % 5, "reply");
        }
        return index;
      }

      const rootIndex = addPerson("總經理", -1, null, "executive", 0);
      const regions = [];
      for (let i = 0; i < regionCount; i++) {
        regions.push(addPerson("區域副總 " + String(i + 1).padStart(2, "0"),
          -1, rootIndex, "region", 1));
      }
      const localDepartments = [];
      for (let d = 0; d < deptCount; d++) {
        const deptId = departments.length;
        const centerX = componentX + 120 + (d % cols) * 195;
        const centerY = compY + 190 + Math.floor(d / cols) * 175;
        const title = "部門 " + String(d + 1).padStart(3, "0");
        const head = addPerson(title + "／部門主管", deptId,
          regions[Math.floor(d / 12)], "department", 2);
        const dept = {id:deptId, component:component + 1, title,
          head, x:centerX, y:centerY, count:1, slot:0, frontline:[], lastWorker:null};
        departments.push(dept);
        localDepartments.push(dept);
      }
      // Organizational hierarchy grows from team/group heads to program heads
      // and (for the largest scale) section heads. Workers are not random peers.
      for (const dept of localDepartments) {
        const teams = [];
        for (let i = 0; i < 3; i++) {
          teams.push(addPerson(dept.title + "／組長 " + (i + 1), dept.id,
            dept.head, "team", 3, ++dept.slot));
          dept.count++;
        }
        const groups = [];
        for (let i = 0; i < 6; i++) {
          groups.push(addPerson(dept.title + "／小組主管 " + (i + 1), dept.id,
            teams[i % teams.length], "group", 4, ++dept.slot));
          dept.count++;
        }
        let frontline = groups;
        if (count >= 3000) {
          const projects = [];
          for (let i = 0; i < 4; i++) {
            projects.push(addPerson(dept.title + "／專案經理 " + (i + 1),
              dept.id, groups[i % groups.length], "project", 5, ++dept.slot));
            dept.count++;
          }
          frontline = projects;
        }
        if (count >= 10000) {
          const sections = [];
          for (let i = 0; i < 6; i++) {
            sections.push(addPerson(dept.title + "／資深領班 " + (i + 1),
              dept.id, frontline[i % frontline.length], "section", 6, ++dept.slot));
            dept.count++;
          }
          frontline = sections;
        }
        dept.frontline = frontline;
      }
      const remainder = count - (nodes.length - begin);
      if (remainder < 0) throw Error("管理層配置超過員工總數。");
      for (let i = 0; i < remainder; i++) {
        const dept = localDepartments[i % localDepartments.length];
        const index = addPerson(dept.title + "／專員 " + String(i + 1).padStart(5,"0"),
          dept.id, dept.frontline[dept.slot % dept.frontline.length],
          "staff", nodes[dept.frontline[0]].level + 1, ++dept.slot);
        dept.count++;
        // Department-local collaboration plus occasional cross-functional
        // approvals yield plausible weighted directional traffic.
        if (dept.lastWorker !== null) {
          addEdge(index, dept.lastWorker, 1 + i % 9, "team");
          if (i % 5 === 0) addEdge(dept.lastWorker, index, 1 + i % 3, "reply");
        }
        dept.lastWorker = index;
        if (i % 17 === 0) {
          const other = localDepartments[(i + 1) % localDepartments.length];
          addEdge(index, other.head, 1 + i % 4, "cross-department");
        }
      }
      // Geometric clusters reflect departments (not simulated org containment
      // for email links). Components are separated by a large horizontal gap.
      nodes[rootIndex].x = componentX + compWidth / 2;
      nodes[rootIndex].y = 26;
      regions.forEach((id, i) => {
        nodes[id].x = componentX + (i + 1) * compWidth / (regions.length + 1);
        nodes[id].y = 91;
      });
      for (const dept of localDepartments) {
        nodes[dept.head].x = dept.x;
        nodes[dept.head].y = dept.y;
        let ordinal = 0;
        for (let i = begin; i < nodes.length; i++) {
          const n = nodes[i];
          if (n.dept !== dept.id || i === dept.head) continue;
          ordinal++;
          const angle = ordinal * 2.399963229728653;
          const radius = 12 + Math.sqrt(ordinal) * 5.1;
          n.x = dept.x + Math.cos(angle) * radius;
          n.y = dept.y + Math.sin(angle) * radius;
        }
      }
      componentX += compWidth + 260;
    }
    if (nodes.length !== preset.nodes) throw Error("合成節點數不符合預設。");
    const adjacency = nodes.map(() => []);
    const outgoing = nodes.map(() => []);
    const incoming = nodes.map(() => []);
    for (const e of edges) {
      adjacency[e.source].push(e.target);
      adjacency[e.target].push(e.source);
      outgoing[e.source].push(e.target);
      incoming[e.target].push(e.source);
    }
    return {key, label:preset.label, nodes, edges, departments,
      adjacency, outgoing, incoming, components:preset.components,
      maxDepth, weightTotal,
      bounds: {x:0,y:0,width:componentX - 260,height:
        Math.max(...departments.map(d => d.y), 160) + 145}};
  }

  function weakComponentSizes(graph) {
    const seen = new Uint8Array(graph.nodes.length), sizes = [];
    for (let i = 0; i < seen.length; i++) {
      if (seen[i]) continue;
      let count = 0;
      const queue = [i]; seen[i] = 1;
      for (let j = 0; j < queue.length; j++) {
        count++;
        for (const neighbor of graph.adjacency[queue[j]]) {
          if (!seen[neighbor]) {seen[neighbor] = 1;queue.push(neighbor);}
        }
      }
      sizes.push(count);
    }
    return sizes.sort((a,b) => b-a);
  }

  function selectLocal(graph, nodeIndex, hops, direction, maxVisible = 2000) {
    if (!Number.isInteger(nodeIndex) || nodeIndex < 0 ||
        nodeIndex >= graph.nodes.length || ![1,2,3].includes(hops) ||
        !["both","in","out"].includes(direction)) throw Error("無效的局部分析設定。");
    const seen = new Set([nodeIndex]);
    let frontier = [nodeIndex], limited = false;
    const neighbors = direction === "both" ? graph.adjacency :
      (direction === "in" ? graph.incoming : graph.outgoing);
    for (let step = 0; step < hops && frontier.length; step++) {
      const next = [];
      for (const index of frontier) {
        for (const target of neighbors[index]) {
          if (seen.has(target)) continue;
          if (seen.size >= maxVisible) {limited = true; continue;}
          seen.add(target); next.push(target);
        }
      }
      frontier = next;
    }
    return {indices: seen, limited};
  }
  return {PRESETS, MAX_NODES, MAX_EDGES, buildScenario, weakComponentSizes, selectLocal};
});
