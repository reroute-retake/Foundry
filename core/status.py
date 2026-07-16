"""Per-batch ledger status report (ADR 017's ``status``).

Read-only. Answers the Operator's two questions before every phase: *what is
ready to advance* and *what is blocked/terminal*. Derived from the event log via
``ledger.fold`` — it never mutates state.
"""

from dataclasses import dataclass, field
from pathlib import Path

import ledger
from pipeline_ledger import TRANSITION_RULES, NodeState

# Actions whose sole precondition is the node's current state (verdict- and
# document-independent), used to compute "what can advance next" cheaply.
_SIMPLE_NEXT = {
    rule.to_state: rule.action
    for rule in TRANSITION_RULES
    if rule.requires_verdict is None and not rule.requires_document_extracted
}

_TERMINAL: set[NodeState] = {"CANONICAL"}
_BLOCKED: set[NodeState] = {"QUARANTINED"}


@dataclass
class StatusReport:
    total_nodes: int = 0
    by_state: dict[str, int] = field(default_factory=dict)
    quarantined: list[str] = field(default_factory=list)
    canonical: list[str] = field(default_factory=list)
    documents_extracted: int = 0
    documents_total: int = 0

    def render(self) -> str:
        lines = [
            f"Nodes: {self.total_nodes}  |  documents extracted: "
            f"{self.documents_extracted}/{self.documents_total}",
        ]
        for state in sorted(self.by_state):
            lines.append(f"  {state:<20} {self.by_state[state]}")
        if self.quarantined:
            lines.append(f"QUARANTINED ({len(self.quarantined)}): {', '.join(self.quarantined)}")
        if self.canonical:
            lines.append(f"CANONICAL ({len(self.canonical)})")
        return "\n".join(lines)


def build_report(root: Path) -> StatusReport:
    manifest = ledger.fold(ledger.read_events(root))
    report = StatusReport()
    report.documents_total = len(manifest.documents)
    report.documents_extracted = sum(1 for d in manifest.documents.values() if d.extracted)
    for entry in manifest.nodes.values():
        report.total_nodes += 1
        report.by_state[entry.state] = report.by_state.get(entry.state, 0) + 1
        if entry.state in _BLOCKED:
            report.quarantined.append(entry.canonical_id)
        elif entry.state in _TERMINAL:
            report.canonical.append(entry.canonical_id)
    report.quarantined.sort()
    report.canonical.sort()
    return report
