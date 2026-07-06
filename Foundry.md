# Foundry — AI-Assisted Knowledge Refinement Pipeline

## Vision

Foundry is a local-first knowledge-generation system designed to transform books, PDFs, articles, and study materials into high-quality learning resources.

Unlike traditional note-taking systems that generate Markdown directly, Foundry treats structured knowledge as the primary artifact and Markdown as a rendered view.

The goal is not to summarize books.

The goal is to create a curated, interconnected, high-quality knowledge base optimized for:

- Learning and long-term retention
    
- Interview preparation and concept mastery
    
- Knowledge discovery
    
- Obsidian-based study workflows
    

# Core Philosophy

Most note-generation systems follow this approach: `Source Material → Notes`

This system follows: `Source Material → Structured Knowledge → Review → Graph Linking → Enrichment → Review → Rendered Artifacts`

Knowledge is the source of truth. Markdown is merely one presentation format.

# Design Principles

## 1. Structured Data First

All intermediate artifacts should be machine-readable (JSON/JSONL). Markdown is generated only at the final stage to allow for multiple output formats and strict programmatic validation.

## 2. Deterministic Extraction

Document extraction should not use an LLM. Tools like Marker or Docling convert PDF to Markdown deterministically. Generative AI is forbidden in Phase 1.

## 3. The Double-Gated Two-Pass Pipeline

Extracting dense ontological facts and generating pedagogical artifacts simultaneously causes LLM context exhaustion.

- **Pass 1 (Ontology):** Extracts pure, atomic facts. Gated by a Review/Fix cycle.
    
- **Pass 2 (Enrichment):** Generates edges, flashcards, and diagrams. Gated by a final Review/Fix cycle before becoming Canonical.
    

## 4. Minimum Information Principle & Atomicity

Notes must be perfectly atomic. A single note answers one question or defines one mechanism. Encyclopedic summaries are forbidden.

## 5. Graph Metadata Over Text

Dependencies are mapped via strict graph edges (`IMPLEMENTS`, `REQUIRES`), not by rewriting prerequisite context inside the note body.

# Pipeline Overview

## Phase 1 — Extraction

- **Purpose:** Convert source documents into structured text.
    
- **Tools:** Marker, Docling. (Deterministic, no reasoning).
    

## Phase 2 — Topic Discovery (Atomic Shredding)

- **Purpose:** Isolate technical entities from prose and classify them using the 10-Level Decision Tree State Machine.
    

## Phase 3 — Ontological Drafting

- **Purpose:** Generate the base JSON schema (strict discriminated unions). No flashcards or edges generated here.
    

## Phase 4 — First Gate: Ontology Review & Resolution

- **Purpose:** The `Reviewer` (Frontier Model) identifies factual gaps in the base draft. The `Fixer` applies corrections.
    

## Phase 5 — Linker (Relationship Discovery)

- **Purpose:** Discover and inject formal Graph Edges (`IS_A`, `MITIGATES`). Creates "Ghost Nodes" for dangling references.
    

## Phase 6 — Pedagogical Enrichment

- **Purpose:** Act as an instructional designer. Reads the validated JSON base and generates analogies, diagrams, and Anki flashcards.
    

## Phase 7 — Second Gate: Enrichment Review & Resolution

- **Purpose:** The `Reviewer` verifies that the newly added graph edges are semantically sound and the flashcards/analogies are factually accurate. The `Fixer` resolves any flaws. The artifact is now **Canonical**.
    

## Phase 8 & 9 — Curation & Rendering

- **Purpose:** Generate Maps of Content (MOCs) and compile the final Canonical JSON payload into Google Open Knowledge Format (OKF) Bundles. The Renderer maps JSON `primary_kind` to the OKF YAML `type`, and translates JSON edges into both extended frontmatter and appended Markdown links.

# Note Taxonomy (The 10 Canonical Types)

The system supports exactly 10 strictly bounded note types, evaluated in this precise sequence from lowest to highest semantic entropy (the canonical evaluation order per ADR 007 — mirrored exactly by `docs/taxonomy.md` and `schemas/discoverer_schema.py`, and never to be reordered independently):

1. **Attack Vector:** Malicious exploits (e.g., SQL Injection)
    
2. **Mitigation:** Defense mechanisms (e.g., Rate Limiting)
    
3. **Data Structure:** Physical byte arrangements (e.g., Write-Ahead Log)
    
4. **Algorithm:** Step-by-step logic (e.g., Two-Phase Commit)
    
5. **Pattern:** Topological layouts (e.g., Leaderless Replication)
    
6. **Failure Mode:** Systemic breakdowns (e.g., Split-Brain)
    
7. **Interface:** Shared boundaries/protocols (e.g., REST, gRPC)
    
8. **Metric:** Quantifiable measures/formulas (e.g., w + r > n)
    
9. **Tool:** Deployable software (e.g., PostgreSQL)
    
10. **Concept:** Theoretical invariants (e.g., Eventual Consistency)