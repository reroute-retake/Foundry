# Decision Register

This register records **ratified judgment calls** — design decisions made during the
implementation-readiness reviews (2026-07-07) that sit *below* ADR level but shape
contracts and code. Each entry was explicitly approved by the project owner. ADRs
remain the authority for architectural decisions; if an entry here is ever contested,
promote it to an ADR rather than silently changing it (AGENTS.md, ADR-Change Rule).

**Status legend:** ✅ enforced by schema/validator/CI · 📄 documented in repo docs ·
📝 recorded here (and in commit messages) only · ⏳ open work item.

Commits referenced: `11f9701`, `f98d7d4`, `b8daa4a`, `39bd5b6`, `84d0aa8`, `6efc371`,
`6c11300`, `67f3fdb`.

## 1. Classification & Taxonomy

| # | Decision & rationale | Status / enforcement |
| --- | --- | --- |
| 1 | **One canonical evaluation order everywhere** (entropy order, Attack Vector → Concept). `docs/taxonomy.md` was reordered rather than kept divergent with a disclaimer — two orders with a footnote is exactly the trap that inverts the decision tree. `schemas/discoverer_schema.py` is the machine source of truth. | ✅ CI parses both markdown listings and asserts equality with `TaxonomyLevel` (`tests/test_adr_compliance.py`) |
| 2 | **Static structural defenses (e.g., Bulkhead) classify as Pattern, not Mitigation.** Strict Axiom 2 reading: Mitigation requires a dynamic threat/load/failure signal consumed at runtime; widening it to static defenses would erode the axiom's crispness. | 📄 `docs/classification-predicates.md`, Level 2 defer clause |
| 3 | **Dual-nature entities lock early by sequential order** (gRPC = Interface at Level 7, never Tool). The order *is* the tie-break by design; the Discoverer must not deliberate beyond the predicates. | 📄 predicates doc, Global Rule 5 |
| 4 | **Concept is a terminal accumulator.** Any genuine technical entity surviving Levels 1–9 lands there; entity-ness is filtered upstream during entity isolation. `ClassificationResult` deliberately has no "not an entity" escape. | 📄 predicates doc, Level 10 |

## 2. Pipeline Ledger

| # | Decision & rationale | Status / enforcement |
| --- | --- | --- |
| 5 | **Gate reviews are executed by Tier 2 scripts** invoking the reviewer model as a tool-less structured-output API call. A Tier 1 agent (`[read, search]`) cannot persist its own Review Report; this resolves the impossibility while making "Reviewer cannot rewrite" absolute (zero tools). | 📄 `docs/pipeline-ledger.md` §3 |
| 6 | **`MAX_FIX_CYCLES_PER_GATE = 2`, then QUARANTINE.** Fixes always re-review before promotion — no AI content reaches Canonical without frontier validation, and no unbounded loops (constitution: "Not an Agentic Loop"). | ✅ schema constant + `TRANSITION_RULES`; invariant tests |
| 7 | **Promotions emit net-new artifact copies** even when content is unchanged — uniform ADR 002 beats a storage-thrift special case. | 📄 pipeline-ledger.md §1/§5 |
| 8 | **Strict `VALIDATED → LINKED → ENRICHED` order.** Enrichment reads edges (`ontology.md`); no Pass-2 parallelism in v1 despite ADR 008's "asynchronous" wording. | ✅ `TRANSITION_RULES` preconditions |
| 9 | **Post-canonical re-ingestion is deferred to v2.** New source material touching a CANONICAL node re-enters via the revision lineage, which already supports it — no redesign needed later. | 📄 pipeline-ledger.md §5 |
| 10 | **Events are canonical; state is derived.** `ledger.jsonl` is the append-only source of truth; `manifest.json` is a rebuildable fold — same doctrine as ADR 014's derived datastores. | 📄 pipeline-ledger.md §1; ✅ `LedgerManifest.folded_through_event_id` |
| 11 | **`RELEASE` is excluded from the static rules table.** Its target state is dynamic (any state in the node's own history), operator-chosen with a mandatory note; the release script enforces history membership. | ✅ schema comment + `tests/test_pipeline_ledger.py` |
| 12 | **`GhostStub` is a distinct minimal schema, deliberately NOT a `BaseNode`** — a stub cannot satisfy BaseNode's required fields; forcing it would corrupt the ontology. | ✅ `schemas/pipeline_ledger.py` |

## 3. Review Contract

| # | Decision & rationale | Status / enforcement |
| --- | --- | --- |
| 13 | **Gate-discriminated ReviewReport union with closed, gate-specific flaw vocabularies** (8 categories each; no `"other"`). Needing a new category means changing the schema, not drifting. | ✅ `schemas/review.py` discriminated union |
| 14 | **Verdict is enforced, not chosen:** `fail` iff any critical/major flaw; duplicate `flaw_id`s rejected. The reviewer model cannot emit an inconsistent report. | ✅ `model_validator` + tests |
| 15 | **Severity triad** critical / major / minor; minors never block promotion alone. | 📄 review.py comments; ✅ via #14 |
| 16 | **Reports pin the reviewed artifact by `reviewed_revision` + `reviewed_sha256`** — no ambiguity about what the Fixer must resolve (ADR 002). | ✅ required fields |
| 17 | **`fix_instruction` must not contain full replacement text.** The Reviewer critiques and sets acceptance criteria; authorship belongs to the Fixer. | 📄 field description (prompt-enforced; Gate script may add lexical checks later) |
| 18 | **`StrictModel` base; `extra='forbid'` on every model, no exceptions** — extended beyond the payloads to Edge, SourceRef, and the discoverer models when the gap was found. | ✅ AGENTS.md rule 9 + universal CI guard (`test_every_model_forbids_extra_fields`) |

## 4. Pass-2 Content (Enrichment & MOC)

| # | Decision & rationale | Status / enforcement |
| --- | --- | --- |
| 19 | **`EnrichedNode` is a composition wrapper `{base, enrichment}`**, not new fields on node classes. Pass-1 schema stays physically untouched (ADR 008 by construction), and the ontology-drift check reduces to a hash comparison of the `base` subtree. | ✅ `schemas/enrichment.py`; base-integrity test |
| 20 | **At least one flashcard required per enriched node.** Retention is the product; a node yielding zero cards is a pipeline smell. | ✅ `min_length=1` |
| 21 | **Analogies must state their `limitations`.** Every analogy misleads somewhere; requiring the breakdown point gives Gate 2's `analogy_inaccuracy` review something concrete. | ✅ required field |
| 22 | **Cloze semantics enforced in-schema:** cloze cards must omit `back` and contain `{{c…}}` markup; basic/reversed require `back`. | ✅ `model_validator` |
| 23 | **Mermaid first-token guard** (closed diagram-type keyword set, `%%` directives allowed). Catches prose-instead-of-code cheaply; deep correctness remains Gate 2's `diagram_error`. | ✅ `field_validator` |
| 24 | **350-character straitjacket caps** on card faces, captions, analogies, and MOC narratives/annotations — mirroring `core_definition`'s cap. | ✅ `max_length=350` |
| 25 | **No `model_id` inside enrichment content.** The ledger's `ActorRef` owns audit. Contrast: ReviewReport *does* carry `reviewer_model_id`, because the critic's identity is part of that document's meaning. | 📝 this register |
| 26 | **MOC consistency rules:** `learning_sequence` ids must be unique and present in section entries; sections must be non-empty. MOCs may carry brief connective narrative — they are structure notes organizing atomic notes, so ADR 005 applies differently. | ✅ validators in `schemas/moc.py`; 📄 docstring |
| 27 | **Curation-phase ledger events deferred.** MOC artifacts have no `ArtifactKind`/event in the ledger yet; belongs with Phase-8 sequencing design. | ⏳ open work item |

## 5. Provenance (Discoverer → Author)

| # | Decision & rationale | Status / enforcement |
| --- | --- | --- |
| 28 | **The LLM emits language; the script emits facts.** `evidence_quote` (a verbatim snippet the script substring-verifies against the chunk) is the only LLM-produced provenance; `document_id`/`chunk_span` are known deterministically by the script that chose the chunk. `TopicMetadata` composes them — a `SourceRef` inside the constrained-decoding schema would invite hallucinated spans. | ✅ `schemas/discoverer_schema.py`; 📄 docstrings |
| 29 | **Quote-equality validator:** `provenance.quotation_snippet == classification.evidence_quote`. The handoff cannot silently carry an unverified quote. | ✅ `model_validator` + test |
| 30 | **snake_case pattern enforced on `BaseNode.canonical_id` and `TopicMetadata.canonical_id` only** — the two artifact anchors, so ids cannot drift between DISCOVER and DRAFT. Deliberately NOT extended to `Edge.target_canonical_id`, `GhostStub`, or `MocEntry`: referential integrity there is the scripts' job against the ledger. | ✅ `pattern=` on both anchors; scope 📝 this register |

## 6. Build & Tooling

| # | Decision & rationale | Status / enforcement |
| --- | --- | --- |
| 31 | **MIT license** under "reroute-retake"; **Python ≥ 3.12**; **pydantic `>=2.13,<3`**. | ✅ LICENSE / pyproject |
| 32 | **Heavy pipeline dependencies deliberately unpinned** pending the extractor benchmark and constrained-decoding spike. `Private :: Do Not Upload` classifier and `uv package = false` guard against accidental publish/build. | 📄 pyproject comments |
| 33 | **AGENTS.md is kept deliberately dense** (constraint one-liners + pointers, ~110 lines) because ForgeCode injects it into every session — context cost is a design constraint, and depth lives in the documents it references. | 📝 this register |
| 34 | **Lint/type configuration:** ruff `UP` rules dropped (schemas intentionally use `typing.List`-style annotations for wide runtime compatibility) and `E501` ignored (long Field descriptions are the straitjacket's documentation); mypy runs strict with the pydantic plugin. | ✅ pyproject; rationale 📝 this register |
| 35 | **ADR-compliance guards run as CI tests**: docs↔schema order parsing (#1), universal `extra='forbid'` (#18), AST scan blocking LLM-client imports in extraction code (ADR 003), and `.skills-data/` gitignore hygiene (ADR 013). Architectural rules fail the build, not the code review. | ✅ `tests/test_adr_compliance.py` + `.github/workflows/ci.yml` |
