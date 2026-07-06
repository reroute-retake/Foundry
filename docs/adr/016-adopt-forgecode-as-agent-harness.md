# ADR 016: Adoption of ForgeCode as the Agent Harness

- **Date:** 2026-07-07
- **Status:** Accepted

## Context

Foundry's agent architecture (ADRs 012–014) requires a runtime that supports declarative agent definitions with per-agent tool allowlists, per-role model routing, bundled skills, MCP integration, and machine-level execution guardrails. Building such a harness in-house would dwarf the pipeline itself. ForgeCode (forgecode.dev) — an open-source, multi-provider CLI coding harness — provides these primitives natively: project-scoped agent definitions (`.forge/agents/*.md` with YAML frontmatter), Claude Code-compatible skills (`.forge/skills/<name>/SKILL.md`), project-scoped MCP configuration (`.mcp.json`), automatic `AGENTS.md` injection, per-agent `model`/`provider` selection, and native bounded-loop controls (`max_turns`, `max_requests_per_turn`, `max_tool_failure_per_turn`).

## Decision

Foundry adopts ForgeCode as its agent harness. All LLM roles (Discoverer, Author, Reviewer, Fixer, Linker, Enricher) are defined as ForgeCode custom agents in `.forge/agents/`. Skills and their bundled mutation scripts live in `.forge/skills/`. Graph and vector read access is provided via MCP servers declared in `.mcp.json`.

Boundaries of responsibility:

1. **The harness is the agent runtime, not the pipeline driver.** ForgeCode executes one agent conversation at a time; it does not deterministically sequence Phases 1–9. Phase sequencing is governed separately (ADR 017, to be authored).
2. **Deterministic enforcement lives in Foundry's scripts.** Pydantic schema validation and all state transitions are enforced by the bundled Python scripts — never by the harness or the model.
3. **Version pinning.** The ForgeCode version in use must be recorded in the repository, since agent, skill, and permission semantics may change between releases.

## Consequences

- **Positive:** Eliminates the single largest build risk (a bespoke harness). Tiered tool scoping, per-role model routing, skills, and MCP arrive as version-controlled configuration instead of code.
- **Negative:** Couples Foundry to ForgeCode's conventions and release cadence. Machine-level guardrails (`restricted` mode, `permissions.yaml`) live outside the repository and require a documented bootstrap step on each runtime machine (ADR 012).
- **Open Item:** Headless/scripted invocation of ForgeCode agents must be verified before any automated, non-interactive pipeline driver is designed (input to ADR 017).
