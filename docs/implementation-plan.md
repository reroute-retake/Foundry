# Implementation Plan — Walking Skeleton (v1)

**Status:** adopted 2026-07-07 · **Scope:** ADR 017 v1 (human-triggered) pipeline from
Source Material through Gate 1 (`VALIDATED`), for one real markdown chapter.
**Out of scope (deferred):** Pass 2 (LINK/ENRICH/Gate 2), Curation, Rendering,
Neo4j/Qdrant/MCP, the headless driver, the extractor benchmark, the eval harness.

Everything below builds against contracts that already exist and are CI-guarded:
`schemas/` (6 modules, 104 tests), `docs/pipeline-ledger.md` (write protocol),
`AGENTS.md` (binding rules), `docs/decision-register.md` (50 ratified decisions).

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

## Phase 0 — Operator pre-flight (user's machine; largely discharged 2026-07-15/16)

| Task | Detail |
| --- | --- |
| Install + pin Hermes | `curl -fsSL https://hermes-agent.nousresearch.com/install.sh \| bash` (`--skip-browser`); pin the **upstream sha** in README (the git installer tracks `main`; `--commit <sha>` for reproducible installs — register #50) |
| Constitutional Bootstrap | Set register #49 config: `approvals.mode manual`, `memory.write_approval`/`skills.write_approval` true, `approvals.deny` globs over `.skills-data/`, local backend |
| Enumerate toolsets | `hermes tools list` + session banner; confirm Tier-2 `-t terminal` and pin the Tier-1 minimal set (AGENTS.md rule 11) |
| Provider access | Two surfaces: (1) harness — `hermes model` → `xai-oauth` (SuperGrok), confirm a chat turn (watch #26847); (2) scripts — set `FOUNDRY_DISCOVERER_BASE_URL=https://api.x.ai/v1` + a prepaid-capped xAI API key (`grok-4.3`), register #47 |
| Choose the chapter | One markdown chapter placed under `works/sources/` |

**Exit:** upstream sha pinned in-repo; bootstrap config set; toolsets recorded; a chat turn succeeds; source file staged. *(Spike status: everything except the `approvals.deny` glob live-test and the Tier-1 minimal set was verified 2026-07-15/16 — see `docs/hermes-migration-plan.md` §12.)*

## Phase 1 — Ledger core library (`core/`)

New top-level `core/` directory (same bare-module convention as `schemas/`;
`pythonpath` and mypy `files` extended accordingly).

| Module | Responsibility |
| --- | --- |
| `core/canonical_json.py` | Pinned deterministic serialization (sorted keys, UTF-8, `\n`, fixed separators) + sha256 helpers — hashes must be reproducible or the immutability witness is worthless |
| `core/workspace.py` | Repo-root/`.skills-data/` path resolution (ADR 013), atomic write (temp + rename), cross-platform lock via `filelock` — fcntl is Unix-only (register #42) |
| `core/ledger.py` | `append_event()`, `fold()` / `rebuild_manifest()`, `validate_transition()` (state, verdict, fix-cycle, document-extracted preconditions), per-node sequence, ULID generation (pure-python, no new dependency) |
| `core/status.py` | Per-batch ledger report (what's next / what's blocked — ADR 017's `status`) |

**Take care (register #41):** the pinned serialization is exactly
`json.dumps(obj, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))`,
explicitly encoded as UTF-8 — never the platform default encoding. One function must
produce the bytes for BOTH the file write and the sha256 (hash-what-you-write; two
serialization paths will drift). The schemas contain no `float` fields — keep it
that way; introducing one requires a register entry (float repr is the other classic
canonicalization hazard).

**Tests:** simulated 3-node lifecycle walk; out-of-order refusal; quarantine on cycle
exhaustion; crash-safety (event appended, manifest stale → rebuild equals fold);
hash reproducibility.

**Exit:** all gates green; a scripted lifecycle walk in tests reaches `VALIDATED`
via ledger calls only.

## Phase 2 — Deterministic skills: ingest + status

`skills/foundry-ingest/` (`SKILL.md` + `scripts/register_document.py`,
`scripts/extract_document.py`) and `skills/foundry-status/`.

- v1 extractor = markdown identity transform (copy + hash), emitting `REGISTER` and
  `EXTRACT` DocumentEvents and the `extracted_text` artifact.
- Skill definitions stay immutable (ADR 013); all outputs land in `.skills-data/`.

**Exit:** `register` + `extract` on the real chapter produce correct ledger entries
and artifacts; `status` reports the document as extracted.

## Phase 3 — Discoverer skill (first LLM stage)

`skills/foundry-discover/` — `scripts/run_discover.py`:

1. Chunk the Extracted Text (v1: markdown-section chunks).
2. Call the structured-output endpoint with the `ClassificationResult` schema; prompt
   embeds the canonical order, level predicates, and axioms as minimal pairs
   (loaded from `docs/` at runtime — no duplicated copies to drift).
3. Verify `evidence_quote` via `normalize_quote()` matching; **recover the source
   span** and store it in `provenance.quotation_snippet` (register #36; the
   normalizer is markdown-aware per #43 — LLMs strip formatting when quoting, and
   the recovered span carries the source's markdown).
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

`skills/foundry-draft/` — `scripts/run_draft.py`:

- **Per-kind schema selection:** `primary_kind` is already decided by Discovery, so
  the Author is constrained to the *specific* node schema for that kind — smaller
  grammar, no discriminated-union support required from the provider.
- The LLM emits title/aliases/definition/context/payload only; the **script**
  assembles `canonical_id` and `provenance` from TopicMetadata (emit-language
  principle again).
- Edges must be empty at DRAFT (Pass 1 — ADR 008); script rejects otherwise.

**Take care (register #44):** never strip fields from the committed models at
runtime. The LLM-facing request schemas are separate, per-kind models containing
only the fields above — `edges` and `provenance` are excluded by construction, the
provider grammar stays small (no Edge/SourceRef `$defs`), and the committed
contracts are never mutated. Provider strict modes reject complex/recursive
schemas; flat request models avoid the entire class. The same pattern applies to
the Fixer in Phase 5.

**Exit:** `DISCOVERED → DRAFTED` with schema-valid `knowledge_draft` revisions for
the chapter's nodes.

## Phase 5 — Gate 1: review, fix, promote (third LLM stage)

`skills/foundry-gate1/` — three scripts per `docs/pipeline-ledger.md` §3:

- `run_review_base.py`: frontier model as a tool-less structured-output call against
  the `OntologyReviewReport` schema; persist report; record verdict.
- `run_promote_base.py`: verdict `pass` → `VALIDATED` (net-new artifact, register #7).
- `run_fix_base.py`: verdict `fail` → Fixer LLM (per-kind schema) consumes report +
  draft → new draft revision; cycle counters; `QUARANTINE` on exhaustion; re-review
  is Operator-triggered (ADR 017 v1).

**Exit:** a full Gate-1 cycle observed on real nodes — ideally at least one
fail → fix → re-review → pass, and one first-pass promotion.

## Phase 6 — Role launch commands, runbook, guardrail bootstrap

- Role launch definitions: per-role Hermes invocations with pinned toolset
  allowlists — `conductor` (Tier 1 — closes the glossary's forward pointer),
  `discoverer`, `author`, `fixer` (Tier 2: `hermes -t terminal`), `reviewer`
  (Tier 1, exploratory only — the formal gate stays script-mediated). Recorded in
  `docs/runbook.md` and/or thin wrapper scripts; bounded-loop settings via
  `delegation.max_iterations` where delegation is used.
- `docs/runbook.md`: the Operator's step-by-step for one batch (the ~9 commands).
- Constitutional Bootstrap spec (register #49): documented `~/.hermes/config.yaml`
  contents + install/verification step (`approvals.mode manual`, write_approval
  gates, `approvals.deny` globs over `.skills-data/`, local backend).
- AGENTS.md: confirm rules 11/15 against the machine; add the runbook pointer.

**Take care (toolset silent failure):** a mistyped toolset in a launch command
silently yields a different tool registry, and a wrong `approvals.deny` glob simply
never matches — both fail quiet or fail open. Defense: after authoring each role
launch command, read the session banner and run `hermes tools list` for that session
and confirm the effective toolset matches its tier definition exactly (spike-proven
method — migration plan §12).

**Exit:** the full skeleton driven end-to-end from interactive Hermes sessions using
the role launch commands; each session banner matches its tier definition.

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
| Hermes toolset mismatch in a role launch command | Session-banner + `hermes tools list` verification per role (Phase 0/6; spike-proven) |
| Cost of frontier gates | Skeleton is one chapter (~tens of nodes); Phase 7 captures the real number before scaling |

## Session bootstrap (read this first tomorrow)

1. Read `AGENTS.md`, then this plan, then `docs/pipeline-ledger.md` §3–4.
2. Confirm Phase 0 is complete (upstream sha pinned, bootstrap config set, toolsets recorded, provider working).
3. Work proceeds phase-by-phase via the established loop: propose → review → gates
   (`ruff` / `mypy` / `pytest`) green locally → commit → CI green.
4. New design decisions go to `docs/decision-register.md`; ADR deviations go through
   the ADR-Change Rule. No exceptions — that discipline is why this repo is safe to
   implement with LLMs.
