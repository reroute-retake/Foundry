# ADR 018: Adoption of Hermes Agent as the Agent Harness

- **Date:** 2026-07-17
- **Status:** Accepted
- **Supersedes:** ADR 016

## Context

ADR 016 adopted ForgeCode as the harness. That decision was accurate about ForgeCode's
capabilities but predated any billing or market survey. Two facts forced a re-evaluation
before implementation began:

1. ForgeCode is practically API-key/pay-as-you-go only; its subscription-riding path
   carries a maintainer-acknowledged account-ban risk. The Operator requires fixed
   monthly subscription cost during development, with PAYG acceptable only after the
   pipeline is built and validated.
2. No pipeline code exists yet, so the harness binding is confined to documentation,
   one README pin, and one test glob — the cheapest possible moment to switch.

A web-verified harness survey (2026-07-15) and an operator-machine spike (2026-07-15/16)
evaluated Hermes Agent (Nous Research, MIT). The spike verified every gating assumption
on Hermes v0.18.2 (upstream `e0e7cfa6`) using a trial SuperGrok subscription via xAI's
officially sanctioned `xai-oauth` provider. Full rationale, rejected alternatives, and
the spike scorecard live in `docs/hermes-migration-plan.md` (§12).

## Decision

Foundry adopts **Hermes Agent** as its agent harness, superseding ADR 016. The two
boundaries from ADR 016 are retained verbatim:

1. **Harness ≠ Pipeline Driver.** The Pipeline Ledger (ADR 017) remains the *sole*
   sequencing authority. Hermes' orchestration subsystems (Kanban, cron dispatcher,
   gateway) MUST NOT sequence or execute node transitions except by invoking the bundled
   ledger scripts, which enforce preconditions regardless of caller.
2. **Deterministic enforcement lives in Foundry's scripts.** Pydantic validation and all
   state transitions stay in bundled Python scripts — never the harness, never the model.

Harness-specific decisions:

3. **Tool scoping via session-launch narrowing.** Roles launch with an explicit toolset
   allowlist (`hermes -t <toolsets>`) — the Hermes analogue of ForgeCode's per-agent
   `tools:` frontmatter. A per-call, model-facing toolset parameter **does not exist and
   MUST NOT be trusted**: spike run 1 showed the model will narrate a restriction it
   cannot apply. Delegated sub-agents inherit the parent's toolset minus a hardcoded
   blocked set. (Verified: `-t terminal` yields terminal+process only; `write_file`
   physically absent; memory-blind.)
   - **Tier 2** (Discoverer, Author, Fixer, Linker, Enricher): `-t terminal`. Mutate
     state only by invoking bundled scripts. No `file`, `delegation`, `memory`, or
     `code_execution`.
   - **Tier 1** (Conductor; exploratory Reviewer): no mutating toolsets; reads via
     read-only MCP (ADR 014). The formal gate Reviewer stays tool-less script-mediated
     (unchanged). Because Hermes' `file` toolset bundles read with write/patch, the exact
     minimal Tier-1 toolset is pinned by per-role session-banner verification in Phase 6
     (open item).

4. **Machine-level guardrails = the Constitutional Bootstrap.** Hermes ships permissive
   defaults (silent memory/skill writes; an auxiliary-LLM "smart approvals" guardian that
   can auto-approve dangerous commands). The following config is therefore a bootstrap
   prerequisite, installed and documented on each runtime machine (the ADR 012 sense of
   machine-level guardrails outside version control):
   - `approvals.mode: manual` — never the `smart` default; smart routes the
     dangerous-command decision to an aux LLM, placing LLM judgment inside enforcement
     (forbidden by ADR 004/012).
   - `memory.write_approval: true` and `skills.write_approval: true` — no silent learning.
   - `approvals.deny` fnmatch globs covering `.skills-data/` mutations (unconditional;
     fires before any yolo/mode-off bypass).
   - local (non-container) backend — container backends disable command approvals by
     documented design.
   - never `--yolo`.
   These replace ForgeCode's restricted mode + `permissions.yaml`. The layer is
   command-scoped only (no read/write/url operation types) — weaker than
   `permissions.yaml`, so script-level validation remains the only fully repo-controlled
   guarantee, exactly as ADR 012 already states.

5. **Sanctioned auth only.** Interactive sessions authenticate via `xai-oauth`
   (SuperGrok). OAuth-token proxy patterns (CLIProxyAPI, codex-proxy, `hermes proxy`) are
   prohibited (provider ToS; 2026 enforcement bans).

6. **Version pinning (retains ADR 016 §3).** Hermes has no auto-update daemon, but the git
   installer tracks `main` and the banner nags — so the pin is the **upstream commit sha**,
   recorded in README; reproducible installs use the installer's `--commit` flag. Updates
   are deliberate: update → re-enumerate toolsets → diff → amend the pin and register in
   one commit.

Skills and their bundled mutation scripts live in repo-local `skills/` (harness-neutral;
ADR 013 amended), registered as a Hermes external skill directory. Graph/vector read
access is via read-only MCP (ADR 014).

## Consequences

- **Positive:** fixed-cost dev inference on a sanctioned ~$30/mo subscription;
  open-source auditable harness; `SKILL.md` skill format portable and unchanged;
  migration touches zero schemas and one test glob; unlocks a future
  operator-gateway/approval/cron roadmap (deferred ADR 019).
- **Negative / accepted risks:** the top-level session retains broad tools unless launched
  with `-t` (mitigated: role launch commands are the allowlist; delegates
  inherit-minus-blocked; approvals manual on local backend; deny globs; the
  script+ledger layer is unchanged). Approval policy is thinner than `permissions.yaml`
  and its default is unsafe — hence the mandatory bootstrap. Hermes is young (weekly
  releases) — the pin discipline absorbs churn. A truly read-only Tier 1 is not cleanly
  expressible via built-in toolsets (`file` bundles write) — resolved via read-only MCP +
  Phase 6 verification.
- **Watch items:** #30269 (delegate memory isolation), #16462 (MCP approval bypass),
  #26847 (SuperGrok 403s), `approvals.mode` default drift. See migration plan §8.
- ADR 016 is marked Superseded; ADRs 012/013/017 are amended in the same change set; the
  decision register gains section 10 (#47–#50).
