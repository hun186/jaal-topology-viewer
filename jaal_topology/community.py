"""Deterministic topology-only Louvain groups for bounded directed graphs.

The current CSV reader deduplicates (sender, recipient) edges and ignores
extra columns: the groups and directed counts are *not* email frequency.
Original graph IDs, edges and translations remain untouched.
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
                   seed: int = 42) -> CommunityResult:
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
    if len(graph.nodes) > 3000 or len(graph.edges) > 5000:
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
    # The graph is topology-only: each distinct directed pair has weight 1.
    directed.add_edges_from(graph.edges)
    if directed.number_of_edges():
        raw_groups = nx.community.louvain_communities(
            directed, weight=None, resolution=float(resolution), seed=seed,
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
    )
