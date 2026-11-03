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

The root `app.py` is a Vercel Flask WSGI entrypoint for the demo only.
No private data or user file upload is exposed. This does not change
the localhost CLI or the downstream `text-category-profiler` pin.

Vercel Git push/PR auto deployments remain disabled. The dedicated
workflow can release **only a relevant merged PR** when its separate
GitHub credentials and enable switch are explicitly configured.
There are no PR preview deployments.

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
graph callbacks/data from leaking across cases. There is no CSV upload or
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
