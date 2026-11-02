# General directed graphs — community-collapse design proposal

> **Design only: not yet an implemented clustering mode.** The current `network-collapsed` / `hierarchical-collapsed` engine in `17.jaal_structural_collapse.js` still uses directed descendants from taxonomy-style roots. The new company-email example is intended for **network (fully expanded)** until a separate community mode is implemented and verified.

## Why tree collapse does not generalize
A directed message `A → B` means A sent a communication to B, **not** B reports to A. Cycles, replies, multi-parent nodes, disconnected components and high-degree bridges make the notion of an entire descendant subtree ambiguous. In a connected communication graph, root-based traversal could cover most nodes and make "collapse" misleading.

## Proposed independent controls
- **Layout:** Network / Hierarchical. This only changes visual positioning. A hierarchy layout on an arbitrary email network is not evidence of reporting lines.
- **Abstraction:** All nodes / Structural descendants / Community clusters. Structural descendants should only be offered with an explicit hierarchical-data contract. Preserve the existing four mode codes and behavior for downstream Stage 4 compatibility; introduce a distinct **network-community-collapsed** (or similarly unambiguous) option, not a silent replacement of `network-collapsed`.
- **Algorithm:** start with weighted Louvain as an explicit experimental choice; evaluate Leiden for connected community quality. Partition reproducibly by recording algorithm version, seed, resolution, treatment of edge weights and graph fingerprint. Algorithm choice cannot be inferred from sender-recipient direction alone.

## Directed graph semantics
- Store original directed edges untouched. For clustering, select **directed modularity** when supported. Alternatively construct a clearly disclosed undirected affinity projection where `w(u,v)=messages(u→v)+messages(v→u)`; never claim that projection preserves message direction.
- Aggregate a quotient graph with **separate directed totals** `W(A→B)=Σ w(u→v)` for `u∈A, v∈B`; `W(B→A)` remains independent. Record intra-community edges separately. Show message counts on edges, not fabricated reporting lines.
- When weights are unavailable, default to `w=1` per stored edge and label the result as **topology-only**. Current `load_graph` ignores third+ CSV columns and deduplicates directed pairs: it **cannot measure repeated emails** until an explicit edge-weight/transaction data contract is implemented.
- No original IDs are altered or discarded. Cluster IDs belong to a namespaced **ephemeral display layer**; reopening a cluster restores exact original nodes, directed edges and filters. Cross-group bridges must remain visible and inspectable. High-betweenness bridge nodes and very small communities may be left uncollapsed with explicit reason.

## Proposed UI / safe interaction
- Optional `社群（收攏）` mode with visible `Louvain (experimental)` algorithm, resolution, seed and minimum community size. Allow "expand this community", "collapse", "restore all" and "recalculate"; show count of people, internal directed edges, outgoing and incoming message counts.
- Preserve camera center and nearby node positions when expanding: avoid unconditional `fit()`. Honor reduced-motion preferences and provide a deterministic fallback.
- Fail closed if algorithm unavailable, graph too large, invalid weight or no meaningful partition: show normal network graph and explain, **never silently switch to descendant collapse**.
- Do not mix clusters with Jaal Search/Filter/Color/Size until preservation and restore invariants are tested. Avoid interpolating CSV names into executable browser scripts.

## Validation gate for implementation
1. Test chain, multi-parent DAG, directed cycle, bidirectional pair, hub/star, disconnected components, mixed cluster sizes, duplicate messages and labels with HTML-like text.
2. Assert every original node belongs to exactly one cluster or is explicitly unclustered; all directed source edges can be reconstructed, including reciprocal edges and cross-cluster arcs.
3. Compare seeded stability and modularity across resolution values. Confirm high-betweenness bridges are not incorrectly presented as hierarchy.
4. Test a medium, cross-connected example such as `examples/company_communications.csv`, then stress sizes near current 3,000-node/5,000-edge rendering cap.
5. Perform actual Dash/browser interaction checks on switching full↔community modes, repeated opening, Search/Filter/Color/Size, original ID lookup, iframe embedding, camera stability, and accessibility, followed by downstream Stage 4 exact-commit compatibility CI.

## Prototype dataset provenance
- [Source: `text-category-profiler/ClassesTree/data/TopicTree.csv`](https://github.com/hun186/text-category-profiler/blob/6cc3855ec5d726d5e207e866ca61b165f30ded88/ClassesTree/data/TopicTree.csv) at commit `6cc3855ec5d726d5e207e866ca61b165f30ded88`.
- Select exactly the directed descendant closure of `TW Affairs`: **77 taxonomy nodes, 82 internal edges**. Rename each original class to a **fictional organizational role** using shortest first-discovery depth and first top-level branch, preserving all original edges as `management-briefing`.
- Add deterministic synthetic directed `reply`, `peer-coordination`, `cross-team` communications to create non-tree cycles and lateral connectivity; these are **fictional illustration**, not extracted emails or actual corporate hierarchy. Mapping file exists solely to audit the conversion; it is not required for use.
- Final generated sample: **77 people/roles, 169 unique directed pairs**; breakout: management-briefing=81, reply=28, peer-coordination=50, cross-team=10.
- The `relation` column is documentation only for current reader. Edges `from→to` mean sender→recipient. Multiple messages by the same pair, dates, real persons and email contents are **not modeled**.

## References
- NetworkX Louvain: https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.community.louvain.louvain_communities.html
- NetworkX Leiden: https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.community.leiden.leiden_communities.html
- vis-network clustering (cluster / openCluster): https://visjs.github.io/vis-network/docs/network/
