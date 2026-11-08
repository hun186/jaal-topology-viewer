# Jaal Topology Viewer

A self-contained Python package for visualizing **directed node relationships**:
one or more relationship CSV files, plus optional node display metadata CSV.
This package has no import from `BertScript`, `ClassesTree`, `TCFMain`, model
training, or WorkPool. It **never writes** either source CSV.

## Public Vercel PoC — real Jaal Viewer

The [public demonstration](vercel-poc/README.md) now mounts the **real
Python Jaal/Dash app**, using the same core, layout controls, Search/
Filter/Color/Size and Louvain/community logic as this portable viewer.
The default case now simulates fictional business-email workflows from
individual events; the former 77-node/169-edge taxonomy-derived network is
still available for comparison. Cyclic graphs correctly disable the two
DAG-only collapse modes.

The common Jaal/Dash viewer has a **collapsible Search/Filter/Color/Size
sidebar**; collapsing it releases the full graph width without unmounting
its controls. The graph-type/cycle explanation is available from the
**圖形說明** disclosure in the compact top toolbar instead of permanently
occupying drawing height. The graph-type badge remains visible so cycle
restrictions are not silently hidden. The Jaal logo is compact.

The toolbar now **scrolls with the page** instead of staying fixed.
Graph height adapts to the viewport rather than the old fixed 600px.
Use **全版檢視 ⛶** to temporarily show only the actual Jaal/visdcc
graph across the available window; **退出全版 ✕** or **Escape** restores
the settings and graph controls without remounting the graph. The
focus layout fills the current browser viewport (or the hosting iframe's
viewport); it does not invoke the operating system fullscreen API.

The root `app.py` remains the Vercel Flask entrypoint. Its optional browser-local
workspace does not upload or persist private files on the server. This does not change
the localhost CLI or the downstream `text-category-profiler` pin.

Vercel Git push/PR auto deployments remain disabled. The dedicated
workflow can release **only a relevant merged PR** when its separate
GitHub credentials and enable switch are explicitly configured.
There are no PR preview deployments.

## My Cases — browser-only graph workspace

The existing gallery toolbar now links to **＋ 我的案例／上傳 CSV**
at **/my-cases/** (same origin). This is a separately scoped **browser-local
workspace**, not a server upload endpoint.

- **Create:** choose a name and 1–5 UTF-8 CSV/TSV relationship files, with
  parent,child / from,to / source,target / sender,recipient headers, or
  headerless first-two-column directed pairs. Optional ClassLabel,CT
  provides Chinese display labels. The optional count/weight column accepts
  positive integers, and exact duplicate pairs are deduplicated.
- **Explore:** preview a real native SVG directed graph, select network or
  hierarchy layout, click nodes, search original IDs/Chinese labels, inspect
  edge directions, choose out/in/both and 0–10/all reachable k-hop scope,
  pan/zoom/reset the viewport. A directed cycle is identified explicitly.
- **Manage:** save up to 20 cases in same-origin IndexedDB, reopen after
  refresh, rename, delete, export an individual/all JSON backup and restore
  a backup. Case limits: 250 nodes, 2,000 unique directed edges, five
  relationship files per case and 2 MB per input. No source CSV is edited.

**Privacy:** scripts and HTML are GET-only static assets with restrictive CSP
(connect-src 'none'). File reading, graph parsing/rendering and persistence
remain inside the browser; no POST, private server data store, remote API,
account sync or filesystem path recording. A browser cannot silently reopen
a file solely from a saved local path. Site-data clearing, incognito mode,
origin changes or browser eviction may erase local cases. JSON backups
contain **plaintext customer relationships** and must be protected by the
customer; private data should not be stored in a shared browser profile.

**Feature boundary:** the local workspace is not the original Jaal/Dash
canvas. The existing five display modes, Louvain collapses and temporal
animation work unchanged for preloaded gallery cases; they do **not yet**
apply to uploaded local cases. This boundary is deliberate: passing user
files to the Python server or swapping the source under stateful Jaal
callbacks would violate the private local-first workflow and per-case
callback isolation. A future opt-in adapter requires separate review.

## Multi-case Jaal gallery

The gallery is an optional part of the **portable Jaal component**, not a
separate SVG mockup. The public demo, as served by `app.py`, offers a searchable
**示範案例** dropdown containing:

- **企業郵件實務模擬（業務與事件）** — the new default at `/`:
  seeded, workflow-driven *fictional* individual emails with replies,
  projects, cross-team escalations, system incidents and month-close effects.
  Directed lines reveal synthetic send frequency; Louvain uses weighted
  volumes. Review the [full model and downloads](examples/REALISTIC_EMAIL_DEMO.md).
- **舊版通訊拓樸（類別樹改編）** — 77 nodes and 169 directed pairs,
  retained at `/cases/mail-network/` for historical algorithm comparison
  (**not** a realistic email event model)
- **公司組織階層樹（無環）** — synthetic 52-node, 51-edge hierarchy,
  initially in hierarchy-collapsed mode, at `/cases/org-tree/`
- **專案相依網路（多父 DAG）** — synthetic 19-node, 31-edge
  directed acyclic graph with shared successors, initially in hierarchy
  mode, at `/cases/project-dag/`

Changing cases navigates **on the same local/hosted domain and port**.
Each page is a separately mounted original Dash/Jaal app with its own
Search/Filter/Color/Size callbacks, cycle safety rules, Louvain partition
and mode selection. Reloading the page when switching prevents stale
graph callbacks/data from leaking across cases. There is no **server-side** CSV upload or
filesystem explorer in the public demo. The default `build_app(graph)`
and existing `mount_flask(...)` consumers remain unchanged.

Other Python projects can construct their own **allowlisted** gallery:

```python
from jaal_topology import GalleryCase, create_gallery_app, load_graph, select_subgraph

cases = [
    GalleryCase("emails", "寄收件網路",
                select_subgraph(load_graph("email_edges.csv", "people.csv"))),
    GalleryCase("taxonomy", "分類階層樹",
                select_subgraph(load_graph("tree_edges.csv", "names.csv")),
                initial_mode="hierarchical-collapsed"),
]
dash_app = create_gallery_app(cases)
app = dash_app.server       # WSGI Flask host, one listener
app.run(host="127.0.0.1", port=8099, debug=False)
```

Only the gallery uses a case selector. The `create_gallery_app` API takes
1–20 preloaded `GalleryCase` entries with unique safe ASCII slugs.
The first case stays at `/`, and subsequent cases are mounted at
`/cases/<key>/`. If two datasets should share a case, callers must
explicitly load/compose them first. Input and graph limits are still
enforced by `load_graph`, `select_subgraph` and `build_app`.

For the built-in public examples (when running from the repository),
use the same existing Vercel-equivalent command:

```bat
.venv-vercel\Scripts\python.exe -c "from app import app; app.run(host='127.0.0.1', port=8099, debug=False)"
```

The case dropdown changes only local/server-loaded examples; **it does
not trigger a new Vercel deployment**. The production Vercel URL remains
on its previously deployed version until an authorized, quota-available
post-Merge release is separately verified.

## Interactive root-neighborhood focus (all graph cases)

The compact toolbar includes **局部子圖／根節點**. Its searchable dropdown
accepts literal English node IDs and Chinese aliases (ClassTable metadata);
clearing the selection restores the entire loaded graph. Choose a shortest
path radius **0–5 steps, 10 steps or 全部可達**, and a traversal direction:

- **向外 →** follows directed edges from the selected root. For category
  DAGs this is the root's descendants; in email graphs it is outgoing mail.
- **向內 ←** follows incoming edges; for DAGs it finds ancestors.
- **雙向 ↔** treats links as undirected *only for reachability*. Displayed
  edges still retain their real original direction and weights.

The selected display is an **induced subgraph**: every original directed
edge whose endpoints both lie within the k-hop neighborhood is retained,
even if that particular edge was not on the shortest path. Cycles and
shared descendants are counted once. Single isolated roots (0 edges) are
valid views. Search, legends, and original source CSV are not rewritten.
All modes use the same selected original IDs, while the animated email
graph still applies its actual per-window activity on top of that stable
selection. Clearing the root restores the full bounded source without
changing URL, rebuilding Jaal, or calling Vercel per animation frame.

For huge raw datasets, the original 3000-node/5000-edge **load cap still
applies**: first select a bounded graph at the Python/CLI layer; the
interactive focus reduces an already loaded bounded graph. It is not
a server-side bypass of graph size limits.

## Temporal Network Analysis — optional event-backed animation

The fictional business-email case has an opt-in **時間演化**
controller for the **same real Jaal/visdcc graph**. Other CSV-based
taxonomy, DAG and historical cases retain their original non-temporal
behavior.

- Drag **either endpoint** of the analysis-range slider, or enter precise
  ISO date/time start and exclusive end in the adjacent text boxes (e.g.
  `2026-10-05T09:00`). The separate blue bar depicts the **currently playing**
  window and moves at both ends while animating. The fixed analysis-range
  slider is no longer mistaken for the active window.
- Choose units **day, three hours, hour, ten minutes or one minute**,
  and choose window width in units. The default is a **three-day,
  non-overlapping partition**; window length = advancement stride.
  The optional overlapping mode exposes a separate stride, requiring
  `stride <= window`; cumulative mode remains available.
- **All precise intervals are left-closed/right-open `[start,end)`**. An
  event exactly on the next window boundary belongs only to the next
  non-overlapping window, never both. Existing Python `snapshot()` /
  `frames()` day-level callers remain intact.
- At most **240 frames** are precomputed. If minute precision over a long
  period exceeds this budget, an explicit error asks the user to shorten
  the analysis range or increase the step; it never quietly downgrades
  timestamps to days or pretends stale frames are current.
- **基礎邊長／間距** (60–300 px) adjusts the network's spring length
  for ordinary graphs and the frozen visual spacing of the temporal
  community viewer. It never changes stored edge weights or source data.
  Expanding a community places its members near the last box position;
  collapsing restores that same anchor, with the current camera preserved.
- **固定社群（比較流量）** is the default: the full-period weighted Louvain
  partition stays anchored while real per-window traffic, active groups
  and pair weights change. Opened groups remain opened, and group/link IDs
  remain stable between frames. **逐格重分群（實驗）** is still available,
  but changes community identity and resets expanded groups on purpose.
- Dense **網狀（全展開）** defaults to labels for the 12 highest-volume
  active participants. All identities, arrows and hover titles remain;
  check **顯示全部節點名稱** to restore every label.
- Scrub manually, advance by precomputed time frames, Play/Pause, loop, and choose
  playback speed 350/700/1400/2500 milliseconds per step.
- Each frame recomputes actual directed-pair message counts, active nodes
  and edges, plus an optional **time-slice Louvain partition**. The default
  baseline grouping is fixed for visual comparison; selecting dynamic
  grouping explicitly switches to the per-frame partition.
- The Python server precomputes a bounded batch after a date/mode/window
  change. Subsequent playback is entirely **in the browser**, without
  a Flask/Vercel HTTP request for each animation tick.

Custom applications can opt in without modifying their old
`Graph(edges,nodes,translations)` or CLI use:

```python
from jaal_topology import GalleryCase, TemporalTimeline, create_gallery_app

# full_graph: original deduplicated Graph, with optional edge_counts
# events: sequence of objects exposing ISO .timestamp, .sender, .recipient
timeline = TemporalTimeline(full_graph, events)
dash_app = create_gallery_app([
    GalleryCase("events", "事件演化", full_graph,
                temporal_timeline=timeline),
])
```

`temporal_timeline=timeline` can be attached to **any** `GalleryCase`, not
just the first case at `/`. Each case owns its own mounted Dash callback
state: ordinary taxonomy/DAG cases do not display temporal controls, while
a selected event-backed case does. The timeline's source `Graph` must match
the case's `Graph`; mismatched cases fail closed at app construction.

The temporal API accepts up to 50,000 events spanning 120 calendar days
and limits rendering to 3,000 nodes/5,000 directed edges (plus a bounded
frame batch). Timestamp strings without offsets are explicitly considered
unspecified local time; timezone-aware timestamps are normalized to UTC,
and mixing conventions is rejected. Time-sliced Filter/Size *server
callback schemas*, live email ingestion, timezone selector and side-by-side
comparisons are not yet included; original Jaal controls still use their
full-period data source while the displayed graph/counts/Louvain evolve.

## Install and use in another Python project

This repository **is the standalone package root**. With Python 3.10+
and an environment compatible with `jaal`/`dash`/`visdcc`, install a
fixed reviewed Git commit rather than a floating `main` dependency:

```sh
python -m pip install "jaal-topology-viewer @ git+https://github.com/hun186/jaal-topology-viewer.git@7a7d8ba1f847b2f95a620c61a0c5a94f0523e255"
jaal-topology --edges ./relationships.csv --metadata ./labels.csv --root Root
```

When contributing to this repository, clone it and use an editable install:

```sh
git clone https://github.com/hun186/jaal-topology-viewer.git
cd jaal-topology-viewer
python -m pip install -e .
```

Alternatively, without modifying global PATH:

```sh
python -m jaal_topology --edges ./relationships.csv --root Root -p 8059
```

The package bundles MIT-licensed Bootstrap 5.3.1 stylesheet and Jaal
browser assets for offline styling; no second backend is needed.
The server listens **only** on `127.0.0.1` (no public bind); visit
`http://127.0.0.1:8059/`. Run `jaal-topology --help` for options.

### Relationships (required)

```csv
parent,child
Root,Branch A
Root,Branch B
Branch A,Leaf
Branch B,Leaf
```

Or omit the header and use the first two fields as `from,to`.
Alternative headers: `from,to`, `source,target`, `母類別,子類別`.
Additional columns are ignored. BOM UTF-8, CSV quoting and multiple
`--edges` inputs are supported; IDs are literal strings, deduplicated edges
retain direction. Multiple parents, cross-links, cycles and disconnected
components are permitted. No conversion into a strict tree is attempted.

### Optional metadata

```csv
ClassLabel,CT,Explanation,Notes
Root,根類別,,
Branch A,分支甲,,
```

Only `ClassLabel` (identity) and `CT` (display name) are required. Missing
rows or blank `CT` fall back to English/original IDs. For custom schemas:

```sh
jaal-topology --edges links.csv --metadata names.csv \
  --metadata-id-column node_id --metadata-label-column display_name
```

The web UI provides a live, **off-by-default** Chinese label checkbox;
English IDs remain authoritative in Search and node tooltips. It also retains
the original Jaal Search/Filter/Color/Size controls plus **four legacy**
layout modes (network/hierarchy, fully shown/structurally collapsed),
and an independent experimental **網狀（社群收攏・Louvain）** mode,
click-to-expand/collapse and the existing smooth hierarchy expansion animation.
Changing display labels never rewrites graph data.

### Size / safety

A selected view defaults to **250 nodes and 5,000 edges**, bounded to
3,000 / 5,000 respectively.
A root that is a leaf with **zero visible edges** is rejected with a helpful
message instead of creating dummy relations: upstream Jaal's Filter UI needs
at least one actual edge to initialize. Select a parent/ancestor as the root. A full graph larger than the node cap is rejected
with instructions to choose `--root`; there is no automatic full-graph
render on import. Source parsing itself rejects more than 100,000 distinct
edges. CSVs remain read-only. The renderer imports heavy dependencies only
on `build_app()`, not `import jaal_topology`.

## Full-feature original Jaal large-email scale gallery (localhost opt-in)

The new **start-gallery.bat** launches the *original* Jaal/Dash Gallery on
`127.0.0.1:8059` with six additional, fixed, **fictional** company-email
scenarios in the SAME searchable case dropdown: 500, 3,000, 5,000, 20,000
employees, an extra 3,000-node **acyclic DAG** expressly to exercise
both structural-collapse modes, and three **actually disconnected weak components**
(167 + 167 + 166 employees). No links exist between the three groups.
All nodes and directed sender→recipient edges are truly loaded, with
deterministic Chinese role names, 5–7 managerial levels, department chatter,
reports/replies and dated fictitious mail events. The actual full-size cases
use original **Jaal/visdcc Search/Filter/Color/Size, Louvain community
expansion, directed root/k-hop filtering and temporal playback**.
Cyclic email-with-replies graphs correctly disable two unsafe structural
collapse modes; the dedicated 3,000-node acyclic DAG verifies that **all five**
layout modes remain selectable when topologically valid. This is not a
Canvas imitation.

Run in Windows **CMD or Anaconda Prompt** (Python 3.11 recommended):

```bat
python -m pip install -r requirements.txt
python -m pip install -e .
start-gallery.bat
```

Or set `JAAL_ENABLE_LARGE_LOCAL=1` before executing
`python -m flask --app app:app run --host 127.0.0.1 --port 8059 --no-reload`.
Large cases are **opt-in, locally served, lazily constructed on first
selection**, to keep the original 77-person Gallery responsive at startup.
This flag must not be enabled in a public deployment; the default public
`app.py` remains four preloaded small cases. All files are read-only;
no actual mail data is accessed.

**Performance / scope honesty:** the normal import and default Jaal
limits (3,000 nodes / 5,000 edges) are preserved. Only the trusted
fixed synthetic scenarios can opt into the 20,000-node / 50,000-edge
graph bound. Opening a 20k Jaal graph can consume significant CPU/RAM,
including Louvain and time slices; physics is disabled for these opt-in
cases, but this does **not** guarantee that client-side full expansion,
hierarchical layout or all controls will perform well on every computer.
First test 500 and 3,000 then increase. The three independent groups are
initially given separated positions to improve readability; the real edge
set, not colors or viewport placement, proves their disconnection.

### Historical separate Canvas laboratory

`/stress-lab/` remains accessible only as an older compatibility
demonstration, but is intentionally **not linked in the main Jaal toolbar**.
It does not replace full Jaal testing or represent support for its five modes.

## Synthetic corporate email stress laboratory (Canvas)

The sample-only Gallery includes a same-origin **/stress-lab/** link for four
fully generated fictional company sizes (500, 3,000, 5,000 and 20,000 employees)
plus a 500-person case consisting of **exactly three weakly connected
components**. Departments, reporting layers, directed manager replies,
local peer traffic and sparse cross-department approvals scale deterministically;
these graphs do not come from real corporate mail or a validated stochastic
model. The user may switch between leadership summary, *actual complete*
Canvas drawing and a direction-aware 1–3 hop local subgraph (local scope caps
at 2,000 nodes, visibly reported). It measures current-browser generation and
drawing durations with performance.now(), not a universal benchmark score.

**Compatibility:** The stress laboratory is an independent client-side Canvas
engine, *not* another Jaal mode. The original Jaal/Dash safety cap remains
3,000 nodes / 5,000 edges and its five layout modes, Louvain and temporal
playback do not apply to this stress demo. No 20k graph is silently truncated
and passed off as full: the summary and local limits are labeled explicitly.
All five stress scenarios are generated in the browser from fixed business
rules, with no server transfer, third-party dependency, uploads or persistent
private data. The Gallery still starts with the existing 77-node corporate
email workflow and retains its four built-in Jaal cases.

## Larger example: fictional corporate communications

This medium-size example is deliberately **not a strict tree**. It transforms the
directed `TW Affairs` taxonomy subtree from
[`text-category-profiler`](https://github.com/hun186/text-category-profiler)
into fictional organizational role IDs, then adds synthetic replies, lateral
messages and cross-team correspondence. **Every directed arrow is
sender → recipient**, never a reporting relationship.

The original selected subtree has **77 nodes and 82 edge records (81 unique directed pairs)**; the
example has **77 roles and 169 unique directed links**.
The `relation` column distinguishes invented message types for documentation;
the current viewer uses just the first two columns, and does not interpret
relation types as line styles or email counts. All names and communications
are synthetic, not actual company or email records.

```sh
# Linux / macOS, from the repository (after python -m pip install -e .):
bash run-company-demo.sh
# Windows cmd.exe:
# run-company-demo.bat
# Or launch directly, on any platform:
python -m jaal_topology --edges examples/company_communications.csv --metadata examples/company_people.csv -p 8059
```

Open `http://127.0.0.1:8059/` locally. Both scripts accept an optional
port and resolve data paths relative to the repository root. The detailed
[interactive demonstration guide](examples/COMPANY_DEMO.md) includes suggested
Search, Chinese labels and cross-team exploration steps.

Start with **網狀（全展開） / network** for this general directed graph.
Try **網狀（社群收攏・Louvain）** for experimental topology-based
communities (seed 42, resolution 1; unweighted distinct directed pairs).
Click a community to open it; click one of its members to collapse it.
The viewer labels the selected directed graph as **tree** (one root and no
shared children), **forest** (multiple disconnected rooted trees), **DAG**
(acyclic shared descendants/multiple parents), or **cyclic network** (at least
one directed cycle, including self-loops or cycles in disconnected components).
Classification is structural only: an email arrow never becomes an org chart.
The classification and descendant-mode safety gate use the same selected
graph without changing nodes, edges, or their identifiers.

The four legacy mode codes stay supported: **網狀（收攏）** still uses taxonomy
descendants, *not* communities. For **directed cyclic graphs**, the two
structural-descendant collapsed radio choices are **disabled with an explanation**,
because cyclic reachability makes many nodes appear to have nearly all others
as descendants. Full network/hierarchy and Louvain remain available. For
acyclic DAGs with multiple parents, structural collapse remains available
with a warning that reachable descendants are not exclusive subordinates. The quotient can have a **new directed cycle even when the input is a
directed acyclic taxonomy DAG**. The UI reports the quotient-cycle status
separately from the original graph; it is never presented as a cycle in the
source taxonomy. Selecting a community link will expose the underlying
unmodified directed source relations (no invented reverse edge).

The community partition is an analytical
grouping, **not** an organization chart. The renderer preserves independent
directional totals; edge count labels are unique source pairs, not emails.
Search/Filter temporarily restores uncollapsed source visualization while
active. The Hosted Windows Chromium headless browser smoke verifies a real
same-port iframe, canvas, mode selectors, language toggle and Search, and
uploads screenshots as evidence. Drag/camera/Color/Size and the Windows
Stage 4 consumer remain separately unverified.

The auditable one-to-one taxonomy→fictional-role mapping is in
[`examples/company_communications_source_mapping.csv`](examples/company_communications_source_mapping.csv).
See [general graph community-collapse design](docs/general_graph_community_collapse.md)
for the implemented experimental directed Louvain mode, alternative Leiden
research proposals, directed aggregation, restore rules and testing gate.
**Leiden remains a proposal; the separate Louvain mode is implemented.**

## Known difference from the Stage 4 customized Jaal viewer

This standalone package now bundles the complete four-mode visdcc browser
engine used by Stage 4, including structural collapse, smooth 460 ms hierarchy
reflow, and reduced-motion behavior. Its own runtime and CLI require no
TextClassification project files. The project-specific same-port iframe mount,
root-search dropdown, Jaal auto-height and advanced panel/sidebar styling still
belong to Stage 4; they are **not yet shared host adapters**. The original
Stage 4 now serves the two browser-runtime scripts from this portable package
as its single source, while preserving the original same-port Jaal UI. Windows
browser visual acceptance and cross-project version compatibility remain open.

Do not delete or redirect the existing Stage 4 Jaal integration based on this
first package. Windows browser visual acceptance, packaging on a clean
external project, version compatibility across Dash 2/3/4, publishing
permissions/licensing, and public deployment security are separate gates.

## Embed on the same port as an existing Flask / Dash app

The pure-Python WSGI adapter does not create a second listening socket:

```python
from flask import Flask
from jaal_topology import load_graph, select_subgraph
from jaal_topology.integration import mount_flask

app = Flask(__name__)
graph = select_subgraph(load_graph("relationships.csv", "metadata.csv"),
                        "Root")
viewer = mount_flask(app, graph, mount_path="/topology", root="Root")
# Embed <iframe src="/topology/"></iframe> inside the host page if desired.
app.run(host="127.0.0.1", port=8059)
```

Call `mount_flask` before the host starts serving requests. All Dash
callback, stylesheet and browser-runtime URLs are prefixed `/topology/`.
The host root, other routes and controls remain intact. No automatic graph
reload: rebuild the selected view by restarting or constructing another
bounded app. This is a same-origin embedded app, not a live cross-origin
embedding or a public Internet deployment service.

## Independent repository testing and integration

This repository includes its own `pyproject.toml`, `LICENSE`,
`THIRD_PARTY_NOTICES.md`, `examples/`, `tests/`, and
`.github/workflows/ci.yml`. It has no import dependency on
`hun186/text-category-profiler`. See [REPOSITORY_SETUP.md](REPOSITORY_SETUP.md)
for authoritative ownership, downstream consumer updates and compatibility
checks:

```sh
python -m pip install -e .
python -m unittest discover -s tests -p "test_*.py" -v
node --test tests/*.test.cjs
jaal-topology --edges examples/relationships.csv --metadata examples/metadata.csv --root Root
```

The local workflow verifies this clean-root package configuration.
`text-category-profiler` now installs this package from an exact Git commit
and verifies its own Stage 4 WSGI and browser compatibility. Do not
publish a new release until independent PR review, hosted CI and appropriate
browser acceptance pass; publishing to PyPI, Docker or a public web server are
separate security/release decisions.
