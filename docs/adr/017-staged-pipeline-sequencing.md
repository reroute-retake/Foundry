# ADR 017: Staged Pipeline Sequencing via a Script-Enforced Ledger

- **Date:** 2026-07-07
- **Amended:** 2026-07-17 — "ForgeCode" renamed to "Hermes" per ADR 018; sequencing substance unchanged. See the Amendment section below.
- **Status:** Accepted

## Context

ADR 016 established that ForgeCode is the agent runtime, not the pipeline driver: nothing in the harness deterministically sequences Phases 1–9. Something must decide, for every node, which phase runs next — and the constitution forbids the obvious shortcut ("Not an Agentic Loop": no LLM may dictate workflow). Meanwhile, ADR 005's atomicity means a single book yields hundreds of nodes crossing two review gates, so any model requiring per-node human triggering cannot scale, and a fully automated driver built first would delay the end-to-end walking skeleton by weeks and depends on ForgeCode headless invocation that remains unverified (ADR 016, Open Item).

## Decision

Sequencing is split into a durable authority layer and a replaceable trigger layer.

1. **Sequencing authority is a deterministic Pipeline Ledger — permanent.** A machine-readable ledger in `.skills-data/pipeline/` records, per node: its current lifecycle state, the artifacts produced so far, and transition history. Every mutation script bundled in `.forge/skills/` MUST check the ledger's preconditions before executing and MUST refuse out-of-order transitions (e.g., Enrichment against a node that has not passed Gate 1 exits with a structured error). The ledger is updated only by these scripts, atomically, as part of the transition they perform. No LLM and no human can move a node to an invalid state; they can only request transitions the ledger permits.

2. **v1 trigger: human-advanced phases, batch-scoped — temporary.** The operator runs an interactive ForgeCode session, invokes the role agent for the current phase (`:discoverer`, `:author`, `:reviewer`, …), and scopes it to a batch (a document or chapter). The agent iterates the batch within its bounded-loop limits, calling the transition scripts per node. Humans trigger phases (~9 per batch), never nodes. A `status` script reports per-batch ledger state so the operator always knows what is next and what is blocked.

3. **v2 trigger: deterministic Python driver — additive.** A thin driver CLI walks the same ledger and issues the same script-mediated transitions automatically. It may be built in either variant: (a) shelling into ForgeCode agents headlessly — permitted only after headless invocation and prompt-free restricted-mode policies are verified — or (b) invoking provider APIs directly with the LLM as a tool-less structured-output function (the model already mandated for the Discoverer by ADR 011). Because the ledger and precondition checks predate the driver, v2 replaces the trigger only; no authority logic moves.

## Consequences

- **Positive:** ADR 004 compliance from the first run — all sequencing logic is deterministic, versioned code. Corrupt-order execution is structurally impossible rather than procedurally avoided. Runs are resumable and auditable via the ledger. Human judgment guards both review gates during prompt-tuning (Quality Over Speed & Cost). The unverified-headless risk is removed from the critical path.
- **Negative:** The ledger (state file, precondition checks, `status` script) must be built before the first pipeline run. v1 throughput is bounded by operator attention and suits chapter-scale batches, not whole-book runs.
- **Strict Constraint:** The trigger layer may change; the authority layer may not. Any future automation — including agent-initiated continuation — must issue transitions exclusively through the ledger-checking scripts. A "driver" that bypasses the ledger is a constitutional violation, not an optimization.

## Amendment (2026-07-17, ADR 018)

References to "ForgeCode" are renamed to "Hermes": the v1 trigger is an interactive Hermes
session invoking role agents per phase; v2 trigger option (a) reads "shelling into Hermes
agents headlessly" (still gated on decisive approval-policy termination — headless
invocation itself is verified: `hermes -z`, spike 2026-07-16). The ADR 016 "Open Item"
pointer now reads ADR 018. The sequencing authority (the ledger) and all preconditions are
unchanged. **Hermes' Kanban dispatcher is NOT adopted as a driver** — any v2 driver issues
transitions only through the ledger scripts (constitution; AGENTS.md rule 14).

Path note: the body's `.forge/skills/` reference (Decision §1) predates ADR 013's
2026-07-17 amendment and now reads as the harness-neutral `skills/`.
