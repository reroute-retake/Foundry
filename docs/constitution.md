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

## 5. Architectural Security & Orchestration (Forge)

- **Tiered Agent Scoping:** Agents must be structurally bounded. Planners and Reviewers must be **Tier 1** (read-only). State mutators must be **Tier 2** (script executors).
- **Prohibition of Native Mutation:** No agent is permitted to natively write JSON using generic `write` or `patch` tools. All ontological state transitions must execute through deterministic Python scripts bundled within Forge skills.
- **State Isolation:** Mutable data must never pollute the `.forge/skills/` directory. All runtime JSON artifacts must be written to a dedicated `.skills-data/` directory.
- **Progressive Disclosure:** Massive Pydantic schemas and ontological axioms must not be loaded in global agent prompts. They must live in skill `references/` folders to be dynamically loaded only when required.

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