# ADR 012: Tiered Agent Capabilities and Strict Tool Scoping

- **Date:** 2026-06-21
- **Amended:** 2026-07-07 — aligned with verified ForgeCode mechanisms. Supersedes all references to `guardrails.deny_commands` and project-level `.forge.toml` hooks, which do not exist in ForgeCode.
- **Amended:** 2026-07-17 — harness mechanism swapped from ForgeCode to Hermes Agent per ADR 018. The two-tier model and defense-in-depth layering stand; the mechanisms that implement them are re-expressed in the Amendment section below, which supersedes the ForgeCode mechanism references in the body.
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

## Amendment (2026-07-17, ADR 018 — Hermes harness)

The tier model is unchanged; its Hermes implementation:

- **Layer 1 (allowlists)** — was ForgeCode `tools:` frontmatter; now **session-launch
  narrowing** `hermes -t <toolsets>` plus delegate inheritance-minus-blocked-set. Tier 2
  = `-t terminal` (terminal+process; spike-verified: no `write_file`/`patch`). Tier 1 =
  no mutating toolsets, reads via read-only MCP (ADR 014); the formal Reviewer stays
  tool-less script-mediated. A per-call model-facing toolset parameter does not exist and
  is not trusted (spike incident A: the model narrated a restriction it never applied —
  `docs/hermes-migration-plan.md` §12).
- **Layer 2 (machine policy)** — was restricted mode + `permissions.yaml`; now the
  **Constitutional Bootstrap** (register #49): `approvals.mode: manual` (the shipped
  `smart` default routes dangerous-command decisions to an aux LLM — forbidden by ADR 004
  and this ADR; spike incident B), `approvals.deny` globs over `.skills-data/`, local
  backend, no `--yolo`. Command-scoped only (no read/write/url operation types) — a
  partial `permissions.yaml` analogue.
- **Layer 3 (script validation)** — unchanged; still the only fully repo-controlled,
  self-enforcing gate.

Caveats retained and re-expressed: the shell escape hatch now reads "the `terminal`
toolset can write via redirection" — reduced by layer-2 deny globs, not eliminated. MCP
still bypasses approval policy (Hermes issue #16462) — Tier-1 read-only stays
server-enforced (ADR 014). Open item: the exact minimal Tier-1 toolset is pinned in
Phase 6, because the Hermes `file` toolset bundles read with write/patch.
