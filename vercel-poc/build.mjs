// Build a deliberately static, read-only topology PoC from the maintained
// fictional example CSVs. No network calls, database, Python/Dash runtime,
// user-provided files or secrets are needed in the deployed application.
import { readFile, mkdir, writeFile, copyFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const dist = join(root, "vercel-poc", "dist");

export function parseCsv(text) {
  const rows = [];
  let row = [], field = "", quoted = false;
  const input = text.replace(/^\uFEFF/, "");
  for (let i = 0; i < input.length; i++) {
    const ch = input[i];
    if (quoted) {
      if (ch === '"') {
        if (input[i + 1] === '"') { field += '"'; i++; }
        else quoted = false;
      } else field += ch;
    } else if (ch === '"' && field === "") {
      quoted = true;
    } else if (ch === ",") {
      row.push(field); field = "";
    } else if (ch === "\n") {
      row.push(field);
      if (row.some(v => v.trim() !== "")) rows.push(row);
      row = []; field = "";
    } else if (ch !== "\r") {
      field += ch;
    }
  }
  if (quoted) throw new Error("Unterminated quoted CSV field");
  row.push(field);
  if (row.some(v => v.trim() !== "")) rows.push(row);
  return rows;
}

async function main() {
  const edgeText = await readFile(join(root, "examples", "company_communications.csv"), "utf8");
  const labelText = await readFile(join(root, "examples", "company_people.csv"), "utf8");
  const edgeRows = parseCsv(edgeText);
  const labelRows = parseCsv(labelText);
  if (edgeRows.shift().join(",") !== "from,to,relation") throw Error("Unexpected relation CSV schema");
  if (labelRows.shift().join(",") !== "ClassLabel,CT") throw Error("Unexpected labels CSV schema");
  const translations = new Map(labelRows.map(([id, name]) => [id, name]));
  const edges = [];
  const ids = new Set();
  const pairs = new Set();
  for (const row of edgeRows) {
    if (row.length !== 3 || !row[0] || !row[1]) throw Error("Malformed example relationship");
    const [from, to, relation] = row;
    const key = JSON.stringify([from, to]);
    if (pairs.has(key)) throw Error("Duplicate directed relationship: " + key);
    pairs.add(key); ids.add(from); ids.add(to);
    edges.push({ from, to, relation });
  }
  if (ids.size !== 77 || edges.length !== 169) {
    throw Error("Unexpected fictional example size; update the acceptance contract intentionally");
  }
  if ([...ids].some(id => !translations.has(id))) throw Error("Missing example CT translation");
  const nodes = [...ids].sort((a, b) => a.localeCompare(b, "en")).map(id => ({
    id,
    label: translations.get(id) || id,
    team: id.includes(" / ") ? id.split(" / ")[0] : "Executive",
  }));
  const data = {
    kind: "fictional-corporate-communications",
    description: "Fictional, topology-only directed relationships: distinct pairs, not email message counts",
    nodes, edges,
  };
  await mkdir(dist, { recursive: true });
  await writeFile(join(dist, "graph.json"), JSON.stringify(data));
  for (const asset of ["index.html", "app.js", "styles.css"]) {
    await copyFile(join(root, "vercel-poc", asset), join(dist, asset));
  }
  console.log("VERCEL_POC_STATIC_BUILD_PASS", nodes.length, edges.length, dist);
}
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  await main();
}
