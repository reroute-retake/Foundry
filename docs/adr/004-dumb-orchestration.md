# ADR 004: Dumb Orchestration (Forge Independence)

* **Date:** 2026-06-20
* **Status:** Accepted

## Context
Complex AI pipelines often bleed prompt logic, retry mechanics, and business rules into the orchestration code, creating an unmaintainable monolith.

## Decision
Forge (the orchestrator) must contain no business logic or domain understanding. Its sole responsibilities are routing state, executing predefined tools, and enforcing JSON schema validation.

## Consequences
* **Positive:** You can swap LLM providers or change the pipeline completely just by updating schemas and prompts, without rewriting Forge's core execution loop.
* **Negative:** Requires extremely rigorous schema definitions, as Forge cannot "infer" what to do with malformed AI outputs.
