# Foundry Constitution

## 1. Mission

Foundry exists to transform learning materials into high-quality, interconnected knowledge artifacts optimized for learning, retention, and practical application. Foundry treats structured knowledge as the primary artifact and Markdown as a rendered view.

## 2. Non-Goals

- **Not a General Purpose Chatbot:** It refines knowledge; it does not converse.
- **Not a Book Summarization Tool:** Summarization creates bloat. Foundry enforces atomicity.
- **Not an Agentic Loop:** The orchestrator enforces strict Pydantic schemas; it does not allow autonomous LLMs to dictate workflows or loop infinitely.

## 3. Core Principles

- **Minimum Information Principle:** Encyclopedic notes are forbidden. Notes must represent a single, indivisible concept.
- **Quality Over Speed & Cost:** Educational efficacy takes precedence over infrastructure costs.
- **Structured Knowledge Before Rendering:** JSON is canonical. Markdown is a disposable view layer.
- **Graph Metadata Over Text:** Context is handled by edges, not by duplicating text.
- **Deterministic Extraction:** Phase 1 extraction must not use generative AI.

## 4. Canonical Artifacts

- **Structured Knowledge Is Canonical:** All downstream outputs derive from the JSON graph.
- **Reviews Are Canonical:** Critiques are preserved for model tuning.
- **Relationships Are Canonical:** Edges (`IMPLEMENTS`, `MITIGATES`) are first-class structural entities.
- **Ghost Nodes Are Permitted:** Dangling references generate placeholder stubs to maintain graph integrity during out-of-order document ingestion.

## 5. Architectural Security & Orchestration (Hermes Harness)

- **Harness Adoption:** Foundry's agent runtime is **Hermes Agent** (the `hermes` CLI). LLM roles are launched as toolset-scoped Hermes sessions; skills and their mutation scripts live in `skills/`, registered as a Hermes external skill directory (ADR 018, supersedes ADR 016).
- **Harness ≠ Pipeline Driver:** Hermes runs one agent conversation at a time and offers orchestration subsystems (Kanban, cron, gateway) — none of which sequence Foundry. Phase sequencing and state routing are Foundry's own responsibility (deterministic scripts; sequencing model governed by ADR 017). A Hermes driver that bypasses the ledger is a constitutional violation.
- **Tiered Agent Scoping:** Agents are structurally bounded via session-launch toolset allowlists (`hermes -t`). **Tier 2** state mutators launch with `-t terminal` and mutate only via scripts. **Tier 1** planner/reviewer roles receive no mutating toolsets; reads come via read-only MCP; the formal gate Reviewer is tool-less and script-mediated (ADR 012, amended by ADR 018).
- **Prohibition of Native Mutation:** No role is launched with the `file` toolset (which bundles `write_file`/`patch`). All ontological state transitions execute through deterministic, Pydantic-validating Python scripts bundled within skills. Tool scoping is defense-in-depth — the `terminal` toolset could technically write via redirection — so hard enforcement comes from the **Constitutional Bootstrap**: `approvals.mode: manual` (never the aux-LLM `smart` default), `approvals.deny` globs over `.skills-data/`, `write_approval` gates on memory and skills, a local backend, and no `--yolo` (register #49).
- **Machine-Level Guardrails Are a Prerequisite, Not a Repo Artifact:** the bootstrap config lives in `~/.hermes/config.yaml` on the runtime machine, outside version control. Its required contents are specified in-repo (register #49) and installed by bootstrap; a run without them is a degraded-guardrail run and must be treated as such.
- **Sanctioned Auth Only:** interactive inference authenticates via the officially sanctioned `xai-oauth` provider (SuperGrok). Credential-proxy patterns are prohibited (ADR 018).
- **MCP Read-Only Is Server-Enforced:** MCP tools bypass approval policy. Tier 1 read-only access to graph/vector stores is enforced by the MCP servers themselves (read-only endpoints and credentials), never assumed from harness policy (ADR 014).
- **State Isolation:** Mutable data must never pollute `skills/`. All runtime JSON artifacts are written to the dedicated `.skills-data/` directory at the project root (ADR 013).
- **Progressive Disclosure:** Massive Pydantic schemas and ontological axioms must not be loaded in global agent prompts. They live in skill `references/` folders and are loaded only when the skill is applied.

## 6. AI Roles and Responsibilities

- **Extractor:** Deterministic document conversion. Must not use LLMs.
- **Discoverer (Tier 2):** Identifies topics and classifies them via the 10-level FSM script. Must not write JSON directly.
- **Author (Tier 2):** Generates Base Ontological JSON artifacts by executing the upsert script.
- **Reviewer (Tier 1):** Evaluates drafts for factual and structural accuracy. Structurally forbidden from writing or patching.
- **Fixer (Tier 2):** Resolves Reviewer critiques via the repair script.
- **Linker (Tier 2):** Discovers Graph Edges using MCP tools, then formally persists them via script.
- **Enricher (Tier 2):** Generates analogies, Mermaid.js diagrams, and Anki flashcards via script. Must not alter ontological facts.
- **Curator:** Generates MOCs and learning sequences.
- **Renderer:** Transforms JSON to Markdown.