# ADR 009: Formal Edge Ontology and Ghost Node Resolution

- **Date:** 2026-06-21
- **Status:** Accepted

## Context

Allowing an LLM to invent arbitrary graph edges (e.g., `HAS_RELATIONSHIP_WITH`) ruins programmatic multi-hop queries. Furthermore, extracting notes out of order creates "dangling links."

## Decision

1. **Formal Vocabulary:** Edges are strictly limited to a defined matrix (`IS_A`, `IMPLEMENTS`, `REQUIRES`, `MITIGATES`, `CAUSES`, `EXEMPLIFIES`, etc.).
2. **Ghost Nodes:** If a target `canonical_id` does not exist during ingestion, the orchestrator executes a defensive `MERGE` to create a "Ghost Node" stub. This stub is later updated via `UPSERT` when the full text is processed.

## Consequences

- **Positive:** Eliminates pipeline crashes due to out-of-order document ingestion and guarantees a traversable property graph.
- **Negative:** Requires defensive upsert logic in Forge.