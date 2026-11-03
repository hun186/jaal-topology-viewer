"""Bounded root-oriented exploration of a directed graph (no source mutation)."""
from __future__ import annotations

from collections import deque

from .data import Graph, GraphInputError

DIRECTIONS = frozenset(("out", "in", "both"))
MAX_HOPS = 10


def reachable_node_ids(graph: Graph, root: str | None, *,
                       hops: int | str = 2, direction: str = "out") -> tuple[str, ...]:
    """Return original IDs at shortest-path distance <= hops.

    out follows parent/sender to child/recipient; in follows incoming edges.
    both ignores edge direction for reachability only. Rendering must retain
    original directed edges. hops='all' explores the full reachable component.
    BFS visits each ID once even for cycles or shared ancestors.
    """
    if not isinstance(graph, Graph):
        raise GraphInputError("Root exploration expects a Graph")
    if direction not in DIRECTIONS:
        raise GraphInputError("Direction must be out, in or both")
    if hops != "all" and (type(hops) is not int or not 0 <= hops <= MAX_HOPS):
        raise GraphInputError("Exploration radius must be 0..10 or all")
    if root is None:
        return graph.nodes
    if not isinstance(root, str) or root not in set(graph.nodes):
        raise GraphInputError("Unknown root node")
    neighbor: dict[str, set[str]] = {name: set() for name in graph.nodes}
    for source, target in graph.edges:
        if direction in ("out", "both"):
            neighbor[source].add(target)
        if direction in ("in", "both"):
            neighbor[target].add(source)
    limit = len(graph.nodes) if hops == "all" else hops
    found = {root}
    queue = deque([(root, 0)])
    while queue:
        node, distance = queue.popleft()
        if distance >= limit:
            continue
        for nxt in neighbor[node]:
            if nxt in found:
                continue
            found.add(nxt)
            queue.append((nxt, distance + 1))
    return tuple(node for node in graph.nodes if node in found)
