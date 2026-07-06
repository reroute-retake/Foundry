# ADR 006: Graph Metadata Over Textual Transclusion

- **Date:** 2026-06-21
- **Status:** Accepted

## Context

When notes are aggressively atomized, authors often rewrite prerequisite context into the new note, violating the DRY (Don't Repeat Yourself) principle and bloating the atomic artifact.

## Decision

Dependencies between concepts will be managed entirely through typed metadata edges (e.g., `IMPLEMENTS`, `MITIGATES`), not through embedded prose in the `core_definition` or `operational_context`. A note speaks only about itself.

## Consequences

- **Positive:** Keeps nodes perfectly atomic and prevents data desynchronization if a prerequisite concept is updated.
- **Negative:** Requires the UI/Renderer layer to dynamically fetch and display prerequisites at render time.