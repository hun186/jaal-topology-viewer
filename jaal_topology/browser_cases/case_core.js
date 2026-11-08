/* Local-only case data contract. No network APIs, eval, DOM HTML or server state. */
(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.JaalLocalCases = api;
})(typeof window !== "undefined" ? window : globalThis, function () {
  "use strict";
  const MAX_FILE_CHARS = 2 * 1024 * 1024;
  const MAX_NODES = 250, MAX_EDGES = 2000, MAX_CASES = 20;
  const SOURCE = new Set(["parent", "from", "source", "sender",
    "母類別", "父類別", "寄件人", "寄件者", "來源", "起點", "起始節點"]);
  const TARGET = new Set(["child", "to", "target", "recipient",
    "子類別", "收件人", "收件者", "目標", "終點", "目標節點"]);
  const LABEL_ID = new Set(["classlabel", "id", "node", "nodeid", "節點", "節點id", "英文名稱"]);
  const LABEL_NAME = new Set(["ct", "label", "name", "chinese", "中文名稱", "中文翻譯", "顯示名稱", "別名"]);
  const WEIGHT = new Set(["count", "weight", "volume", "messages", "封數", "件數", "次數", "權重"]);

  function norm(value) {
    return String(value).trim().replace(/[\s_#-]/g, "").toLowerCase();
  }
  function clean(value, what, max) {
    if (typeof value !== "string") throw Error(what + "必須是文字。");
    const s = value.trim();
    if (!s || s.length > max || /[\u0000-\u0008\u000b\u000e-\u001f\u007f]/.test(s)) {
      throw Error(what + "不能空白、含控制字元或超過 " + max + " 字。");
    }
    return s;
  }

  // RFC 4180 quoted cells, escaped quotes, CRLF and embedded line breaks.
  // A tab-separated file is accepted too; no third-party parser is loaded.
  function parseDelimited(source) {
    if (typeof source !== "string" || !source.trim()) throw Error("CSV 檔案是空的。");
    if (source.length > MAX_FILE_CHARS) throw Error("單一檔案不可超過 2 MB。");
    const input = source.charCodeAt(0) === 0xfeff ? source.slice(1) : source;
    // Detect separators outside quoted cells even for headerless TSV.
    let outsideQuotes = true, commas = 0, tabs = 0;
    for (let i = 0; i < input.length; i++) {
      const ch = input[i];
      if (ch === '"') {
        if (!outsideQuotes && input[i + 1] === '"') {i++; continue;}
        outsideQuotes = !outsideQuotes;
      } else if (outsideQuotes && (ch === "\n" || ch === "\r")) break;
      else if (outsideQuotes && ch === ",") commas++;
      else if (outsideQuotes && ch === "\t") tabs++;
    }
    const delimiter = tabs > commas ? "\t" : ",";
    const rows = [];
    let row = [], cell = "", quoted = false, afterQuote = false, atStart = true;
    function flushCell() {
      row.push(cell.trim());
      cell = ""; afterQuote = false; atStart = true;
    }
    function flushRow() {
      flushCell();
      if (row.some(value => value !== "")) rows.push(row);
      row = [];
      if (rows.length > 100001) throw Error("CSV 超過單次解析上限，請先縮小資料範圍。");
    }
    for (let i = 0; i < input.length; i++) {
      const ch = input[i];
      if (quoted) {
        if (ch === '"') {
          if (input[i + 1] === '"') {cell += '"'; i++;}
          else {quoted = false; afterQuote = true;}
        } else {
          cell += ch;
        }
      } else if (ch === delimiter) {
        flushCell();
      } else if (ch === "\n" || ch === "\r") {
        if (ch === "\r" && input[i + 1] === "\n") i++;
        flushRow();
      } else if (ch === '"' && atStart) {
        quoted = true; atStart = false;
      } else if (ch === '"' || (afterQuote && ch !== " " && ch !== "\t")) {
        throw Error("CSV 引號格式有誤：請檢查雙引號及分隔符號。");
      } else if (afterQuote) {
        // Whitespace after a quoted value is allowed.
      } else {
        cell += ch;
        if (ch !== " " && ch !== "\t") atStart = false;
      }
    }
    if (quoted) throw Error("CSV 有未結束的雙引號。");
    if (row.length || cell.length || afterQuote) flushRow();
    if (!rows.length) throw Error("CSV 沒有有效資料列。");
    return rows;
  }

  function columns(row, first, second, allowHeaderless) {
    const names = row.map(norm);
    const a = names.findIndex(name => first.has(name));
    const b = names.findIndex(name => second.has(name));
    if (a >= 0 && b >= 0 && a !== b) {
      return {a, b, hasHeader: true};
    }
    if (!allowHeaderless || a >= 0 || b >= 0) {
      throw Error("找不到完整欄位名稱；請使用 parent,child 或 from,to。");
    }
    return {a: 0, b: 1, hasHeader: false};
  }

  function importGraph(title, edgeTexts, labelText) {
    const name = clean(title, "案例名稱", 100);
    if (!Array.isArray(edgeTexts) || !edgeTexts.length || edgeTexts.length > 5) {
      throw Error("請選擇 1 至 5 份關係 CSV。");
    }
    const edgesByKey = new Map();
    for (const text of edgeTexts) {
      const rows = parseDelimited(text);
      const cols = columns(rows[0], SOURCE, TARGET, true);
      const weightColumn = cols.hasHeader
        ? rows[0].map(norm).findIndex(x => WEIGHT.has(x)) : -1;
      for (const row of rows.slice(cols.hasHeader ? 1 : 0)) {
        if (row.length <= Math.max(cols.a, cols.b)) {
          throw Error("關係 CSV 有缺少起點或終點的資料列。");
        }
        const from = clean(row[cols.a], "起點 ID", 160);
        const to = clean(row[cols.b], "終點 ID", 160);
        let weight = 1;
        if (weightColumn >= 0) {
          const value = String(row[weightColumn] || "").trim();
          if (!/^[1-9][0-9]{0,6}$/.test(value) || Number(value) > 1000000) {
            throw Error("權重／件數欄位必須是 1 至 1,000,000 的正整數。");
          }
          weight = Number(value);
        }
        const key = JSON.stringify([from, to]);
        if (!edgesByKey.has(key)) edgesByKey.set(key, {from, to, weight: 0, unweighted: false});
        const prev = edgesByKey.get(key);
        // Explicit counts add; unweighted occurrences contribute once.
        // Both cases are independent of file ordering.
        if (weightColumn >= 0) prev.weight += weight;
        else if (!prev.unweighted) {prev.weight += 1; prev.unweighted = true;}
        if (prev.weight > 1000000) throw Error("同一有向關係累計權重超過上限。");
        if (edgesByKey.size > MAX_EDGES) {
          throw Error("超過 " + MAX_EDGES.toLocaleString("en-US") + " 條有向邊；請先篩選資料。");
        }
      }
    }
    if (!edgesByKey.size) throw Error("關係檔沒有有效的有向連線。");
    const ids = new Set();
    for (const edge of edgesByKey.values()) {ids.add(edge.from); ids.add(edge.to);}
    if (ids.size > MAX_NODES) {
      throw Error("超過 " + MAX_NODES + " 個節點；請先切出分析用子圖。");
    }
    const labels = new Map();
    if (typeof labelText === "string" && labelText.trim()) {
      const rows = parseDelimited(labelText);
      const cols = columns(rows[0], LABEL_ID, LABEL_NAME, true);
      for (const row of rows.slice(cols.hasHeader ? 1 : 0)) {
        if (row.length <= Math.max(cols.a, cols.b)) {
          throw Error("節點名稱 CSV 有缺少欄位的資料列。");
        }
        const id = clean(row[cols.a], "節點 ID", 160);
        const label = String(row[cols.b] || "").trim();
        if (label && !ids.has(id)) continue;
        if (label) {
          clean(label, "顯示名稱", 180);
          if (labels.has(id) && labels.get(id) !== label) {
            throw Error("同一節點有不同顯示名稱：" + id);
          }
          labels.set(id, label);
        }
      }
    }
    return {
      schemaVersion: 1, title: name,
      nodes: [...ids].map(id => ({id, label: labels.get(id) || id})),
      edges: [...edgesByKey.values()].map(({from, to, weight}) => ({from, to, weight})),
    };
  }

  function validateCase(value) {
    if (!value || typeof value !== "object" || value.schemaVersion !== 1 ||
        !Array.isArray(value.nodes) || !Array.isArray(value.edges)) {
      throw Error("案例備份格式錯誤或版本不支援。");
    }
    const title = clean(value.title, "案例名稱", 100);
    if (!value.nodes.length || value.nodes.length > MAX_NODES ||
        !value.edges.length || value.edges.length > MAX_EDGES) {
      throw Error("案例節點／連線數量不在允許範圍內。");
    }
    const names = new Set();
    const nodes = value.nodes.map(node => {
      if (!node || typeof node !== "object") throw Error("節點格式不正確。");
      const id = clean(node.id, "節點 ID", 160);
      if (names.has(id)) throw Error("重複節點：" + id);
      names.add(id);
      return {id, label: clean(node.label, "顯示名稱", 180)};
    });
    const pairKeys = new Set();
    const edges = value.edges.map(edge => {
      if (!edge || typeof edge !== "object") throw Error("連線格式不正確。");
      const from = clean(edge.from, "起點 ID", 160);
      const to = clean(edge.to, "終點 ID", 160);
      if (!names.has(from) || !names.has(to)) throw Error("有連線指向不存在的節點。");
      const key = JSON.stringify([from, to]);
      if (pairKeys.has(key)) throw Error("備份含重複有向連線。");
      pairKeys.add(key);
      if (!Number.isSafeInteger(edge.weight) || edge.weight < 1 ||
          edge.weight > 1000000) throw Error("連線權重不合法。");
      return {from, to, weight: edge.weight};
    });
    if (!edges.length) throw Error("案例至少需要一條連線。");
    return {schemaVersion: 1, title, nodes, edges};
  }

  function neighborhood(value, rootId, hops, direction) {
    const graph = validateCase(value);
    if (!rootId) return graph;
    const ids = new Set(graph.nodes.map(n => n.id));
    if (!ids.has(rootId)) throw Error("找不到選取的根節點。");
    if (!(hops === "all" || (Number.isInteger(hops) && hops >= 0 && hops <= 10))) {
      throw Error("局部分析步數必須在 0 至 10 或選擇全部可達。");
    }
    if (!["out", "in", "both"].includes(direction)) throw Error("無效的探索方向。");
    const seen = new Set([rootId]);
    let frontier = [rootId], step = 0;
    while (frontier.length && (hops === "all" || step < hops)) {
      const next = [];
      for (const edge of graph.edges) {
        for (const [a, b] of (
          direction === "out" ? [[edge.from, edge.to]] :
          direction === "in" ? [[edge.to, edge.from]] :
          [[edge.from, edge.to], [edge.to, edge.from]]
        )) {
          if (frontier.includes(a) && !seen.has(b)) {seen.add(b); next.push(b);}
        }
      }
      frontier = next; step++;
    }
    return {...graph,
      nodes: graph.nodes.filter(n => seen.has(n.id)),
      edges: graph.edges.filter(e => seen.has(e.from) && seen.has(e.to)),
    };
  }

  function topology(value) {
    const graph = validateCase(value);
    const indegree = new Map(graph.nodes.map(n => [n.id, 0]));
    const successors = new Map(graph.nodes.map(n => [n.id, []]));
    for (const edge of graph.edges) {
      indegree.set(edge.to, indegree.get(edge.to) + 1);
      successors.get(edge.from).push(edge.to);
    }
    const queue = graph.nodes.map(n => n.id).filter(id => indegree.get(id) === 0);
    let visited = 0;
    for (let i = 0; i < queue.length; i++) {
      const node = queue[i]; visited++;
      for (const next of successors.get(node)) {
        indegree.set(next, indegree.get(next) - 1);
        if (indegree.get(next) === 0) queue.push(next);
      }
    }
    return {hasCycle: visited !== graph.nodes.length,
      nodes: graph.nodes.length, edges: graph.edges.length};
  }

  return {parseDelimited, importGraph, validateCase, neighborhood, topology,
    MAX_NODES, MAX_EDGES, MAX_CASES, MAX_FILE_CHARS};
});
