const test = require("node:test");
const assert = require("node:assert/strict");
const {spawnSync} = require("node:child_process");
const {readFileSync} = require("node:fs");
const {resolve} = require("node:path");


const root = resolve(__dirname, "..");
test("CSV parser preserves quoted delimiters and rejects broken fields", async () => {
  const {parseCsv} = await import("../vercel-poc/build.mjs");
  assert.deepEqual(parseCsv('from,to\r\n"A,B","C""D"\r\n'), [
    ["from", "to"], ["A,B", 'C"D']
  ]);
  assert.throws(() => parseCsv('"unterminated'), /Unterminated/);
});
test("builds fictional directed graph and original IDs", () => {
  const result = spawnSync(process.execPath, ["vercel-poc/build.mjs"], {
    cwd: root, encoding: "utf8"
  });
  assert.equal(result.status, 0, result.stderr);
  const graph = JSON.parse(readFileSync(resolve(root, "vercel-poc/dist/graph.json")));
  assert.equal(graph.kind, "fictional-corporate-communications");
  assert.equal(graph.nodes.length, 77);
  assert.equal(graph.edges.length, 169);
  assert.equal(new Set(graph.edges.map(e => JSON.stringify([e.from, e.to]))).size, 169);
  assert.equal(new Set(graph.nodes.map(n => n.id)).size, 77);
  assert.equal(graph.nodes.find(n => n.id === "CEO / Executive Office").label, "執行長／總經理室");
  const ids = new Set(graph.nodes.map(n => n.id));
  assert.ok(graph.edges.every(e => ids.has(e.from) && ids.has(e.to)));
});
test("Vercel Git integration cannot automatically deploy any branch", () => {
  const cfg = JSON.parse(readFileSync(resolve(root, "vercel.json")));
  assert.equal(cfg.git.deploymentEnabled, false);
  assert.equal(cfg.framework, "flask");
  assert.equal(cfg.buildCommand, undefined);
  assert.equal(cfg.outputDirectory, undefined);
  const app = readFileSync(resolve(root, "app.py"), "utf8");
  assert.match(app, /create_gallery_app\(_CASES\)/);
  assert.match(app, /GalleryCase\(\s*"mail-workflow"/);
  assert.match(app, /GalleryCase\(\s*"mail-network"/);
  assert.match(app, /GalleryCase\(\s*"org-tree"/);
  assert.match(app, /GalleryCase\(\s*"project-dag"/);
  assert.match(app, /app = dash_app\.server/);
  // Dash injects its own script bootstrap; a static-only script CSP is invalid.
  assert.ok(cfg.headers[0].headers.some(x => x.key === "X-Content-Type-Options" && x.value === "nosniff"));
});
test("deployment only on merged and relevant PRs", () => {
  const yaml = readFileSync(resolve(root, ".github/workflows/vercel-poc-merge-only.yml"), "utf8");
  assert.match(yaml, /^\s+pull_request_target:\s*$/m);
  assert.match(yaml, /types: \[closed\]/);
  assert.match(yaml, /github\.event\.pull_request\.merged == true/);
  assert.match(yaml, /github\.event\.pull_request\.base\.ref == 'main'/);
  assert.match(yaml, /vars\.JAAL_VERCEL_POC_ENABLED == 'true'/);
  assert.match(yaml, /mergeCommitSha/);
  assert.match(yaml, /git merge-base --is-ancestor/);
  assert.doesNotMatch(yaml, /^\s+push:\s*$/m);
  assert.doesNotMatch(yaml, /^\s+workflow_dispatch:\s*$/m);
});
