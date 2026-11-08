"""Local opt-in deterministic fictitious company email Graph + dated events.

These are full inputs to original Jaal/Dash, never a separate SVG/Canvas
renderer, not actual employees/messages, and no real email is accessed.
"""
from __future__ import annotations
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import timedelta
from math import cos, sin
from .data import Graph, GraphInputError
from .email_simulation import EmailEvent, START_DAY

SCALES = {"500": (500, 1), "3000": (3000, 1),
          "5000": (5000, 1), "20000": (20000, 1),
          "3000-dag": (3000, 1),
          "three-components": (500, 3)}
MAX_DEMO_NODES = 20_000
MAX_DEMO_EDGES = 50_000


@dataclass(frozen=True)
class ScaledEmailDemo:
    graph: Graph
    events: tuple[EmailEvent, ...]
    departments: int
    depth: int
    components: tuple[int, ...]
    positions: dict[str, tuple[float, float]]


def component_sizes(graph: Graph) -> tuple[int, ...]:
    adj = defaultdict(list)
    for a, b in graph.edges:
        adj[a].append(b)
        adj[b].append(a)
    unseen, sizes = set(graph.nodes), []
    while unseen:
        start = min(unseen)
        unseen.remove(start)
        pending = deque([start])
        count = 0
        while pending:
            count += 1
            for nxt in adj[pending.popleft()]:
                if nxt in unseen:
                    unseen.remove(nxt)
                    pending.append(nxt)
        sizes.append(count)
    return tuple(sorted(sizes, reverse=True))


def build_scaled_email_demo(key: str) -> ScaledEmailDemo:
    if type(key) is not str or key not in SCALES:
        raise GraphInputError("Unknown fixed synthetic full-Jaal scenario")
    total, components = SCALES[key]
    acyclic = key == "3000-dag"
    nodes, labels, positions = [], {}, {}
    pairs = {}
    dept_total, max_depth = 0, 0

    def mail(sender: str, recipient: str):
        if sender != recipient:
            pairs[(sender, recipient)] = 1

    for company in range(components):
        target_count = total // components + (company < total % components)
        dept_count = min(200, max(3, target_count // 82))
        regions_count = max(1, (dept_count + 11) // 12)
        columns = max(2, int((dept_count*1.6)**.5 + .999999))
        left, serial, initial = company * (columns*240 + 1500), 0, len(nodes)

        def person(title, manager, level, x, y):
            nonlocal serial, max_depth
            serial += 1
            node = f"C{company+1:02d}-N{serial:05d}"
            nodes.append(node)
            labels[node] = f"集團 {company+1}／{title}"
            positions[node] = (x, y)
            max_depth = max(max_depth, level)
            if manager is not None:
                mail(node, manager)
                if serial % 4 == 0 and not acyclic:
                    mail(manager, node)
            return node

        ceo = person("總經理", None, 0, left+columns*120, 0)
        regions = [person(f"區域副總 {i+1:02d}", ceo, 1,
                          left+(i+1)*columns*240/(regions_count+1), 110)
                   for i in range(regions_count)]
        depts = []
        for i in range(dept_count):
            x, y = left+(i%columns)*240, 420+(i//columns)*220
            title = f"部門 {i+1:03d}"
            head = person(f"{title}／部門主管", regions[i//12], 2, x, y)
            depts.append({"head":head, "title":title, "x":x, "y":y,
                          "front":(), "slot":0, "last":None})
            dept_total += 1
        for d in depts:
            teams = [person(f"{d['title']}／組長 {i+1}",d["head"],3,
                            d["x"]+(i-1)*30,d["y"]+40) for i in range(3)]
            groups = [person(f"{d['title']}／小組主管 {i+1}",teams[i%3],4,
                             d["x"]+(i-2.5)*25,d["y"]+80) for i in range(6)]
            front = groups
            if target_count >= 3000:
                front = [person(f"{d['title']}／專案經理 {i+1}",groups[i%6],5,
                                d["x"]+(i-1.5)*25,d["y"]+120) for i in range(4)]
            if target_count >= 10000:
                front = [person(f"{d['title']}／資深領班 {i+1}",
                                front[i%len(front)],6,d["x"]+(i-2.5)*22,
                                d["y"]+150) for i in range(6)]
            d["front"] = tuple(front)

        extra = target_count-(len(nodes)-initial)
        if extra < 0:
            raise GraphInputError("Requested size smaller than management structure")
        for i in range(extra):
            d = depts[i%len(depts)]
            slot = d["slot"]
            leader = d["front"][slot%len(d["front"])]
            radius, angle = 20+6*slot**.5,slot*2.399963229728653
            worker = person(f"{d['title']}／專員 {i+1:05d}",leader,
                            7 if target_count>=10000 else 6 if target_count>=3000 else 5,
                            d["x"]+radius*cos(angle),
                            d["y"]+190+radius*sin(angle))
            d["slot"] += 1
            if d["last"] is not None:
                mail(worker, d["last"])
                if i%5==0 and not acyclic: mail(d["last"], worker)
            d["last"] = worker
            if i%17==0:
                mail(worker,depts[(i+1)%len(depts)]["head"])
        if len(nodes)-initial != target_count:
            raise GraphInputError("Synthetic graph size mismatch")

    if len(nodes)!=total or len(nodes)>MAX_DEMO_NODES or len(pairs)>MAX_DEMO_EDGES:
        raise GraphInputError("Synthetic full-Jaal dataset exceeds 20k/50k cap")
    ordered = tuple(sorted(pairs))
    # At most one dated event per directed pair: 20k case is below the
    # unchanged TemporalTimeline 50,000-event limit.
    events = []
    for i,(sender,recipient) in enumerate(ordered):
        day = i%20
        stamp = START_DAY + timedelta(days=day+2*(day//5),minutes=(i*13)%540)
        events.append(EmailEvent(
            id=f"S-{i+1:06d}",timestamp=stamp.isoformat(timespec="minutes"),
            thread_id=f"SYNTH-{i+1:06d}",sender=sender,recipient=recipient,
            workflow="manager-report" if i%3==0 else "team-routine",
            subject="虛構企業任務與回覆"))
    graph = Graph(ordered,tuple(sorted(nodes)),labels,dict(pairs))
    actual = component_sizes(graph)
    expected = tuple(sorted((total//components+(i<total%components)
                             for i in range(components)),reverse=True))
    if actual!=expected:
        raise GraphInputError("The intended disconnected components are linked")
    return ScaledEmailDemo(
        graph,tuple(sorted(events,key=lambda m:(m.timestamp,m.id))),
        dept_total,max_depth,actual,positions)
