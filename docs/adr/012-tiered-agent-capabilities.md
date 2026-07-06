# ADR 012: Tiered Agent Capabilities and Strict Tool Scoping

- **Date:** 2026-06-21    
- **Status:** Accepted

## Context

If an LLM agent possesses native read/write/shell privileges, it can easily bypass execution scripts and hand-write malformed JSON, destroying pipeline determinism.

## Decision

All Forge agents defined in `.forge/agents/` must be explicitly divided into two security tiers using the `tools:` frontmatter array:

- **Tier 1 (Read-Only):** Agents like `Conductor` and `Reviewer` are granted `[read, sem_search, mcp_read]`. They are structurally incapable of mutating files or running shell commands.
- **Tier 2 (Script Executors):** Agents like `Discoverer`, `Author`, and `Fixer` are granted `[read, shell]`, but explicitly denied `write`, `patch`, and `remove`. They mutate state _only_ by executing bundled Python scripts, enforced via `.forge.toml` hooks and `guardrails.deny_commands`.

## Consequences

- **Positive:** Mathematically prevents an LLM from "going rogue" and hand-crafting invalid JSON files.
- **Negative:** Requires rigorous custom agent definitions instead of using the default, over-privileged `forge` agent.