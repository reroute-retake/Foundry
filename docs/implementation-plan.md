# Implementation Plan — Walking Skeleton (v1)

**Status:** adopted 2026-07-07 · **Scope:** ADR 017 v1 (human-triggered) pipeline from
Source Material through Gate 1 (`VALIDATED`), for one real markdown chapter.
**Out of scope (deferred):** Pass 2 (LINK/ENRICH/Gate 2), Curation, Rendering,
Neo4j/Qdrant/MCP, the headless driver, the extractor benchmark, the eval harness.

Everything below builds against contracts that already exist and are CI-guarded:
`schemas/` (6 modules, 100 tests), `docs/pipeline-ledger.md` (write protocol),
`AGENTS.md` (binding rules), `docs/decision-register.md` (38+ ratified decisions).

## Kickoff Decisions (adopted for this plan — register #39, #40)

1. **Day-1 Discoverer backend = frontier structured-output API** behind a stable
   script interface (`run_discover.py` + OpenAI-compatible base-URL configuration).
   Provider JSON-schema modes are server-side constrained decoding, satisfying
   ADR 011's *mechanism*; a local vLLM/Outlines endpoint slots in behind the same
   interface after the (parallel, non-blocking) serving spike.
2. **Skeleton source = a markdown chapter** (no PDF). Phase-1 extraction becomes a
   deterministic copy + hash, sidestepping the Marker/Docling benchmark until real
   PDFs enter. Source files live under `works/` (gitignored).

## Guiding rules for every phase

- Every mutation flows through the ledger write protocol (flock → validate against
  `TRANSITION_RULES` → artifacts + sha256 → append event + fsync → manifest rename).
- "LLMs emit language; scripts emit facts" — scripts assemble ids, provenance, and
  ledger state; LLMs only ever return schema-validated content payloads.
- Each phase ends green: `ruff check .`, `mypy`, `pytest -q`, CI on push.
- Deviations from ADRs or register entries stop work and go through the
  ADR-Change Rule (AGENTS.md) — never silently.

---

## Phase 0 — Operator pre-flight (user's machine, ~1 hour)

| Task | Detail |
| --- | --- |
| Install ForgeCode | `curl -fsSL https://forgecode.dev/cli \| sh`; run `forge --version` |
| Pin the version | Record in README ("ForgeCode version") and AGENTS.md (ADR 016 requirement) |
| Verify tool ids | Run `:tools`; record exact ids (settles the `search` vs `sem_search` note in ADR 012 / AGENTS.md rule 11) |
| Provider access | `:login`; confirm a frontier key (Anthropic or OpenRouter) works — needed for Reviewer and day-1 Discoverer |
| Choose the chapter | One markdown chapter placed under `works/sources/` |

**Exit:** version pinned in-repo; tool ids recorded; API call succeeds; source file staged.

## Phase 1 — Ledger core library (`core/`)

New top-level `core/` directory (same bare-module convention as `schemas/`;
`pythonpath` and mypy `files` extended accordingly).

| Module | Responsibility |
| --- | --- |
| `core/canonical_json.py` | Pinned deterministic serialization (sorted keys, UTF-8, `\n`, fixed separators) + sha256 helpers — hashes must be reproducible or the immutability witness is worthless |
| `core/workspace.py` | Repo-root/`.skills-data/` path resolution (ADR 013), atomic write (temp + rename), flock context manager |
| `core/ledger.py` | `append_event()`, `fold()` / `rebuild_manifest()`, `validate_transition()` (state, verdict, fix-cycle, document-extracted preconditions), per-node sequence, ULID generation (pure-python, no new dependency) |
| `core/status.py` | Per-batch ledger report (what's next / what's blocked — ADR 017's `status`) |

**Tests:** simulated 3-node lifecycle walk; out-of-order refusal; quarantine on cycle
exhaustion; crash-safety (event appended, manifest stale → rebuild equals fold);
hash reproducibility.

**Exit:** all gates green; a scripted lifecycle walk in tests reaches `VALIDATED`
via ledger calls only.

## Phase 2 — Deterministic skills: ingest + status

`.forge/skills/foundry-ingest/` (`SKILL.md` + `scripts/register_document.py`,
`scripts/extract_document.py`) and `.forge/skills/foundry-status/`.

- v1 extractor = markdown identity transform (copy + hash), emitting `REGISTER` and
  `EXTRACT` DocumentEvents and the `extracted_text` artifact.
- Skill definitions stay immutable (ADR 013); all outputs land in `.skills-data/`.

**Exit:** `register` + `extract` on the real chapter produce correct ledger entries
and artifacts; `status` reports the document as extracted.

## Phase 3 — Discoverer skill (first LLM stage)

`.forge/skills/foundry-discover/` — `scripts/run_discover.py`:

1. Chunk the Extracted Text (v1: markdown-section chunks).
2. Call the structured-output endpoint with the `ClassificationResult` schema; prompt
   embeds the canonical order, level predicates, and axioms as minimal pairs
   (loaded from `docs/` at runtime — no duplicated copies to drift).
3. Verify `evidence_quote` via `normalize_quote()` matching; **recover the source
   span** and store it in `provenance.quotation_snippet` (register #36).
4. Slugify → `canonical_id`; assemble `TopicMetadata`; execute `DISCOVER`
   transitions (including `GHOST` reification when applicable).
5. Bounded retries per chunk (2), then skip + append to a discovery-failures report —
   never an unbounded loop.

Configuration via env (`FOUNDRY_DISCOVERER_BASE_URL`, provider key); add
`.env.example`.

**Tests:** mocked LLM fixtures — quote recovery (typographic divergence), slugify,
ghost reification, retry/skip path, ledger effects.

**Exit:** the real chapter yields `DISCOVERED` nodes with valid TopicMetadata;
classification spot-check by the Operator looks sane.

## Phase 4 — Author skill (second LLM stage)

`.forge/skills/foundry-draft/` — `scripts/run_draft.py`:

- **Per-kind schema selection:** `primary_kind` is already decided by Discovery, so
  the Author is constrained to the *specific* node schema for that kind — smaller
  grammar, no discriminated-union support required from the provider.
- The LLM emits title/aliases/definition/context/payload only; the **script**
  assembles `canonical_id` and `provenance` from TopicMetadata (emit-language
  principle again).
- Edges must be empty at DRAFT (Pass 1 — ADR 008); script rejects otherwise.

**Exit:** `DISCOVERED → DRAFTED` with schema-valid `knowledge_draft` revisions for
the chapter's nodes.

## Phase 5 — Gate 1: review, fix, promote (third LLM stage)

`.forge/skills/foundry-gate1/` — three scripts per `docs/pipeline-ledger.md` §3:

- `run_review_base.py`: frontier model as a tool-less structured-output call against
  the `OntologyReviewReport` schema; persist report; record verdict.
- `run_promote_base.py`: verdict `pass` → `VALIDATED` (net-new artifact, register #7).
- `run_fix_base.py`: verdict `fail` → Fixer LLM (per-kind schema) consumes report +
  draft → new draft revision; cycle counters; `QUARANTINE` on exhaustion; re-review
  is Operator-triggered (ADR 017 v1).

**Exit:** a full Gate-1 cycle observed on real nodes — ideally at least one
fail → fix → re-review → pass, and one first-pass promotion.

## Phase 6 — Agents, runbook, guardrail bootstrap

- `.forge/agents/`: `conductor.md` (Tier 1 — closes the glossary's forward
  pointer), `discoverer.md`, `author.md`, `fixer.md` (Tier 2), `reviewer.md`
  (Tier 1, exploratory only — formal gate stays script-mediated). Frontmatter uses
  the tool ids verified in Phase 0, plus bounded-loop settings.
- `docs/runbook.md`: the Operator's step-by-step for one batch (the ~9 commands).
- `permissions.yaml` bootstrap spec (documented contents + install step; restricted
  mode optional for interactive v1).
- AGENTS.md: fill the verified tool ids; add the runbook pointer.

**Exit:** the full skeleton driven end-to-end from an interactive ForgeCode session
using the agent definitions.

## Phase 7 — Acceptance run + retrospective

- Run the entire chapter end-to-end; capture: node count, kind distribution,
  gate pass rate, fix-cycle counts, token cost, wall time.
- Verify invariants held: `fold(ledger) == manifest`, no direct `.skills-data/`
  writes outside scripts, CI green throughout.
- Record findings in the decision register; choose the next milestone
  (Pass 2 vs. local-serving spike vs. eval set) based on observed weaknesses.

**Skeleton Definition of Done:** one real chapter's nodes reach `VALIDATED` with a
clean, replayable ledger; every guard (schemas, tier scoping, ADR-compliance CI)
held without manual overrides.

---

## Dependencies & parallelism

Phases 1 → 2 → 3 → 4 → 5 are sequential (each consumes the previous state).
Phase 6 agent files can be drafted alongside Phases 3–5. The local-serving spike
(vLLM/Outlines) may run any time in parallel and swaps in behind
`FOUNDRY_DISCOVERER_BASE_URL` with zero script changes.

## Risks & mitigations

| Risk | Mitigation |
| --- | --- |
| Provider structured-output limits on complex schemas | Per-kind schema selection (Phase 4) keeps grammars small; ClassificationResult is flat |
| Evidence-quote recovery failure rate | Bounded retries + discovery-failures report; failures are data for the eval set |
| Chunking quality drives classification quality | v1 section-based chunking is deliberately simple; revisit with Phase 7 metrics |
| ForgeCode tool-id mismatch in agent frontmatter | Resolved in Phase 0 before any agent file is written |
| Cost of frontier gates | Skeleton is one chapter (~tens of nodes); Phase 7 captures the real number before scaling |

## Session bootstrap (read this first tomorrow)

1. Read `AGENTS.md`, then this plan, then `docs/pipeline-ledger.md` §3–4.
2. Confirm Phase 0 is complete (version pinned, tool ids recorded, key working).
3. Work proceeds phase-by-phase via the established loop: propose → review → gates
   (`ruff` / `mypy` / `pytest`) green locally → commit → CI green.
4. New design decisions go to `docs/decision-register.md`; ADR deviations go through
   the ADR-Change Rule. No exceptions — that discipline is why this repo is safe to
   implement with LLMs.
