# ADR 015: Adoption of OKF as a Rendering Target

- **Date:** 2026-07-07
- **Status:** Accepted

## Context

Google Cloud published the Open Knowledge Format (OKF v0.1), establishing a vendor-neutral interchange format for AI agents consisting of a directory of Markdown files with YAML frontmatter (the "LLM-Wiki" pattern). While highly compatible with downstream PKM tools (like Obsidian) and MCP file servers, allowing an LLM to natively mutate YAML/Markdown documents violates the strict deterministic constraints of our pipeline and invites silent schema corruption.

## Decision

We reaffirm **ADR 001**: Pydantic-validated JSON remains the absolute, immutable source of truth for all Foundry knowledge graphs. We explicitly reject OKF as a storage mechanism or system of record.

However, we adopt OKF as our official, disposable **Render Target**. The final stage of the Foundry pipeline (`Renderer`) will utilize a unidirectional, deterministic compiler to project the Canonical JSON graph into a strictly compliant OKF Bundle.

- JSON `primary_kind` maps to OKF YAML `type`.
- JSON `edges` map to both an extended YAML frontmatter array (for lossless machine reading) and appended Markdown links (for human/generic parser reading).

## Consequences

- **Positive:** Instantly unlocks massive ecosystem leverage. Foundry output becomes natively ingestible by standard MCP servers, Obsidian Dataview, Google Knowledge Catalog, and third-party visualizers without requiring custom adapters.
- **Negative:** Requires building a deterministic JSON-to-OKF compiler.
- **Strict Constraint:** The OKF directory is an immutable build artifact. Manual human edits to the rendered Markdown files will _not_ synchronize back to the Foundry JSON core.