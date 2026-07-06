# ADR 013: Skill State Isolation (`.skills-data/`)

- **Date:** 2026-06-21
- **Status:** Accepted

## Context

Standard agent workflows often dump generated logs, cache files, and intermediate JSON artifacts directly into the folder where the agent's instructions live. This pollutes version control and mixes immutable instructions with mutable state.

## Decision

Foundry mandates absolute State Isolation.

- `.forge/skills/` is strictly reserved for immutable skill definitions, scripts, schemas, and axioms.
- All executing scripts must route their outputs, temp files, and generated canonical JSON payloads to a dedicated `/.skills-data/` directory at the project root.

## Consequences

- **Positive:** `.forge/` remains entirely version-controllable and clean. Runtime data is easily queryable and reviewable in a centralized data folder.
- **Negative:** Bundled Python scripts must accurately resolve workspace paths to ensure data lands in the correct output directory.