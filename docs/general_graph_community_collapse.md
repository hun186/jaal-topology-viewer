# General directed graphs — community-collapse design proposal

> **Partial implementation, experimental; browser validation pending.** The independent `network-community-collapsed` mode uses NetworkX directed Louvain (seed 42, resolution 1, `weight=None`) to detect communities. It projects a directed quotient graph in `18.jaal_community_collapse.js`. The older `network-collapsed` / `hierarchical-collapsed` modes still use taxonomy descendant collapse. These are **not** interchangeable. The feature is not production browser-certified.

## Why tree collapse does not generalize
A directed message `A → B` means A sent a communication to B, **not** B reports to A. Cycles, replies, multi-parent nodes, disconnected components and high-degree bridges make the notion of an entire descendant subtree ambiguous. In a connected communication graph, root-based traversal could cover most nodes and make "collapse" misleading.

## Proposed independent controls
- **Layout:** Network / Hierarchical. This only changes visual positioning. A hierarchy layout on an arbitrary email network is not evidence of reporting lines.
- **Abstraction:** All nodes / Structural descendants / Community clusters. Structural descendants should only be offered with an explicit hierarchical-data contract. Preserve the existing four mode codes and behavior for downstream Stage 4 compatibility; introduce a distinct **network-community-collapsed** (or similarly unambiguous) option, not a silent replacement of `network-collapsed`.
- **Algorithm:** implemented first pass: NetworkX directed, topology-only Louvain; deterministic seed 42, resolution 1, no message count weights. Future: expose parameters, support typed weights, benchmark Leiden and log algorithm + graph fingerprint. Do not infer hierarchy from sender→recipient relationships.

## Directed graph semantics
- Store original directed edges untouched. For clustering, select **directed modularity** when supported. Alternatively construct a clearly disclosed undirected affinity projection where `w(u,v)=messages(u→v)+messages(v→u)`; never claim that projection preserves message direction.
- Aggregate a quotient graph with **separate directed totals** `W(A→B)=Σ w(u→v)` for `u∈A, v∈B`; `W(B→A)` remains independent. Record intra-community edges separately. Show message counts on edges, not fabricated reporting lines.
- When weights are unavailable, default to `w=1` per stored edge and label the result as **topology-only**. Current `load_graph` ignores third+ CSV columns and deduplicates directed pairs: it **cannot measure repeated emails** until an explicit edge-weight/transaction data contract is implemented.
- No original IDs are altered or discarded. Cluster IDs belong to a namespaced **ephemeral display layer**; reopening a cluster restores exact original nodes, directed edges and filters. Cross-group bridges must remain visible and inspectable. High-betweenness bridge nodes and very small communities may be left uncollapsed with explicit reason.

## Proposed UI / safe interaction
- Implemented `網狀（社群收攏・Louvain）` fixed-parameter first pass; communities of at least 3 members are represented as compact nodes. Click cluster to expand; click member to re-collapse. User-adjustable resolution, seed, live recalculation, fully surfaced in/out totals and a distinct restore-all button are future UI work.
- Preserve camera center and nearby node positions when expanding: avoid unconditional `fit()`. Honor reduced-motion preferences and provide a deterministic fallback.
- Fail closed if algorithm unavailable, graph too large, invalid weight or no meaningful partition: show normal network graph and explain, **never silently switch to descendant collapse**.
- During upstream Jaal Search/Filter where hidden flags are active, temporarily restore the original filtered DataSets; switching out of community mode restores original IDs/edges. Browser E2E Search/Filter/Color/Size combinations are still an acceptance gate. Never interpolate CSV names into executable browser scripts.

## Validation gate for implementation
1. Test chain, multi-parent DAG, directed cycle, bidirectional pair, hub/star, disconnected components, mixed cluster sizes, duplicate messages and labels with HTML-like text.
2. Assert every original node belongs to exactly one cluster or is explicitly unclustered; all directed source edges can be reconstructed, including reciprocal edges and cross-cluster arcs.
3. Compare seeded stability and modularity across resolution values. Confirm high-betweenness bridges are not incorrectly presented as hierarchy.
4. Test a medium, cross-connected example such as `examples/company_communications.csv`, then stress sizes near current 3,000-node/5,000-edge rendering cap.
5. Perform actual Dash/browser interaction checks on switching full↔community modes, repeated opening, Search/Filter/Color/Size, original ID lookup, iframe embedding, camera stability, and accessibility, followed by downstream Stage 4 exact-commit compatibility CI.

## Prototype dataset provenance
- [Source: `text-category-profiler/ClassesTree/data/TopicTree.csv`](https://github.com/hun186/text-category-profiler/blob/6cc3855ec5d726d5e207e866ca61b165f30ded88/ClassesTree/data/TopicTree.csv) at commit `6cc3855ec5d726d5e207e866ca61b165f30ded88`.
- Select exactly the directed descendant closure of `TW Affairs`: **77 taxonomy nodes, 82 internal edge rows (81 unique directed pairs)**. Rename each original class to a **fictional organizational role** using shortest first-discovery depth and first top-level branch, preserving all original edges as `management-briefing`.
- Add deterministic synthetic directed `reply`, `peer-coordination`, `cross-team` communications to create non-tree cycles and lateral connectivity; these are **fictional illustration**, not extracted emails or actual corporate hierarchy. Mapping file exists solely to audit the conversion; it is not required for use.
- Final generated sample: **77 people/roles, 169 unique directed pairs**; breakout: management-briefing=81, reply=28, peer-coordination=50, cross-team=10.
- The `relation` column is documentation only for current reader. Edges `from→to` mean sender→recipient. Multiple messages by the same pair, dates, real persons and email contents are **not modeled**.

## References
- NetworkX Louvain: https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.community.louvain.louvain_communities.html
- NetworkX Leiden: https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.community.leiden.leiden_communities.html
- vis-network clustering (cluster / openCluster): https://visjs.github.io/vis-network/docs/network/
