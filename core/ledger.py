"""Ledger engine: ULIDs, precondition validation, fold, append (ADR 017).

The ledger is the sole sequencing authority. This module derives everything
from the append-only event log — the manifest is a convenience snapshot, never
trusted as authority (crash-safety witness: ``fold(events)`` must equal the
persisted manifest).

Write protocol (docs/pipeline-ledger.md; orchestrated by mutation scripts):
    flock → validate_node_transition → write artifacts + sha256 →
    append_event + fsync → rebuild_manifest (atomic rename)

This module owns validation, folding, ULID minting, and the append/rebuild
primitives. It never decides *business* outcomes (verdicts, content) — those
arrive from the scripts and the LLM roles.
"""

import secrets
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from pydantic import TypeAdapter

import canonical_json
import workspace
from pipeline_ledger import (
    MAX_FIX_CYCLES_PER_GATE,
    TRANSITION_RULES,
    ArtifactRef,
    DocumentEvent,
    DocumentManifestEntry,
    LedgerEvent,
    LedgerManifest,
    NodeAction,
    NodeManifestEntry,
    NodeState,
    NodeTransitionEvent,
    TransitionRule,
)

# A concrete alias for the event union (the schema's ``LedgerEvent`` is an
# Annotated form; this is the plain union used for static typing).
Event = NodeTransitionEvent | DocumentEvent

# One adapter for the whole discriminated union — parses each JSONL line.
_EVENT_ADAPTER: TypeAdapter[Event] = TypeAdapter(LedgerEvent)

_RULES_BY_ACTION: dict[NodeAction, TransitionRule] = {
    rule.action: rule for rule in TRANSITION_RULES
}

# Which gate a bounded FIX action belongs to (for cycle accounting).
_GATE1_FIX = "FIX_BASE"
_GATE2_FIX = "FIX_ENRICHMENT"


class LedgerError(RuntimeError):
    """Base for ledger failures."""


class TransitionError(LedgerError):
    """A requested transition violates the precondition table (structured refusal)."""


class QuarantineRequired(TransitionError):
    """A bounded gate exhausted its fix cycles; the caller must QUARANTINE."""


# ---------------------------------------------------------------------------
# ULID — pure-python, lexicographically sortable (no new dependency)
# ---------------------------------------------------------------------------

_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"  # excludes I, L, O, U


def new_ulid(now_ms: Optional[int] = None) -> str:
    """26-char Crockford base32 ULID: 48-bit ms timestamp + 80-bit randomness."""
    timestamp = int(time.time() * 1000) if now_ms is None else now_ms
    if not 0 <= timestamp < (1 << 48):
        raise ValueError("timestamp out of 48-bit ULID range")
    value = (timestamp << 80) | int.from_bytes(secrets.token_bytes(10), "big")
    chars = [""] * 26
    for i in range(25, -1, -1):
        value, rem = divmod(value, 32)
        chars[i] = _CROCKFORD[rem]
    return "".join(chars)


def utc_now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ---------------------------------------------------------------------------
# Derived per-node snapshot (single source of truth for fold AND validate)
# ---------------------------------------------------------------------------

@dataclass
class _NodeAccum:
    state: Optional[NodeState] = None
    last_sequence: int = 0
    revision: int = 0
    fix_cycle_gate1: int = 0
    fix_cycle_gate2: int = 0
    latest_verdict: Optional[str] = None
    last_event_id: str = ""
    updated_at: str = ""
    history_states: set[str] = field(default_factory=set)  # states ever occupied (RELEASE membership)
    current_artifacts: list[ArtifactRef] = field(default_factory=list)


@dataclass
class _DocAccum:
    source_sha256: str
    extracted: bool = False
    extracted_text: Optional[ArtifactRef] = None


def _accumulate(events: list[Event]) -> tuple[dict[str, _NodeAccum], dict[str, _DocAccum]]:
    """Fold events into per-node and per-document accumulators."""
    nodes: dict[str, _NodeAccum] = {}
    documents: dict[str, _DocAccum] = {}
    for event in events:
        if isinstance(event, DocumentEvent):
            doc = documents.setdefault(event.document_id, _DocAccum(source_sha256=event.source_sha256))
            if event.action == "EXTRACT":
                doc.extracted = True
                for artifact in event.produced:
                    if artifact.kind == "extracted_text":
                        doc.extracted_text = artifact
            continue

        assert isinstance(event, NodeTransitionEvent)
        acc = nodes.setdefault(event.canonical_id, _NodeAccum())
        acc.state = event.to_state
        acc.last_sequence = event.sequence
        acc.revision = event.sequence
        acc.last_event_id = event.event_id
        acc.updated_at = event.occurred_at
        acc.history_states.add(event.to_state)
        if event.action == _GATE1_FIX:
            acc.fix_cycle_gate1 += 1
        elif event.action == _GATE2_FIX:
            acc.fix_cycle_gate2 += 1
        if event.verdict is not None:
            acc.latest_verdict = event.verdict
        if event.produced:
            acc.current_artifacts = list(event.produced)
    return nodes, documents


# ---------------------------------------------------------------------------
# Manifest fold (schema-compliant snapshot)
# ---------------------------------------------------------------------------

def fold(events: list[Event]) -> LedgerManifest:
    """Rebuild the manifest from the full event list (never authoritative)."""
    nodes, documents = _accumulate(events)
    manifest = LedgerManifest()
    for canonical_id, acc in nodes.items():
        assert acc.state is not None
        manifest.nodes[canonical_id] = NodeManifestEntry(
            canonical_id=canonical_id,
            state=acc.state,
            revision=acc.revision,
            fix_cycle_gate1=acc.fix_cycle_gate1,
            fix_cycle_gate2=acc.fix_cycle_gate2,
            last_event_id=acc.last_event_id,
            last_sequence=acc.last_sequence,
            current_artifacts=acc.current_artifacts,
            updated_at=acc.updated_at,
        )
    for document_id, doc in documents.items():
        manifest.documents[document_id] = DocumentManifestEntry(
            document_id=document_id,
            source_sha256=doc.source_sha256,
            extracted=doc.extracted,
            extracted_text=doc.extracted_text,
        )
    if events:
        manifest.folded_through_event_id = events[-1].event_id
    return manifest


# ---------------------------------------------------------------------------
# Precondition validation
# ---------------------------------------------------------------------------

@dataclass
class ResolvedTransition:
    rule: TransitionRule
    from_state: Optional[NodeState]
    to_state: NodeState
    sequence: int
    fix_cycle: int  # resulting gate cycle recorded on the event


def validate_node_transition(
    events: list[Event],
    action: NodeAction,
    canonical_id: str,
    *,
    event_verdict: Optional[str] = None,
    document_extracted: bool = False,
) -> ResolvedTransition:
    """Check a requested transition against ``TRANSITION_RULES``; raise on refusal.

    ``events`` is the current node event log (document events are ignored here).
    ``event_verdict`` is the verdict carried by THIS action (REVIEW_* only).
    ``document_extracted`` gates DISCOVER (the node's document must be extracted).
    """
    rule = _RULES_BY_ACTION.get(action)
    if rule is None:
        raise TransitionError(f"no transition rule for action {action!r} (RELEASE is script-mediated)")

    nodes, _ = _accumulate([e for e in events if isinstance(e, NodeTransitionEvent)])
    acc = nodes.get(canonical_id)
    from_state: Optional[NodeState] = acc.state if acc else None

    if from_state not in rule.allowed_from:
        raise TransitionError(
            f"{action} refused: node {canonical_id!r} is {from_state or 'ABSENT'}, "
            f"allowed_from={rule.allowed_from}"
        )

    if rule.requires_document_extracted and not document_extracted:
        raise TransitionError(f"{action} refused: source document not yet EXTRACTED")

    if rule.requires_verdict is not None:
        latest = acc.latest_verdict if acc else None
        if latest != rule.requires_verdict:
            raise TransitionError(
                f"{action} refused: requires latest verdict {rule.requires_verdict!r}, "
                f"node's latest verdict is {latest!r}"
            )

    prior_gate1 = acc.fix_cycle_gate1 if acc else 0
    prior_gate2 = acc.fix_cycle_gate2 if acc else 0
    resulting_fix_cycle = prior_gate1 if action != _GATE2_FIX else prior_gate2

    if rule.bounded_by_fix_cycle:
        prior = prior_gate1 if action == _GATE1_FIX else prior_gate2
        if prior >= MAX_FIX_CYCLES_PER_GATE:
            raise QuarantineRequired(
                f"{action} refused: gate fix cycles exhausted "
                f"({prior}/{MAX_FIX_CYCLES_PER_GATE}) — QUARANTINE instead"
            )
        resulting_fix_cycle = prior + 1

    if rule.requires_verdict is None and event_verdict is not None and action.startswith("REVIEW"):
        # REVIEW_* records a verdict; it's carried on the event, not a precondition.
        pass

    sequence = (acc.last_sequence if acc else 0) + 1
    return ResolvedTransition(
        rule=rule,
        from_state=from_state,
        to_state=rule.to_state,
        sequence=sequence,
        fix_cycle=resulting_fix_cycle,
    )


# ---------------------------------------------------------------------------
# Read / append / rebuild
# ---------------------------------------------------------------------------

def read_events(root: Path) -> list[Event]:
    """Parse the append-only JSONL event log into typed events."""
    path = workspace.ledger_path(root)
    if not path.is_file():
        return []
    events: list[Event] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            events.append(_EVENT_ADAPTER.validate_json(line))
    return events


def append_event(root: Path, event: Event) -> None:
    """Append one validated event as a canonical JSONL line + fsync.

    Assumes the caller holds ``workspace.ledger_lock``. The line bytes are
    produced by ``canonical_json.canonical_bytes`` (sorted keys, UTF-8, one
    trailing newline) so the log is byte-reproducible.
    """
    payload = _EVENT_ADAPTER.dump_python(event, mode="json", exclude_none=False)
    workspace.append_bytes_fsync(workspace.ledger_path(root), canonical_json.canonical_bytes(payload))


def rebuild_manifest(root: Path) -> LedgerManifest:
    """Fold the log and atomically rewrite ``manifest.json``."""
    manifest = fold(read_events(root))
    payload = manifest.model_dump(mode="json", exclude_none=False)
    workspace.atomic_write_bytes(workspace.manifest_path(root), canonical_json.canonical_bytes(payload))
    return manifest
