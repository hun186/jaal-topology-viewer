"""Deterministic, scenario-based fictional corporate email event simulation.

This is a teaching dataset, NOT real corporate mail or a statistically
validated population model. Employees are role names, not real people.
Business rules drive who contacts whom, timing, replies and incidents.
A fixed random seed adds bounded variation without creating arbitrary edges.
No network access, personal data, external storage or runtime CSV ingestion.
"""
from __future__ import annotations

import csv
import io
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from types import MappingProxyType

from .data import Graph, GraphInputError

SEED = 20261103
START_DAY = datetime(2026, 10, 5, 9, 0)
WORK_DAYS = 20

# The first person is each division's head, followed by distinct working
# roles. Direct managers are real team leads (not simply randomly chosen).
DEPARTMENTS = (
    ("Executive", "經營管理", ("CEO", "COO", "CFO", "CTO")),
    ("Engineering", "工程研發", ("VP", "Platform Lead", "Backend Lead",
                             "Data Lead", *("Engineer %02d" % i for i in range(1, 13)))),
    ("Product", "產品企劃", ("VP", "Design Lead", "Product Lead",
                         *("PM %02d" % i for i in range(1, 8)))),
    ("Sales", "業務拓展", ("VP", "Enterprise Lead", "Channel Lead",
                       *("Account Rep %02d" % i for i in range(1, 9)))),
    ("Customer Success", "客戶服務", ("VP", "Support Lead", "Onboarding Lead",
                                    *("Agent %02d" % i for i in range(1, 9)))),
    ("Finance", "財務管理", ("VP", "Accounting Lead", "Planning Lead",
                         *("Analyst %02d" % i for i in range(1, 6)))),
    ("Operations", "營運供應", ("VP", "Procurement Lead", "Delivery Lead",
                             *("Coordinator %02d" % i for i in range(1, 7)))),
    ("People", "人力資源", ("VP", "Recruiting Lead",
                         *("HR Specialist %02d" % i for i in range(1, 5)))),
    ("Security", "資訊安全", ("VP", "Security Lead",
                           *("Analyst %02d" % i for i in range(1, 4)))),
)

WORKFLOW_LABELS = {
    "team-routine": "團隊例行協作",
    "manager-report": "主管回報／指示",
    "customer-deal": "客戶提案／報價",
    "customer-escalation": "客訴與技術升級",
    "incident-response": "系統事件應變",
    "month-close": "月結／財務核對",
    "management-update": "經營管理公告",
    "onboarding": "新進同仁協作",
}


@dataclass(frozen=True)
class EmailEvent:
    id: str
    timestamp: str
    thread_id: str
    sender: str
    recipient: str
    workflow: str
    subject: str
    reply_to: str = ""


@dataclass(frozen=True)
class MailSimulation:
    graph: Graph
    events: tuple[EmailEvent, ...]
    divisions: dict[str, str]
    counts: dict[tuple[str, str], int]

    def events_csv(self) -> str:
        """UTF-8 export with an explicit fictional provenance header."""
        out = io.StringIO(newline="")
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow([
            "event_id", "timestamp", "thread_id", "from", "to",
            "workflow", "subject", "reply_to",
        ])
        for event in self.events:
            writer.writerow((
                event.id, event.timestamp, event.thread_id, event.sender,
                event.recipient, event.workflow, event.subject, event.reply_to,
            ))
        return out.getvalue()

    def aggregate_csv(self) -> str:
        out = io.StringIO(newline="")
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow(["from", "to", "message_count", "synthetic"])
        for (sender, recipient), count in sorted(self.counts.items()):
            writer.writerow([sender, recipient, count, "true"])
        return out.getvalue()


def simulate_company_email(seed: int = SEED) -> MailSimulation:
    """Build a reproducible 20-workday event log, then aggregate it to a graph.

    Mechanisms: frequent intra-team chatter, manager reports and delegation,
    bidirectional replies in the SAME thread, cross-functional deal / support
    workflows, one security incident spike, end-of-month finance close,
    limited executive broadcasts and HR onboarding. The random source changes
    intensity and employee choice within these workflows, not graph topology
    picked uniformly at random.
    """
    if type(seed) is not int or not 0 <= seed <= 2**32 - 1:
        raise GraphInputError("Email simulation seed must be a 32-bit unsigned integer")
    rng = random.Random(seed)
    dept_people: dict[str, tuple[str, ...]] = {}
    divisions: dict[str, str] = {}
    translations: dict[str, str] = {}
    heads: dict[str, str] = {}
    manager: dict[str, str] = {}
    for dept, zh, titles in DEPARTMENTS:
        ids = tuple(f"{dept} / {title}" for title in titles)
        dept_people[dept] = ids
        heads[dept] = ids[0]
        for person, title in zip(ids, titles):
            divisions[person] = dept
            translations[person] = f"{zh}／{title}"
            if dept != "Executive" and person != ids[0]:
                # Assigned to a stable team lead, not an arbitrary colleague.
                lead_count = 3 if dept in ("Engineering", "Product") else (
                    2 if dept not in ("People", "Security") else 1
                )
                if person in ids[1: 1 + lead_count]:
                    manager[person] = ids[0]
                else:
                    subteam = (ids.index(person) - 1 - lead_count) % lead_count
                    manager[person] = ids[1 + subteam]

    events: list[EmailEvent] = []
    day_events: dict[int, int] = defaultdict(int)
    serial = 0
    thread_serial = 0

    def thread(prefix: str) -> str:
        nonlocal thread_serial
        thread_serial += 1
        return f"{prefix}-{thread_serial:05d}"

    def emit(day: int, sender: str, recipient: str, flow: str,
             topic: str, thread_id: str, hour: int | None = None,
             minute: int | None = None, reply_to: str = "") -> EmailEvent:
        nonlocal serial
        if sender not in divisions or recipient not in divisions or sender == recipient:
            raise RuntimeError("Synthetic workflow has invalid sender/recipient")
        if flow not in WORKFLOW_LABELS:
            raise RuntimeError("Unknown mail workflow")
        serial += 1
        current = START_DAY + timedelta(days=day + 2 * (day // 5))
        at = current.replace(
            hour=hour if hour is not None else rng.randrange(9, 18),
            minute=minute if minute is not None else rng.randrange(60),
        )
        event = EmailEvent(
            f"M-{serial:06d}", at.isoformat(timespec="minutes"),
            thread_id, sender, recipient, flow, topic, reply_to,
        )
        events.append(event)
        day_events[day] += 1
        return event

    def exchange(day: int, sender: str, recipient: str, flow: str,
                 topic: str, response_chance: float = 0.65,
                 hour: int | None = None, thread_id: str | None = None):
        t = thread_id or thread(flow[:4].upper())
        sent = emit(day, sender, recipient, flow, topic, t, hour=hour)
        if rng.random() < response_chance:
            emit(day, recipient, sender, flow, "RE: " + topic, t,
                 hour=hour, reply_to=sent.id)
        return t

    all_staff = [p for dept, people in dept_people.items()
                 if dept != "Executive" for p in people]
    everyone = tuple(divisions)
    # Enforce that leadership is low-volume relative to ordinary collaboration;
    # CEO only appears in periodic executive messages, not generic daily chatter.
    for day in range(WORK_DAYS):
        # Daily within-department communication and stable reporting lines.
        for dept, members in dept_people.items():
            if dept == "Executive":
                continue
            staff = members[1:]
            for person in staff:
                if rng.random() < 0.57:
                    peer = rng.choice([x for x in staff if x != person])
                    exchange(day, person, peer, "team-routine",
                             "任務進度／協作回覆", response_chance=0.55)
                if rng.random() < 0.44:
                    exchange(day, person, manager[person], "manager-report",
                             "每日進度與待辦", response_chance=0.43)
            for leader in members[: min(3, len(members))]:
                if rng.random() < 0.75:
                    recipient = rng.choice([x for x in staff if x != leader])
                    exchange(day, leader, recipient, "manager-report",
                             "任務派工與優先順序", response_chance=0.5)

        # Deals: sales coordinates product needs, operational lead time and price.
        for _ in range(3):
            rep = rng.choice(dept_people["Sales"][3:])
            product = rng.choice(dept_people["Product"][1:])
            finance = rng.choice(dept_people["Finance"][1:])
            ops = rng.choice(dept_people["Operations"][1:])
            t = thread("DEAL")
            exchange(day, rep, product, "customer-deal",
                     "客戶需求／產品確認", 0.78, thread_id=t)
            exchange(day, rep, finance, "customer-deal",
                     "價格條件／簽核", 0.62, thread_id=t)
            if rng.random() < 0.68:
                exchange(day, product, ops, "customer-deal",
                         "交期與交付準備", 0.54, thread_id=t)

        # Customer cases: frontline escalation to engineering and product,
        # with direct technical and customer follow-up.
        for _ in range(2):
            support = rng.choice(dept_people["Customer Success"][3:])
            engineer = rng.choice(dept_people["Engineering"][4:])
            owner = rng.choice(dept_people["Product"][3:])
            t = thread("TICKET")
            exchange(day, support, engineer, "customer-escalation",
                     "客戶問題單／技術釐清", 0.88, thread_id=t)
            exchange(day, engineer, owner, "customer-escalation",
                     "修復優先序／重現條件", 0.72, thread_id=t)
            if rng.random() < 0.4:
                exchange(day, owner, support, "customer-escalation",
                         "回覆客戶／排程", 0.55, thread_id=t)

        # HR onboarding happens once per week to several *different* roles.
        if day % 5 == 0:
            hr = dept_people["People"][2]
            for person in rng.sample([x for x in all_staff if x != hr], 4):
                exchange(day, hr, person, "onboarding",
                         "新人帳號／教育訓練", 0.36, thread_id=thread("HR"))
        # Executive briefings are periodic and target division heads only.
        if day % 5 == 4:
            for target in [heads[d] for d in dept_people if d != "Executive"]:
                exchange(day, heads["Executive"], target, "management-update",
                         "週營運摘要／主管會議", 0.30, thread_id=thread("MGMT"))

        # Two incidents, deliberately outside routine office hours, create
        # temporary bridges among engineering, operations, security, CTO.
        if day in (6, 12):
            t = thread("INCIDENT")
            engineer = dept_people["Engineering"][4]
            security = dept_people["Security"][1]
            ops = dept_people["Operations"][1]
            product = dept_people["Product"][1]
            for _ in range(8):
                exchange(day, engineer, security, "incident-response",
                         "系統異常／權限與風險確認", 0.95, hour=20,
                         thread_id=t)
                exchange(day, security, ops, "incident-response",
                         "服務恢復／事件通報", 0.90, hour=21,
                         thread_id=t)
                exchange(day, engineer, product, "incident-response",
                         "回復排程／客戶影響", 0.85, hour=22,
                         thread_id=t)
            exchange(day, ops, heads["Executive"].replace("CEO", "CTO"),
                     "incident-response", "事件升級／處置摘要", 0.70,
                     hour=22, thread_id=t)

        # Month-end finance reconciliation causes a different bridge pattern.
        if day in (17, 18, 19):
            for dept in ("Sales", "Operations", "People", "Product"):
                for _ in range(4):
                    exchange(day, dept_people["Finance"][2], heads[dept],
                             "month-close", "月結對帳／費用確認", 0.78,
                             thread_id=thread("CLOSE"))
            exchange(day, heads["Finance"], "Executive / CFO",
                     "month-close", "月度結帳與例外事項", 0.84)

    # Preserve the actual event log as the authoritative volume source.
    # Directed pairs are deduplicated only when adapted for the Jaal graph.
    counts = Counter((m.sender, m.recipient) for m in events)
    if not counts or any(value <= 0 for value in counts.values()):
        raise RuntimeError("Synthetic email event log is unexpectedly empty")
    # Some people can have zero activity in a sampling window: keep this
    # explicit rather than silently inventing arbitrary edges for them.
    active_nodes = tuple(sorted({x for a, b in counts for x in (a, b)}))
    graph = Graph(
        edges=tuple(sorted(counts)),
        nodes=active_nodes,
        translations={k: translations[k] for k in active_nodes},
        edge_counts=dict(counts),
    )
    return MailSimulation(graph, tuple(events),
                          {k: divisions[k] for k in active_nodes},
                          dict(counts))
