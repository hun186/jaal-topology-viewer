# Maintaining the independent Jaal Topology Viewer repository

## Source of truth

The independent repository is
**[hun186/jaal-topology-viewer](https://github.com/hun186/jaal-topology-viewer)**.
It is the **only maintained core implementation** of the reusable
`jaal_topology` Python package and its Jaal browser assets. Do not copy
these sources back into the `text-category-profiler` tree.

The former `packages/jaal-topology/` directory, originally exported by the
source text classification repository, is retired after integration PRs
[#209](https://github.com/hun186/text-category-profiler/pull/209) and
[#210](https://github.com/hun186/text-category-profiler/pull/210).
The former artifact-export GitHub Action is also retired; it is not
the current release or publication channel.

The consumer app `text-category-profiler` retains project-owned
`TopicTree.csv` and `ClassTable.csv`, its original searchable root picker,
lazy bounded loading, same-port WSGI router, iframe autoheight, Jaal
Search/Filter/Color/Size, Chinese labels toggle and sidebar UI. Those are
**application-specific adapters**, not duplicated Jaal core libraries.

## Developer setup and CI

```sh
git clone https://github.com/hun186/jaal-topology-viewer.git
cd jaal-topology-viewer
python -m pip install -e .
python -m unittest discover -s tests -p "test_*.py" -v
node --test tests/*.test.cjs
jaal-topology --edges examples/relationships.csv \
  --metadata examples/metadata.csv --root Root
```

The built-in `Portable Jaal Viewer CI` workflow validates Python and
Node tests plus real Dash HTTP/JS/CSS assets. All changes should use a
reviewed PR, latest-head Hosted CI PASS and formal Codex Review with
zero unresolved findings before Merge.

## How a downstream Python project consumes a reviewed version

Example fixed Git commit already verified in the source integration:

```text
jaal-topology-viewer @ git+https://github.com/hun186/jaal-topology-viewer.git@7a7d8ba1f847b2f95a620c61a0c5a94f0523e255
```

Install with `python -m pip install -r requirements.txt` from the consumer
repository. This Git requirement is resolved during installation, **not at
runtime**. For an offline target environment, build and transfer a Wheel
from that exact source commit and record its version and hash. Never
silently fall back to `main` or download updates dynamically when the
viewer is launched.

Python usage:

```python
from jaal_topology import ASSETS_DIR, load_graph, select_subgraph
from jaal_topology.modes import layout_options
from jaal_topology.integration import mount_flask
```

`ASSETS_DIR` is the installed distribution's resource directory. The
independent `mount_flask` is an optional bounded viewer; the original
text-category-profiler retains its customized WSGI integration to
preserve project UI behavior.

## Safe update from the independent repo into text-category-profiler

1. Make and review the core change in **this repository**; keep Python,
   Node, HTTP asset and WSGI checks green. Where applicable, confirm
   Windows browser behavior.
2. Record the exact new commit SHA; update the fixed Git dependency in
   `hun186/text-category-profiler/requirements.txt`, not a floating branch.
3. Update any applicable dependency provenance tests, then run the
   consumer's `Portable Jaal Topology Package`,
   `Stage 4 Original Jaal Same-Port Compatibility` and complete Hosted
   CI workflows. Verify the original root selection, Chinese fallback,
   Search/Filter/Color/Size, 4 graph modes, collapse animation, sidebar
   and same-port iframe.
4. Merge the downstream dependency bump **only** after the exact-head
   formal review and CI acceptance criteria pass. Do not use publishing a
   new upstream commit to automatically change an existing consumer.

There is no cross-repository auto-sync or PyPI release obligation at
present. An upstream GitHub merge alone does not update the consumer;
it remains pinned to the previously reviewed commit.

## Compatibility boundaries

Python >=3.10 and matching Jaal/Dash/visdcc versions are required.
Hosted testing is not equivalent to visual acceptance on the user's Windows
machine. Do not imply that all Dash 2/3/4 combinations, external browser
environments or publicly accessible deployments have been certified.
This package starts a loopback-only server by default; exposing the viewer
to the public Internet requires a separate security and deployment review.
