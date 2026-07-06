# AGENTS.md — Binding Rules for AI Agents in This Repository

You are working on **Foundry**, a knowledge-refinement pipeline whose architecture is already decided and recorded. Your job is to implement within these decisions, not to re-litigate them. This file is normative; on conflict, ADRs win over this summary.

**Read before any non-trivial task:** `docs/constitution.md`, `docs/ubiquitous-language.md`, `docs/pipeline-ledger.md`, and the ADR relevant to your change.

## The ADR-Change Rule (overrides everything)

If a task requires deviating from an accepted ADR: **STOP. Do not silently deviate.** Write a superseding or amending ADR (next number, house format: Context / Decision / Consequences), present it for acceptance, and only then implement. ADRs in `docs/adr/` are the sole mechanism for changing architectural decisions.

## Non-Negotiable Constraints (ADR index)

1. **JSON is canonical; Markdown is a disposable view.** Never treat rendered output as a source of truth. (ADR 001, 015 — OKF is a render target only, never storage.)
2. **Phase outputs are immutable.** Copy-on-write revisions under `.skills-data/nodes/<id>/rev-NNN.<kind>.json`; never modify an existing revision file; the ledger is append-only. (ADR 002, `docs/pipeline-ledger.md`)
3. **No generative AI in Phase 1 extraction.** Deterministic tools only. Phase-1 code must not import any LLM client. (ADR 003)
4. **No business logic in orchestration.** Scripts route state and enforce schemas; domain judgment lives in prompts and reviewed content. (ADR 004)
5. **Minimum Information Principle:** one artifact = one concept; no enumerations; context via edges, never transcluded prose. (ADR 005, 006)
6. **The taxonomy evaluation order is canonical and immutable:** Attack Vector → Mitigation → Data Structure → Algorithm → Pattern → Failure Mode → Interface → Metric → Tool → Concept. `schemas/discoverer_schema.py` is the machine source of truth; never reorder any mirror. (ADR 007, `docs/classification-predicates.md`)
7. **Two-pass pipeline:** no pedagogical fields in Pass-1 schemas; enrichment never alters ontological fields (scripts diff-check). (ADR 008)
8. **Edge vocabulary is closed** (`EdgePredicate` in `schemas/taxonomy.py`); dangling targets become Ghost stubs via the ledger's `CREATE_GHOST` — a `GhostStub` is not a `BaseNode`. (ADR 009)
9. **Every Pydantic model:** v2, discriminated unions where variant, and `model_config = ConfigDict(extra='forbid')` — no exceptions. (ADR 010)
10. **Discoverer runs under constrained decoding** at the serving layer (vLLM/Outlines class), invoked as a script — never as free text generation. (ADR 011)
11. **Tier definitions (ADR 012):**
    - Tier 1 (Reviewer-type): `tools: [read, search]` (+ read-only MCP). Never `write`, `patch`, `shell`, `fetch`, `remove`.
    - Tier 2 (Discoverer, Author, Fixer, Linker, Enricher): `tools: [read, shell]`. Mutate state **only** by invoking bundled scripts in `.forge/skills/`.
    - Formal gate reviews are executed by Tier 2 scripts invoking the reviewer model as a tool-less structured-output API call (`docs/pipeline-ledger.md` §3).
    - Verify exact tool ids against `:tools` output before authoring agent files.
12. **State isolation:** `.forge/skills/` holds immutable definitions only; ALL runtime artifacts go to `.skills-data/`. (ADR 013)
13. **MCP is read-only for agents;** graph writes happen via scripts. MCP tools bypass `permissions.yaml` — read-only must be enforced server-side. (ADR 014)
14. **ForgeCode is the harness, not the pipeline driver.** The Pipeline Ledger is the sole sequencing authority; every state transition goes through a ledger-checking script — a driver that bypasses the ledger is a constitutional violation. (ADR 016, 017)

## Ledger Rules (operational)

- Never write to `.skills-data/nodes/` or `.skills-data/pipeline/` directly — only through transition scripts.
- Every mutation script follows the write protocol: flock → validate against `TRANSITION_RULES` (`schemas/pipeline_ledger.py`) → write artifacts + record sha256 → append one event + fsync → rewrite manifest via atomic rename.
- Refuse out-of-order transitions with a structured error. On gate fix-cycle exhaustion (`MAX_FIX_CYCLES_PER_GATE = 2`), QUARANTINE — never loop.

## Vocabulary

Use the exact terms from `docs/ubiquitous-language.md` in every identifier, prompt, and schema. Core artifact chain: Source Material → Extracted Text → Topic Metadata → Knowledge Draft → Review Report → Canonical Knowledge. The harness is **ForgeCode**; the sequencing record is the **Pipeline Ledger**.

## Coding Conventions

- Python ≥ 3.12, Pydantic v2 (`>=2.13,<3`). Run scripts with `python3`.
- Type hints everywhere; `ruff` and `mypy` clean; tests with `pytest`.
- No new dependencies without stating why in the PR/commit message.
- Commit style: `area: imperative summary` with a body explaining the why.

## Definition of Done

A change is done only when ALL hold:

1. Schemas/models validate under Pydantic 2.x — including a round-trip test and an `extra='forbid'` rejection test for any new model.
2. `pytest`, `ruff check .`, and `mypy schemas/` pass.
3. No ADR violated; if one had to change, the superseding ADR is in the same commit.
4. New behavior is documented (docs/ updated), and the ubiquitous language is used.
5. No runtime artifacts, secrets, or `.skills-data/` contents are committed.
