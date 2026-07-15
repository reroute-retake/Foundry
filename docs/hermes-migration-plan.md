# Hermes Agent Migration Plan (ForgeCode → Hermes)

- **Date:** 2026-07-15
- **Status:** Proposal — pre-ADR planning document
- **Scope discipline:** This document plans the migration; it does not execute it. Per the AGENTS.md ADR-Change Rule, ADR 016 remains the accepted harness decision until the superseding ADR (018, step M1 below) is authored and accepted. Nothing else in the repository changes with this commit.

## 1. Decision and scope

The Operator has decided to replace **ForgeCode** with **Hermes Agent** (Nous Research, `github.com/NousResearch/hermes-agent`, MIT) in the role ADR 016 defines: the **agent harness** — the runtime that hosts LLM roles as scoped agents, serves skills, connects MCP, and injects `AGENTS.md`.

Two boundaries are explicitly **preserved unchanged**:

1. **Harness ≠ Pipeline Driver** (constitution §"Harness ≠ Pipeline Driver", ADR 016 boundary 1, ADR 017, AGENTS.md rule 14). The Pipeline Ledger remains the *sole* sequencing authority. Hermes' own orchestration subsystems (Kanban task board, cron dispatcher, gateway) MUST NOT execute or sequence node state transitions except by invoking the bundled ledger scripts, which enforce preconditions regardless of caller.
2. **Deterministic enforcement lives in Foundry's scripts** (ADR 016 boundary 2). Pydantic validation and all state transitions stay in the bundled Python scripts — never in the harness, never in the model.

An externally produced "Hermes blueprint" proposing Hermes Kanban as the pipeline orchestrator and OAuth-proxy layers (CLIProxyAPI / codex-proxy / `hermes proxy`) for subscription billing was evaluated on 2026-07-15 and **rejected** on both counts (see §8 and §11). This migration adopts Hermes for the harness role only, on sanctioned auth only.

## 2. Why

1. **Billing model mismatch (the trigger).** ForgeCode is practically API-key/pay-as-you-go only. Its subscription-riding `claude_code` provider carries a maintainer-acknowledged account-ban risk (Anthropic's January 2026 enforcement against credential piggybacking). The Operator requires **fixed monthly subscription cost during development** — no metered API surprises — with PAYG acceptable only after the pipeline is built and validated. ADR 016 §Context was accurate about capabilities but the decision predated any billing/market survey; this migration corrects that with one (research provenance in §12).
2. **A sanctioned subscription path exists on Hermes.** xAI's `xai-oauth` provider integration is **officially sanctioned by xAI** (co-announced 2026-05-15, `x.ai/news/grok-hermes`; Hermes PR #26534): a SuperGrok subscription (~$30/mo) legitimately drives Hermes interactive sessions with grok-4.3 (1M-token context, GA 2026-05-06). This is, as of research date, the only ToS-clean consumer-subscription → frontier-model path among the Operator's candidate subscriptions.
3. **Operational roadmap value.** Hermes provides, today: messaging gateways (Telegram/WhatsApp among ~20 adapters) with **blocking approval flows**, scheduled/cron automations with a deterministic no-agent watchdog mode, and headless invocation. These map directly onto Foundry's Operator duties (phase triggering, gate notifications, exclusive QUARANTINE/RELEASE authority — ADR 017 v1) and onto ADR 017's deferred v2 driver. Adoption of those features is a **separate, future ADR** (019, deferred); they are motivation, not scope.
4. **Low migration cost, and the cheapest possible moment.** No pipeline code exists yet (Phases 1+ not started). The ForgeCode binding is confined to documentation, one README pin, and one glob in one test (§7, grep-verified at HEAD `99bd589`). Skills were specified in the Claude Code-compatible `SKILL.md` format (ADR 016), which Hermes implements natively (agentskills.io) — skill specifications port as-is.

**Honest ranking note.** The 2026-07-15 research ranked Claude Code + Claude Max first on enforcement-mechanism maturity (its settings-based deny/allow/ask engine is the closest match to ADR 012's original design). The Operator selects Hermes on total cost (~$30/mo vs ~$100+/mo), the sanctioned xai-oauth path, open-source auditability, and the ops roadmap (§2.3), accepting the enforcement deltas in §9 with the mitigations stated there. Claude Code + Max remains the named fallback if M2 verification fails (§10).

## 3. What Hermes is (verified 2026-07-15)

Open-source (MIT) agent framework by Nous Research; launched Feb–Mar 2026; ~215K GitHub stars; weekly releases; current release v0.18.2 / v2026.7.7.2 (2026-07-07). Relevant verified primitives: named delegate profiles with **construction-time-enforced** toolsets (delegated sub-agents physically lack excluded tools — issue #9459 closed 2026-07-05); delegation depth capped by `delegation.max_spawn_depth` (default 1); `AGENTS.md` context injection; `SKILL.md` skills with external skill-directory support, hub security scanning, and hash-locking; MCP client (OAuth 2.1, mTLS) and MCP server modes; layered security model including command approval with blocklist and a file-write denylist; SQLite+FTS5 session store; two-file Markdown memory (silent writes by default; `memory.write_approval` / `skills.write_approval` opt-in gates; `memory_enabled: false` kill switch); delegates are memory-blind by construction (memory tool blocked + `skip_memory=True`); headless mode; local trajectory export (off by default).

## 4. Tier discipline re-mapped (ADR 012 → Hermes primitives)

| ADR 012 concept | ForgeCode mechanism | Hermes mechanism | Status |
| --- | --- | --- | --- |
| Per-role agent definitions, version-controlled | `.forge/agents/*.md` frontmatter | Named delegate profiles (model + prompt + toolsets) | ✅ shipped (#9459); exact config format pinned in M2 |
| Tier tool allowlists, machine-enforced | `tools:` frontmatter allowlist | Delegate `toolsets` enforced at construction (tools absent from child schema) | ✅ for **delegates**; ⚠️ see top-level caveat below |
| Deny sub-agent spawning per role (register #45 `task` never-list) | omit `task` | `max_spawn_depth: 1` default; `delegation` toolset force-stripped from delegates | ✅ aligns by default |
| Machine-level guardrails outside repo | `restricted = true` + `permissions.yaml` (allow/deny/confirm globs) | Command-approval layer + YOLO blocklist + **file-write denylist**; no glob allow/deny/confirm policy engine equivalent | ⚠️ partial — mitigations in §9 |
| Skills with bundled mutation scripts | `.forge/skills/<name>/SKILL.md` | Same `SKILL.md` format; repo-local directory registered as an external skill dir; `skills.write_approval: true`; agent self-editing of pipeline skills forbidden (ADR 013) | ✅ format-identical |
| MCP read-only for Tier 1, server-side enforced | `.mcp.json`; permissions.yaml does not govern MCP | Hermes MCP config; approvals do not govern MCP either (issue #16462 open) | ✅ unchanged stance — ADR 014's server-side enforcement was already the only real layer |
| `AGENTS.md` injection | automatic | automatic (context files) | ✅ |
| Bounded loops | `max_turns`, `max_requests_per_turn`, `max_tool_failure_per_turn` | Hermes equivalents to be enumerated and pinned | ⏳ M2 |
| Tool-id verification & pinning | `:tools` (register #45) | Hermes toolset enumeration equivalent; **this plan deliberately does not guess toolset ids** — pin via the register #45 pattern (enumerate twice on the operator machine, pre/post provider setup) | ⏳ M2 |
| Version pin + auto-update off | README pin + `[updates] auto_update = false` (register #46) | Pin Hermes release in README; disable its auto-update equivalent | ⏳ M2 (config key) |

**Top-level agent caveat (the material regression).** ForgeCode agents receive no tools by default; every role, including the interactive session, is an allowlisted definition. In Hermes, construction-time toolset enforcement applies to **delegates**; the top-level session agent retains broad tools and cannot (as of research date) be config-stripped to a hard allowlist. Consequences and mitigations in §9.

**Memory doctrine.** Hermes memory (silent-by-default learning) is constitutionally incompatible with pipeline determinism (ADR 007 text-grounded evaluation; prompts loaded from `docs/` at runtime). Bootstrap config MUST set `skills.write_approval: true` and either `memory_enabled: false` or `memory.write_approval: true` for any profile used on Foundry work. Delegates being memory-blind by construction is **desirable here** — note the community pressure to reverse it (issue #30269): if a future release injects parent memory into delegates, re-verify isolation before upgrading (watch item, §9).

## 5. Model and inference-billing plan (two surfaces)

Foundry consumes models on two distinct surfaces; conflating them is the external blueprint's core billing error.

1. **Surface 1 — interactive harness sessions** (Conductor-analogue planning, Tier-2-style delegate runs, Phase 6 agent work): **SuperGrok subscription via sanctioned `xai-oauth`** (~$30/mo, grok-4.3). Known caveat: intermittent 403 tier-allowlist bug for some SuperGrok subscribers (Hermes issue #26847) — verify in M2.
2. **Surface 2 — script-level structured-output API calls** (`run_discover.py`, `run_draft.py`, `run_review_base.py`, `run_fix_base.py`; register #39; `FOUNDRY_DISCOVERER_BASE_URL`): **unchanged by this migration.** Consumer subscriptions do not cover programmatic API calls. Register #47 (provider selection) remains open, with candidates: (a) xAI API, PAYG with a hard spend cap — verify grok-4.3's JSON-schema structured-output mode against `ClassificationResult` in M2; (b) another frontier PAYG API with a hard cap; (c) the already-planned local vLLM/Outlines serving spike. Walking-skeleton volume (one chapter) makes a capped PAYG budget small; measure in M3.

**Prohibited paths (recorded so they are never "discovered" later):** `hermes proxy`, CLIProxyAPI, codex-proxy, and all OAuth-token relay/proxy patterns. Rationale: provider ToS prohibit credential piggybacking; Google suspended entire accounts for OAuth-proxying (Feb 2026); Anthropic blocks subscription tokens outside Claude Code (Jan–Feb 2026); the "wrap Gemini CLI" route for Google AI Pro is additionally **dead** — Google ended Gemini CLI consumer AI Pro/Ultra auth on 2026-06-18. The Operator's Google AI Pro subscription stays for personal Antigravity use; it plays no role in this pipeline.

## 6. ADR impact analysis (all 17, verified against HEAD `99bd589`)

| ADR | Disposition | Required action |
| --- | --- | --- |
| 001, 005, 006, 007, 008, 009, 010, 011, 015 | **Unaffected** | None. "Forge" mentions in 001/004/009/010 are the *historical orchestrator concept*, already redirected by the glossary's historical note — not the ForgeCode product. ADR 011 stays satisfied per register #39 (provider-side JSON-schema modes now; local vLLM/Outlines later). |
| 002 | **Unaffected** | Immutability/copy-on-write rules are harness-independent. |
| 003 | **Unaffected in substance** | Extraction stays a plain reviewed script with no LLM client imports. Explicitly do **not** route extraction through Hermes `execute_code` (blueprint's proposal) — the agent must not re-enter a phase designed to exclude it. One test glob updates (§7). |
| 004 | **Unaffected** | "Forge Independence" = orchestrator-concept independence; the principle transfers verbatim. |
| 012 | **Amend (substantial)** | Re-express tiers in Hermes primitives per §4: delegate-profile allowlists (layer 1), file-write denylist + command approvals replacing restricted-mode/permissions.yaml (layer 2), script validation unchanged (layer 3). New caveats: top-level agent breadth; container backends bypass command approvals **by documented design** (non-container backend required for approval enforcement, or the bypass is explicitly accepted and documented); MCP approval bypass (#16462) — reaffirms ADR 014. Memory doctrine (§4) added. |
| 013 | **Amend (light)** | `.forge/skills/` → repo-local skills directory (recommend harness-neutral `skills/` — this migration's own lesson: harness-branded paths cost renames later) registered as a Hermes external skill directory. Add: `skills.write_approval: true` mandatory; pipeline skill definitions remain immutable — changes only via reviewed commits. |
| 014 | **Amend (light)** | Note Hermes MCP approval bypass (#16462): server-side read-only endpoints/credentials remain the only enforcement layer — stance unchanged, now doubly load-bearing. Hermes MCP-*server* mode noted as out of scope. |
| 016 | **Superseded** | Status header edited to "Superseded by ADR 018" when 018 lands. File retained (house rule: ADRs are never deleted). |
| 017 | **Amend (light, references only)** | §Context and triggers reference ForgeCode by name (v1 "interactive ForgeCode session"; v2 option (a) "shelling into ForgeCode agents headlessly"; the ADR 016 Open Item). Name-swap to Hermes + repoint to ADR 018. **Sequencing substance unchanged.** The v2 driver may study Hermes Kanban's dispatch patterns, but any driver issues transitions only through the ledger scripts. |
| **018 (new)** | **Create** | "Adopt Hermes Agent as the agent harness (supersedes ADR 016)." House format. Records: role boundaries retained (§1), version-pin requirement retained (register #46 pattern), sanctioned-auth-only rule (§5), the §4 enforcement re-mapping, and the M2 verification gate as an explicit acceptance precondition. |
| **019 (new, deferred)** | **Do not create yet** | "Operator gateway and messaging-triggered phase advancement" (Telegram/WhatsApp triggers → ledger scripts; gate notifications; phone-based QUARANTINE approvals; cron watchdog integrity checks). Out of walking-skeleton scope; draft only when adopted, after the skeleton proves out. Listed here so the roadmap is on record. |

## 7. Non-ADR file impact (grep-verified inventory)

| File | Refs | Required change (executed in M1, not now) |
| --- | --- | --- |
| `AGENTS.md` | 5 | Rule 11 rewritten: Hermes toolset vocabulary (pinned via M2, register #45 pattern), delegate-profile semantics, memory/write_approval doctrine. Rule 14: ADR 016 → 018. Vocabulary: "The harness is **ForgeCode**" → **Hermes Agent**. Keep the ~110-line density rule (register #33 — Hermes also injects AGENTS.md per session). |
| `README.md` | 2 | Harness sentence + link; version-pin block → Hermes release + auto-update-off discipline; repo-map rows (this plan; ADR 018). |
| `docs/constitution.md` | 7 | §5 rewritten around Hermes guardrail mechanisms (same skeleton as the 2026-07-07 ForgeCode rewrite: machine-level guardrails as bootstrap prerequisite, server-enforced MCP read-only, state isolation, progressive disclosure). "Harness ≠ Pipeline Driver" retained verbatim with name swap. |
| `docs/ubiquitous-language.md` | 6 | ForgeCode entry → Hermes Agent, extending the existing historical note (Forge → ForgeCode → Hermes). Tier 1/Tier 2 entries: tool ids updated after M2 pinning. Conductor (drop the `muse` analogue; define against Hermes read-only delegate profile). Operator: "ForgeCode CLI" → Hermes CLI/gateway. |
| `docs/implementation-plan.md` | 10 | Phase 0 table rewritten (see M2). Skill paths `.forge/skills/foundry-*` → `skills/foundry-*`. Phase 6: `.forge/agents/` → Hermes delegate-profile definitions + runbook + config bootstrap. |
| `docs/decision-register.md` | 3 | Append section 10 (see M1 list). Entries #45/#46 are ForgeCode-specific: superseded by new entries, never rewritten (append-only culture). #33 gains a parenthetical (Hermes injection). |
| `tests/test_adr_compliance.py` | 1 | Line 75: ADR 003 AST-scan glob `.forge/skills/*extract*/**/*.py` → `skills/*extract*/**/*.py`. The **only code change** in the migration; all three gates re-run. |
| `.gitignore` | 0 | Verify in M2 whether any Hermes runtime files land in-repo (none expected: `~/.hermes/` is home-scoped; `.skills-data/` rule already covers runtime artifacts). |
| `docs/pipeline-ledger.md`, `Foundry.md`, `docs/taxonomy.md`, axioms/predicates, `docs/ontology.md`, `docs/schema-explanation.md`*, all `schemas/*.py`, all other tests, `pyproject.toml`, `LICENSE` | 0 product refs | **No change.** (*`schema-explanation.md`'s "Forge Orchestrator" = historical concept; optionally sweep in M1 for consistency.) |

## 8. Implications

**Positive.**
- Development-time inference for interactive work on a fixed ~$30/mo sanctioned subscription; harness itself free and open-source; no metered surprises on surface 1.
- Ops roadmap unlocked (gateway triggering, phone approvals mapped to the Operator's QUARANTINE authority, cron watchdog for nightly ledger-integrity checks) behind a future, bounded ADR 019.
- Skill format continuity (`SKILL.md`/agentskills.io) — specifications port as-is, and remain portable *away* from Hermes (exit-cost hedge; the format is the industry standard, also native to Claude Code).
- Migration touches zero schemas and one test glob; the walking-skeleton scope (register #40) is unaffected.

**Negative / accepted risks (with mitigations).**
1. **Top-level agent breadth** (§4): tier isolation is preserved for pipeline roles *only if* they run as delegate profiles. Mitigations: pipeline roles run exclusively as delegates with enforced toolsets; interactive sessions run with command approvals ON on a **non-container backend** (container backends disable command approvals by documented design); file-write denylist covers `.skills-data/**` so direct state writes are machine-refused even for the top-level agent; layer 3 (script validation + ledger preconditions) is unchanged and remains the only fully repo-controlled layer — exactly as ADR 012's consequences already state.
2. **No glob allow/deny/confirm policy engine.** ForgeCode's `permissions.yaml` had no full Hermes equivalent; approvals are interactive. Consequence: ADR 012's existing caveat hardens into a rule — **no unattended execution** until the M2-verified approval posture is documented (and ADR 019, when drafted, must solve decisive policy termination for gateway-triggered runs).
3. **Project youth and release cadence.** Hermes is ~5 months old with weekly releases; semantics may move under the pin. Mitigation: register #46 discipline carries over verbatim (pin → deliberate updates → re-enumerate toolsets → diff → amend pin and register in the same commit).
4. **Single-vendor coupling for interactive quality** (grok-4.3). Bounded: gate-review quality rides surface 2 (register #47), not the harness subscription.
5. **Memory/self-improvement defaults are anti-constitutional** and must be configured off/gated (§4) as part of the M2 bootstrap — config is part of the guardrail bootstrap doc, mirroring ADR 012's "machine-level configuration outside the repository" consequence.

**Watch items (re-verify before any Hermes upgrade):** #30269 (delegate memory isolation — a "fix" would inject parent memory into delegates), #16462 (MCP approval gap), #26847 (SuperGrok 403s), leaf-delegate force-stripped toolsets vs. Tier-2 shell needs (M2 item 1).

## 9. Migration sequence

- **M0 (this commit):** This plan document only. No other repo change.
- **M1 (one coherent commit series, after Operator sign-off on this plan):** Author ADR 018; amend ADRs 012/013/017 (+ status header on 016); update AGENTS.md, README, constitution §5, glossary, implementation plan; fix the test glob; append register section 10: **#47** (surface-2 provider selection, or explicit deferral with cap), **#48** (harness re-selection decision + research provenance), **#49** (Hermes governance bootstrap posture: write_approval, memory, backend/approval mode, denylist, sanctioned-auth-only), **#50** (watch items above). Gates green (`ruff`, `mypy schemas/`, `pytest`).
- **M2 (operator machine, ~1–2 h — Phase 0 rerun, Hermes edition):** Install + pin Hermes; disable auto-update; enumerate toolsets twice (register #45 pattern) and pin ids; `xai-oauth` login and #26847 check; **verify a shell-capable, memory-blind delegate profile can run a bundled script end-to-end** (make-or-break item 1); verify file-write denylist blocks a direct `.skills-data/` write; verify approval prompts fire on the chosen backend; verify grok-4.3 JSON-schema structured output against `ClassificationResult` (surface 2 candidate); bank all results as register entries.
- **M3:** Resume `docs/implementation-plan.md` Phase 1 (ledger core library) — unchanged by this migration.

**Fallback checkpoint.** If any make-or-break M2 item fails, the documented fallback is: remain on ForgeCode 2.13.16 (ADR 016 stands; this plan is archived with the failure recorded in the register) with a hard-capped PAYG key for both surfaces — or escalate to the research runner-up (Claude Code + Max) via a fresh ADR. The fallback exists so this migration is a reversible, evidence-gated step, not a leap.

## 10. Rejected alternatives (recorded)

| Option | Why rejected |
| --- | --- |
| OAuth proxy layers (CLIProxyAPI, codex-proxy, `hermes proxy`) | ToS violations; Google account suspensions (Feb 2026); Anthropic token blocks; Gemini CLI consumer path dead (2026-06-18). |
| Hermes Kanban as pipeline driver (external blueprint's thesis) | Second sequencing authority; violates constitution / ADR 016 boundary 1 / ADR 017 / AGENTS.md rule 14. Kanban lacks the ledger's append-only, flock, sha256-witness, copy-on-write guarantees. Patterns may inform the v2 driver *through* ledger scripts. |
| Client-side Outlines "logit-level" enforcement on remote models (blueprint) | Technically impossible — remote endpoints expose no logits. Provider-side JSON-schema modes (register #39) and the local vLLM/Outlines spike already cover both real mechanisms. Named skill does not exist. |
| Antigravity (+ Google AI Pro) as harness | Open permission-enforcement bug (SDK #65: subagent tool/MCP flags accepted but unenforced); compute-weighted quota lockouts; closed-source. Stays as the Operator's personal IDE. |
| Claude Code + Claude Max | Research runner-up; strongest permission engine; ~$100+/mo and no gateway/ops layer. Named fallback (§9). |
| OpenCode | Subscription sign-in removed by maintainers (Mar 2026) after provider bans; API-key-only in practice. |
| ForgeCode + capped PAYG (status quo) | Viable and capability-verified; loses on dev-cost model and offers no ops roadmap. Named fallback (§9). |

## 11. Research provenance and open items

Decision basis: web-verified research conducted 2026-07-15 (five-agent harness-landscape survey; three Hermes deep-dive passes; claim-by-claim verification of the external blueprint) against official sources — `hermes-agent.nousresearch.com` docs (note: `hermes-agent.ai` is an unaffiliated SEO site), the NousResearch/hermes-agent repository (issues/PRs cited by number above), `x.ai/news/grok-hermes`, xAI model docs, and Google's Gemini CLI deprecation notices. Full research notes live in the project workspace outside this repository.

Anything marked ⏳ in §4, plus the M2 checklist in §9, is **deliberately unpinned** here: per this repository's own discipline (register #45–#46), runtime facts are pinned from hands-on verification on the operator machine, not from documentation reading.
