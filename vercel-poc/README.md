# Public Vercel PoC — genuine Jaal/Dash runtime

The public endpoint now runs the **same** `jaal_topology.viewer.build_app()`
used by the standalone Python CLI, exposed as Flask WSGI from the root
`app.py`. It is not the earlier independent SVG reproduction.

## Demonstrated behavior

- Real Jaal/visdcc Search, Filter, Color, Size and interactive graph physics
- All five portable layout choices: network, DAG-only structural collapse,
  Louvain community collapse, hierarchy, DAG-only hierarchical collapse
- Real graph-type/cycle guidance, optional CT translations and original IDs
- Same original fictional corporate communication fixture: 77 nodes,
  169 unique directed edges. Because this graph has cycles, the two
  structural collapse controls are disabled **exactly as on localhost**.
  Louvain mode stays available.

The real Jaal UI now uses a compact, wrapping top toolbar and
a toggleable original Search/Filter/Color/Size settings panel. Hidden
settings retain their values, and the graph column expands to the
available width. The long cycle/quotient explanations appear only when
opening **圖形說明** (the graph's cyclic status remains visible).

The user-facing **全版檢視 ⛶** button creates a temporary viewport-sized
topology view, hides Jaal's toolbar/settings/logo, and keeps the **退出全版 ✕**
button available; **Escape** also restores the previous layout. In ordinary
mode, the toolbar is no longer sticky when scrolling, and graph height uses
its enclosing viewport-based column (not a hardcoded 600px). This is a
layout-only switch on the same visdcc.Network, not a second graph renderer.
Inside an iframe, it fills the iframe viewport rather than escaping to
the hosting page or invoking the browser Fullscreen API.

The old static SVG prototype remains in `vercel-poc/` as an explicitly
**unpublished historical comparison**; it is *not* the deployed viewer.
The public runtime does not support arbitrary file uploads, secrets,
private datasets, databases or model training.

## Run a deployment-equivalent local instance

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -p 'test_vercel_runtime.py' -v
python -c "from app import app; app.run(host='127.0.0.1', port=8099)"
```

The rendered app is then available at `http://127.0.0.1:8099/`.
`/healthz` exposes only the fixture mode/count identity. The existing
portable CLI remains independent and does not import `app.py`.

CI verifies this entry at Python 3.12, original Dash assets and callbacks,
plus a Windows Chromium browser that uses the actual Vercel WSGI entry.
Live Vercel function cold starts, bundle contents, and routing require
an **additional post-Merge production HTTP check**, not merely CI PASS.

## Strict deployment quota policy

`vercel.json` **still** disables Git deployment for every branch.
There is no pull-request preview deployment. The optional
`.github/workflows/vercel-poc-merge-only.yml` only runs for a
`pull_request_target.closed` event when the PR was successfully merged
into `main` and touched relevant runtime/PoC files. It checks that the
merge commit is an ancestor of `main`, serializes deployments and
queries Vercel for the same commit before deploying; API errors fail
closed. It cannot deploy on Push, review, CI rerun, or manual dispatch.

The initial bootstrap was explicitly done **after** merging; future
automated releases are OFF until GitHub is explicitly configured:

- Repository variables: `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`,
  `VERCEL_CLI_VERSION` (a reviewed exact x.y.z version).
- GitHub Environment `vercel-poc` restricted to `main`, holding only
  the `VERCEL_TOKEN` secret.
- Only after all values have been verified, set the repository variable
  `JAAL_VERCEL_POC_ENABLED=true`.

The same public Vercel Hobby project runs a **serverless function** now,
so requests consume execution resources instead of pure static serving.
Never claim it is a full, unlimited or identical production-grade
Stage 4 deployment. The optional public demo retains no private state,
and its runtime and limits must be rechecked after any release.
