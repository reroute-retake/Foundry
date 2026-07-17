"""Discoverer: Extracted Text → Topic Metadata (first LLM stage, Phase 3).

"LLMs emit language; scripts emit facts." The LLM returns ONLY
``ClassificationResult`` objects (register #39: provider-side JSON-schema
structured output — server-side constrained decoding satisfying ADR 011's
mechanism). This script owns everything factual: chunking, prompts assembled
at runtime from ``docs/`` (no duplicated copies to drift), evidence-quote
verification with SOURCE-span recovery (register #36/#43), slugified
``canonical_id``s, ``TopicMetadata`` assembly, and every ledger transition
(``DISCOVER``, including GHOST reification) via the write protocol.

Bounded by construction: at most ``MAX_ATTEMPTS`` LLM calls per chunk, then
the chunk is skipped and recorded in the discovery-failures report — never an
unbounded loop (constitution: "Not an Agentic Loop").

Configuration (environment, optionally from ``<repo>/.env`` — see .env.example):
    FOUNDRY_DISCOVERER_BASE_URL   OpenAI-compatible base URL (register #47)
    FOUNDRY_DISCOVERER_API_KEY    the prepaid, hard-capped key
    FOUNDRY_DISCOVERER_MODEL     model id (default: grok-4.3)

Usage:
    python3 skills/foundry-discover/scripts/run_discover.py <document_id> [--max-chunks N]
"""

import argparse
import json
import os
import sys
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import _bootstrap
from pydantic import BaseModel, ConfigDict

import canonical_json
import ledger
import workspace
from discoverer_schema import ClassificationResult, TopicMetadata, normalize_quote
from pipeline_ledger import ActorRef, ArtifactRef, NodeTransitionEvent
from taxonomy import SourceRef

MAX_ATTEMPTS = 3  # 1 initial + 2 retries per chunk (implementation plan, Phase 3)
RETRY_SLEEP_SECONDS = 1.0
MIN_CHUNK_CHARS = 80  # headings-only / whitespace stubs are not classifiable
_ACTOR_ROLE = "Discoverer"

# Prompt sources — loaded from docs/ at runtime so nothing drifts (Phase 3 rule).
_PROMPT_DOCS = ("docs/taxonomy.md", "docs/classification-predicates.md",
                "docs/classification-axioms.md")


class DiscoveryBatch(BaseModel):
    """LLM-facing request schema (register #44 pattern: a separate, flat,
    script-owned model — the committed contracts are never mutated at runtime).
    One chunk may ground several distinct entities."""
    model_config = ConfigDict(extra="forbid")

    entities: List[ClassificationResult]


@dataclass
class Config:
    base_url: str
    api_key: str
    model: str
    timeout_seconds: float = 120.0


@dataclass
class Chunk:
    index: int
    start: int  # character offset in the extracted document
    text: str


@dataclass
class Summary:
    chunks_total: int = 0
    chunks_processed: int = 0
    discovered: int = 0
    reified_ghosts: int = 0
    duplicates: int = 0
    failed_chunks: int = 0
    failure_report: Optional[str] = None
    discovered_ids: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def _load_dotenv(code_root: Path) -> None:
    """Minimal KEY=VALUE loader for <repo>/.env; real env vars win. No new deps."""
    env_file = code_root / ".env"
    if not env_file.is_file():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_config(code_root: Path) -> Config:
    _load_dotenv(code_root)
    base_url = os.environ.get("FOUNDRY_DISCOVERER_BASE_URL", "").rstrip("/")
    api_key = os.environ.get("FOUNDRY_DISCOVERER_API_KEY", "")
    if not base_url or not api_key:
        raise RuntimeError(
            "FOUNDRY_DISCOVERER_BASE_URL and FOUNDRY_DISCOVERER_API_KEY are required "
            "(register #47; see .env.example)"
        )
    return Config(base_url=base_url, api_key=api_key,
                  model=os.environ.get("FOUNDRY_DISCOVERER_MODEL", "grok-4.3"))


# ---------------------------------------------------------------------------
# Deterministic pieces: chunking, slugify, prompt assembly
# ---------------------------------------------------------------------------

def chunk_markdown(text: str, min_chars: int = MIN_CHUNK_CHARS) -> List[Chunk]:
    """v1 chunking: one chunk per markdown heading section (deliberately simple;
    revisit with Phase 7 metrics)."""
    boundaries = [0]
    offset = 0
    for line in text.splitlines(keepends=True):
        if line.startswith("#") and offset != 0:
            boundaries.append(offset)
        offset += len(line)
    boundaries.append(len(text))

    chunks: List[Chunk] = []
    for start, end in zip(boundaries[:-1], boundaries[1:], strict=True):
        piece = text[start:end]
        if len(piece.strip()) >= min_chars:
            chunks.append(Chunk(index=len(chunks), start=start, text=piece))
    return chunks


def slugify(name: str) -> str:
    """extracted_entity_name → canonical_id (pattern ^[a-z][a-z0-9_]*$, ≤64)."""
    import re

    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    if slug and slug[0].isdigit():
        slug = f"n{slug}"  # ids must start with a letter; deterministic prefix
    slug = slug[:64].rstrip("_")
    if not re.fullmatch(r"[a-z][a-z0-9_]*", slug or ""):
        raise ValueError(f"cannot slugify entity name {name!r} into a canonical_id")
    return slug


def build_system_prompt(code_root: Path) -> str:
    sections = []
    for relative in _PROMPT_DOCS:
        path = code_root / relative
        sections.append(f"<<<{relative}>>>\n{path.read_text(encoding='utf-8')}")
    corpus = "\n\n".join(sections)
    return (
        "You are the Foundry Discoverer. From the supplied markdown chunk, identify "
        "every distinct technical entity worth an atomic knowledge node, and classify "
        "each one by walking the canonical taxonomy order SEQUENTIALLY — the first "
        "level whose entry predicate is TRUE locks the classification. Apply the "
        "reference material below exactly; it is the sole authority.\n\n"
        f"{corpus}\n\n"
        "Rules:\n"
        "- For each entity, write the sequential evaluation trace BEFORE the verdict.\n"
        "- evidence_quote MUST be copied verbatim from the chunk (a contiguous span, "
        "≤350 characters) that grounds the entity. Do not paraphrase.\n"
        "- Do not invent entities that the chunk does not substantively discuss.\n"
        "- Emit JSON matching the provided schema exactly."
    )


# ---------------------------------------------------------------------------
# Evidence-quote → source-span recovery (register #36/#43)
# ---------------------------------------------------------------------------

def _indexed_locator_stream(text: str) -> tuple[str, List[int]]:
    """Aggressive lowercase-alnum stream WITH source indices, link-labels only.

    This is a LOCATOR heuristic — acceptance always goes through the schema's
    conservative ``normalize_quote`` oracle, so locator/oracle drift cannot
    corrupt provenance (discoverer_schema.normalize_quote docstring)."""
    import re
    import unicodedata

    stream: List[str] = []
    indices: List[int] = []
    link = re.compile(r"\[([^\]]*)\]\([^)]*\)")
    pieces: List[tuple[str, int]] = []
    cursor = 0
    for match in link.finditer(text):
        pieces.append((text[cursor:match.start()], cursor))
        pieces.append((match.group(1), match.start(1)))
        cursor = match.end()
    pieces.append((text[cursor:], cursor))

    for segment, base in pieces:
        for i, char in enumerate(segment):
            for folded in unicodedata.normalize("NFKC", char).lower():
                if folded.isalnum():
                    stream.append(folded)
                    indices.append(base + i)
    return "".join(stream), indices


def recover_span(chunk_text: str, quote: str) -> Optional[tuple[str, int, int]]:
    """Find the SOURCE span whose normalize_quote equals the quote's.

    Returns (recovered_source_text, start, end) with chunk-relative offsets,
    or None when the quote cannot be grounded (weak grounding → LLM retry)."""
    target = normalize_quote(quote)
    if not target:
        return None

    # Tier 1: the quote already appears verbatim.
    literal = chunk_text.find(quote)
    if literal != -1:
        return quote, literal, literal + len(quote)

    # Tier 2: aggressive locator stream, then oracle-verified boundary search.
    quote_stream, _ = _indexed_locator_stream(quote)
    chunk_stream, index_map = _indexed_locator_stream(chunk_text)
    if not quote_stream:
        return None
    at = chunk_stream.find(quote_stream)
    if at == -1:
        return None
    core_start = index_map[at]
    core_end = index_map[at + len(quote_stream) - 1] + 1

    for start_delta in range(0, 9):
        start = max(0, core_start - start_delta)
        for end_delta in range(0, 13):
            end = min(len(chunk_text), core_end + end_delta)
            candidate = chunk_text[start:end].strip()
            if candidate and normalize_quote(candidate) == target:
                begin = start + chunk_text[start:end].index(candidate[0]) if candidate else start
                return candidate, begin, begin + len(candidate)
    return None


# ---------------------------------------------------------------------------
# LLM transport (injectable seam: tests replace ``TRANSPORT``)
# ---------------------------------------------------------------------------

def _http_transport(config: Config, system_prompt: str, user_prompt: str) -> str:
    """POST an OpenAI-compatible chat completion with strict JSON-schema output.

    stdlib-only on purpose: pyproject defers heavy dependencies, and the stable
    interface here is exactly what lets a local vLLM endpoint swap in behind
    FOUNDRY_DISCOVERER_BASE_URL with zero script changes (register #39/#47)."""
    body = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "discovery_batch",
                "strict": True,
                "schema": DiscoveryBatch.model_json_schema(),
            },
        },
    }
    request = urllib.request.Request(
        f"{config.base_url}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=config.timeout_seconds) as response:
        payload = json.loads(response.read().decode("utf-8"))
    content = payload["choices"][0]["message"]["content"]
    if not isinstance(content, str):
        raise RuntimeError("provider returned non-text content")
    return content


TRANSPORT = _http_transport


def classify_chunk(config: Config, system_prompt: str, chunk: Chunk) -> DiscoveryBatch:
    raw = TRANSPORT(config, system_prompt, chunk.text)
    return DiscoveryBatch.model_validate_json(raw)


# ---------------------------------------------------------------------------
# Ledger commit (write protocol) and failure reporting
# ---------------------------------------------------------------------------

def _commit_topic(root: Path, document_id: str, chunk: Chunk, config: Config,
                  entity: ClassificationResult, span: tuple[str, int, int],
                  summary: Summary) -> None:
    recovered, rel_start, rel_end = span
    canonical_id = slugify(entity.extracted_entity_name)
    metadata = TopicMetadata(
        canonical_id=canonical_id,
        classification=entity,
        provenance=SourceRef(
            document_id=document_id,
            chunk_span=f"chars:{chunk.start + rel_start}-{chunk.start + rel_end}",
            quotation_snippet=recovered,
        ),
    )

    with workspace.ledger_lock(root):
        events = ledger.read_events(root)
        try:
            resolved = ledger.validate_node_transition(
                events, "DISCOVER", canonical_id, document_extracted=True
            )
        except ledger.TransitionError:
            summary.duplicates += 1  # already discovered (or beyond) — benign dedupe
            return
        payload = metadata.model_dump(mode="json")
        data = canonical_json.canonical_bytes(payload)
        destination = workspace.artifact_path(root, canonical_id, resolved.sequence, "topic_metadata")
        workspace.atomic_write_bytes(destination, data)
        event = NodeTransitionEvent(
            event_id=ledger.new_ulid(),
            canonical_id=canonical_id,
            sequence=resolved.sequence,
            action="DISCOVER",
            from_state=resolved.from_state,
            to_state=resolved.to_state,
            actor=ActorRef(role=_ACTOR_ROLE, execution="tier2_script", model_id=config.model),
            produced=[ArtifactRef(
                kind="topic_metadata",
                path=workspace.relative_to_skills_data(root, destination),
                revision=resolved.sequence,
                sha256=canonical_json.sha256_of_bytes(data),
            )],
            occurred_at=ledger.utc_now_iso(),
        )
        ledger.append_event(root, event)
        ledger.rebuild_manifest(root)

    summary.discovered += 1
    summary.discovered_ids.append(canonical_id)
    if resolved.from_state == "GHOST":
        summary.reified_ghosts += 1


def _report_failure(root: Path, document_id: str, chunk: Chunk, errors: List[str]) -> str:
    report = workspace.pipeline_dir(root) / "discovery-failures.jsonl"
    line = canonical_json.canonical_bytes({
        "document_id": document_id,
        "chunk_index": chunk.index,
        "chunk_start": chunk.start,
        "attempts": MAX_ATTEMPTS,
        "errors": errors[-MAX_ATTEMPTS:],
        "occurred_at": ledger.utc_now_iso(),
    })
    with workspace.ledger_lock(root):
        workspace.append_bytes_fsync(report, line)
    return workspace.relative_to_skills_data(root, report)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def discover_document(root: Path, code_root: Path, document_id: str, config: Config,
                      max_chunks: Optional[int] = None) -> Summary:
    with workspace.ledger_lock(root):
        manifest = ledger.fold(ledger.read_events(root))
    entry = manifest.documents.get(document_id)
    if entry is None or not entry.extracted or entry.extracted_text is None:
        raise RuntimeError(f"document {document_id!r} is not EXTRACTED — run foundry-ingest first")

    artifact = workspace.skills_data_dir(root) / entry.extracted_text.path
    if canonical_json.sha256_of_file(artifact) != entry.extracted_text.sha256:
        raise RuntimeError("extracted_text artifact hash mismatch — ledger integrity violated")
    text = artifact.read_text(encoding="utf-8")

    system_prompt = build_system_prompt(code_root)
    chunks = chunk_markdown(text)
    if max_chunks is not None:
        chunks = chunks[:max_chunks]

    summary = Summary(chunks_total=len(chunks))
    for chunk in chunks:
        errors: List[str] = []
        done = False
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                batch = classify_chunk(config, system_prompt, chunk)
            except Exception as exc:  # noqa: BLE001 — every failure becomes a bounded retry
                errors.append(f"attempt {attempt}: LLM/schema failure: {exc}")
                time.sleep(RETRY_SLEEP_SECONDS * (attempt - 1))
                continue

            unrecovered: List[str] = []
            for entity in batch.entities:
                span = recover_span(chunk.text, entity.evidence_quote)
                if span is None:
                    unrecovered.append(entity.extracted_entity_name)
                    continue
                try:
                    _commit_topic(root, document_id, chunk, config, entity, span, summary)
                except (ValueError, ledger.LedgerError) as exc:
                    unrecovered.append(f"{entity.extracted_entity_name} ({exc})")
            if unrecovered:
                errors.append(
                    f"attempt {attempt}: quote/commit failures: {', '.join(unrecovered)}"
                )
                time.sleep(RETRY_SLEEP_SECONDS * (attempt - 1))
                continue
            done = True
            break
        summary.chunks_processed += 1
        if not done:
            summary.failed_chunks += 1
            summary.failure_report = _report_failure(root, document_id, chunk, errors)
    return summary


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("document_id", help="an EXTRACTED document id (see foundry-status)")
    parser.add_argument("--max-chunks", type=int, default=None,
                        help="process only the first N chunks (operator spot-check)")
    args = parser.parse_args(argv)

    code_root = _bootstrap.code_root()
    root = _bootstrap.data_root()
    try:
        config = load_config(code_root)
        summary = discover_document(root, code_root, args.document_id, config,
                                    max_chunks=args.max_chunks)
    except RuntimeError as exc:
        print(json.dumps({"ok": False, "error": "DISCOVER_ABORTED", "message": str(exc)}),
              file=sys.stderr)
        return 1

    print(json.dumps({
        "ok": summary.failed_chunks == 0,
        "action": "DISCOVER",
        "document_id": args.document_id,
        "chunks": summary.chunks_total,
        "discovered": summary.discovered,
        "reified_ghosts": summary.reified_ghosts,
        "duplicates": summary.duplicates,
        "failed_chunks": summary.failed_chunks,
        "failure_report": summary.failure_report,
        "discovered_ids": summary.discovered_ids,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
