"""Deterministic Louvain groups for bounded directed graphs.

Ordinary CSV graphs retain original topology-only, unit-weight semantics.
Explicit synthetic email graphs can additionally carry directed event counts:
Louvain uses event frequency as weight, while quotient directed-pair counts
remain the original number of *unique pairs*, not number of mail events.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import isfinite

from .data import Graph, GraphInputError, assess_structural_collapse


@dataclass(frozen=True)
class CommunityResult:
    groups: tuple[tuple[str, ...], ...]
    member_to_group: dict[str, str]
    cross_group_edges: dict[tuple[str, str], int]
    internal_edges: dict[str, int]
    quotient_has_cycle: bool = False
    method: str = "directed-louvain-topology-only"
    seed: int = 42
    resolution: float = 1.0


def community_quotient_has_cycle(groups, directed_pairs) -> bool:
    """Detect directed cycles AFTER aggregation, without changing the source."""
    labels = tuple(sorted(set(groups)))
    if not labels:
        return False
    inter = tuple(sorted(set((a, b) for a, b in directed_pairs if a != b)))
    return assess_structural_collapse(Graph(inter, labels)).has_cycle


def detect_louvain(graph: Graph, *, resolution: float = 1.0,
                   seed: int = 42, allow_large_demo: bool = False) -> CommunityResult:
    """Partition a selected graph; preserve directed aggregates independently.

    Group identifiers are local to a *single partition result*. They are not
    external node IDs; the view layer must use collision-safe synthetic IDs.
    """
    if type(seed) is not int:
        raise GraphInputError("Louvain seed must be an integer")
    if isinstance(resolution, bool) or not isinstance(resolution, (int, float)) or (
        not isfinite(resolution) or resolution <= 0
    ):
        raise GraphInputError("Louvain resolution must be a finite positive number")
    # The larger ceiling is never the default; it is exclusively enabled for
    # a reviewed, fictional, locally opted-in Gallery case.
    max_nodes, max_edges = ((20_000, 50_000) if allow_large_demo
                            else (3000, 5000))
    if len(graph.nodes) > max_nodes or len(graph.edges) > max_edges:
        raise GraphInputError("Select a bounded graph before community analysis")
    if len(set(graph.nodes)) != len(graph.nodes):
        raise GraphInputError("Graph has duplicate node IDs")
    nodes = set(graph.nodes)
    if any(a not in nodes or b not in nodes for a, b in graph.edges):
        raise GraphInputError("Graph edge endpoint is absent from node IDs")
    if len(set(graph.edges)) != len(graph.edges):
        raise GraphInputError("Community analysis requires deduplicated directed edges")

    import networkx as nx

    directed = nx.DiGraph()
    directed.add_nodes_from(sorted(graph.nodes))
    if graph.edge_counts:
        if set(graph.edge_counts) != set(graph.edges):
            raise GraphInputError("Weighted community graph needs every directed pair")
        for (sender, recipient), count in graph.edge_counts.items():
            if type(count) is not int or not 1 <= count <= 1_000_000:
                raise GraphInputError("Message frequency must be a positive bounded integer")
            directed.add_edge(sender, recipient, weight=count)
        weight_field = "weight"
    else:
        # Original taxonomy and network semantics remain topology-only:
        # every distinct directed pair has an equal unit contribution.
        directed.add_edges_from(graph.edges)
        weight_field = None
    if directed.number_of_edges():
        raw_groups = nx.community.louvain_communities(
            directed, weight=weight_field, resolution=float(resolution), seed=seed,
        )
    else:
        raw_groups = [{node} for node in directed.nodes]
    ordered = tuple(sorted(
        (tuple(sorted(group)) for group in raw_groups),
        key=lambda group: (-len(group), group),
    ))
    if set.union(set(), *(set(group) for group in ordered)) != nodes or (
        sum(map(len, ordered)) != len(nodes)
    ):
        raise RuntimeError("Louvain produced an incomplete or overlapping partition")

    memberships = {
        member: f"community-{index}"
        for index, group in enumerate(ordered)
        for member in group
    }
    between: Counter[tuple[str, str]] = Counter()
    within: Counter[str] = Counter()
    for sender, recipient in graph.edges:
        src, dst = memberships[sender], memberships[recipient]
        if src == dst:
            within[src] += 1
        else:
            between[(src, dst)] += 1
    assert sum(within.values()) + sum(between.values()) == len(graph.edges)
    quotient_cyclic = community_quotient_has_cycle(
        memberships.values(), between.keys()
    )
    return CommunityResult(
        ordered, memberships, dict(sorted(between.items())),
        dict(sorted(within.items())), quotient_has_cycle=quotient_cyclic,
        seed=seed, resolution=float(resolution),
        method=("directed-louvain-message-count-weighted" if graph.edge_counts
                else "directed-louvain-topology-only"),
    )
