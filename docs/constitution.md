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

## 5. Architectural Security & Orchestration (ForgeCode Harness)

- **Harness Adoption:** Foundry's agent runtime is **ForgeCode** (the `forge` CLI). All LLM roles are project-scoped ForgeCode agents in `.forge/agents/`; skills and their mutation scripts live in `.forge/skills/` (ADR 016).
- **Harness ≠ Pipeline Driver:** ForgeCode runs one agent conversation at a time; it does not sequence the pipeline. Phase sequencing and state routing are Foundry's own responsibility (deterministic scripts; sequencing model governed by ADR 017).
- **Tiered Agent Scoping:** Agents are structurally bounded via ForgeCode's per-agent `tools:` allowlist (agents have no tools unless granted). Reviewers and planner-type roles are **Tier 1** (read-only: `read`, `search`, read-only MCP). State mutators are **Tier 2** (`read`, `shell` — script executors only) (ADR 012).
- **Prohibition of Native Mutation:** No agent is granted `write`, `patch`, or `remove`. All ontological state transitions execute through deterministic, Pydantic-validating Python scripts bundled within skills. Tool tiering is defense-in-depth — the `shell` tool could technically write files — so hard enforcement comes from ForgeCode **restricted mode** (`restricted = true`) plus **`permissions.yaml`** command allowlists installed on the runtime machine via the documented bootstrap step.
- **Machine-Level Guardrails Are a Prerequisite, Not a Repo Artifact:** `.forge.toml` and `permissions.yaml` live in the ForgeCode config directory, outside version control. Their required contents are specified in-repo and installed by bootstrap; a run without them is a degraded-guardrail run and must be treated as such.
- **MCP Read-Only Is Server-Enforced:** MCP tools bypass `permissions.yaml`. Tier 1 read-only access to graph/vector stores is enforced by the MCP servers themselves (read-only endpoints and credentials), never assumed from harness policy (ADR 014).
- **State Isolation:** Mutable data must never pollute `.forge/skills/`. All runtime JSON artifacts are written to the dedicated `.skills-data/` directory at the project root (ADR 013).
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