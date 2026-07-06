# Foundry Schema: A Plain English Guide

The Python code in `schemas/taxonomy.py` looks highly academic, but its actual purpose is extremely practical: it acts as a **straitjacket** for the Large Language Model (LLM).

LLMs naturally want to write chatty, rambling, encyclopedic paragraphs. By using this strict Pydantic JSON schema, we force the AI to break down complex technical thoughts into perfectly isolated, bite-sized facts.

## How We Handle Context (The ADR 006 Rule)

A common question when atomizing notes is: _"If a note is perfectly atomic, how do we capture its context? If I read a note about 'Read Repair', don't I need to know it belongs to 'Leaderless Replication'?"_

The answer is governed by **ADR 006: Graph Metadata Over Textual Transclusion**. We do **not** write paragraphs explaining prerequisite context. We map it via `edges`.

**Bad (Violates ADR 006):**

> _core_definition: "Read Repair is a process used in leaderless replication databases where a client reading from multiple nodes notices a stale value on one node and sends the updated value back."_

**Good (Follows ADR 006):**

> _core_definition: "An anti-entropy process where a client detects stale data during a read operation and immediately sends a write request to update the lagging replica."_ _edges: `[{"predicate": "REQUIRES", "target_canonical_id": "leaderless_replication"}]`_

When you finally view the note in Obsidian, the `Renderer` phase will automatically fetch the target edge and dynamically display the connection. The knowledge remains atomic, but the human reading it gets the full context.

## The Base Properties (Every Note Has These)

Regardless of whether the AI is defining a Tool (like PostgreSQL) or a Failure Mode (like Split-Brain), it must provide:

- **canonical_id:** A unique, URL-safe snake_case name (e.g., `two_phase_commit`). Used to link notes together.
- **title:** The human-readable name.
- **core_definition:** The strict, invariant "What". Restricted to a few sentences. No bulleted lists allowed.
- **operational_context:** The "Where/When". What kind of workload or environment triggers this?
- **edges:** The specific relationships to other canonical IDs (e.g., `MITIGATES: replication_lag`).
- **provenance:** Exactly where in the PDF/Source the AI found this fact, to prevent hallucinations.

## The Discriminated Payload (Type-Specific Rules)

Because we use a "Discriminated Union," the AI must declare exactly what _kind_ of note it is writing using the `primary_kind` field. Once it declares a type, it is forced to fill out a specialized `payload`.

For example, if the AI says `primary_kind: "Algorithm"`, it is instantly forced to provide:

1. **pre_conditions:** What must be true before this algorithm starts?
2. **post_conditions:** What state is guaranteed after it finishes?
3. **time_complexity / space_complexity:** Big-O notation.

If it tries to write an Algorithm without providing `time_complexity`, the Forge Orchestrator automatically rejects it.

## Where are the Flashcards and Diagrams? (The ADR 008 Rule)

You might notice that `visual_representation` (Mermaid diagrams) and `flashcards` are missing from this schema.

This is intentional, based on **ADR 008: The Two-Pass Pipeline**.

1. **Pass 1 (This Schema):** The LLM extracts only the pure, mathematical/ontological facts from the text.
2. **Pass 2 (Enrichment):** After the facts are securely saved, a separate AI process reads the finalized JSON and acts as an instructional designer, generating the analogies, diagrams, and flashcards.

By splitting these tasks, we prevent the LLM from getting "confused" or dropping important data while it tries to juggle technical extraction and creative pedagogical generation simultaneously.