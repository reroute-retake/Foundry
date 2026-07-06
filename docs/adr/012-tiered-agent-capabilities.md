# ADR 012: Tiered Agent Capabilities and Strict Tool Scoping

- **Date:** 2026-06-21
- **Amended:** 2026-07-07 — aligned with verified ForgeCode mechanisms. Supersedes all references to `guardrails.deny_commands` and project-level `.forge.toml` hooks, which do not exist in ForgeCode.
- **Status:** Accepted

## Context

If an LLM agent possesses native write privileges, it can bypass the bundled execution scripts and hand-write malformed JSON, destroying pipeline determinism. ForgeCode agents receive **no tools by default**; each agent's `tools:` frontmatter array is an explicit allowlist. ForgeCode additionally provides a machine-level policy engine: when `restricted = true` is set in `.forge.toml` (in the ForgeCode config directory), every built-in tool call is evaluated against `permissions.yaml` rules (`allow` / `deny` / `confirm`), glob-matched over four operation types: `read`, `write`, `command`, `url`.

## Decision

All Foundry agents defined in `.forge/agents/` are divided into two capability tiers:

- **Tier 1 (Read-Only):** `Reviewer` (and any future planner-type role) is granted `tools: [read, search]` plus narrowly-scoped read-only MCP tools (e.g., `mcp_neo4j_read_*`). Never `write`, `patch`, `shell`, `fetch`, or `remove`. (Exact tool ids — including `sem_search` availability via ForgeCode Services — must be verified against `:tools` output and pinned in AGENTS.md.)
- **Tier 2 (Script Executors):** `Discoverer`, `Author`, `Fixer`, `Linker`, and `Enricher` are granted `tools: [read, shell]` only. State is mutated exclusively by invoking the deterministic Python scripts bundled in `.forge/skills/`.

Enforcement is layered (defense in depth):

1. **Agent allowlists** (`tools:` frontmatter) — removes native `write`/`patch`/`remove` from every LLM role. First line of defense; version-controlled with the repo.
2. **Restricted mode + `permissions.yaml`** — hard enforcement on the runtime machine: `command` rules allowlist only bundled script invocations (e.g., `python3 .forge/skills/**`) and deny generic file-writing shell patterns. These files live in the ForgeCode config directory, _outside_ the repository, and must be installed by the documented bootstrap step.
3. **Script-level validation** — every mutation script validates its payload against the Pydantic schemas before writing. This is the final gate and the only layer that is fully repo-controlled and self-enforcing.

## Caveats (Accepted Risks)

- **Shell escape hatch:** A Tier 2 agent's `shell` tool can, in principle, write files directly (`echo > file.json`, `python -c`, `sed -i`). Tool tiering alone therefore _reduces_ rather than _eliminates_ this risk; elimination requires the restricted-mode command allowlist (layer 2) to be active on the runtime machine.
- **MCP bypass:** `permissions.yaml` governs built-in tools only — **MCP tools bypass it entirely**. Read-only guarantees for Tier 1 MCP access must be enforced server-side (read-only endpoints and credentials), per ADR 014.
- **Unmatched operations prompt:** In restricted mode, an operation matching no rule falls back to `confirm` (an interactive prompt). Policies must terminate decisively (explicit allow/deny coverage) before any unattended execution is introduced.

## Consequences

- **Positive:** Structurally prevents casual native JSON mutation by LLM roles and makes every state change an auditable script invocation.
- **Negative:** Full guardrail strength depends on machine-level configuration that cannot be version-controlled; requires a bootstrap script and honest documentation rather than a claim of absolute prevention.
