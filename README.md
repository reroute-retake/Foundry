# Foundry

**An AI-assisted knowledge refinement pipeline.** Foundry transforms books, PDFs, and study materials into an atomic, graph-linked knowledge base — treating structured JSON as the canonical artifact and Markdown (Obsidian/OKF) as a disposable rendered view.

> **Status: architecture complete, pre-implementation.** The contracts below are normative; implementation code lands next.

## How it works

```
Source Material ─▶ Extracted Text ─▶ Topic Metadata ─▶ Knowledge Draft
      (deterministic)    (Discoverer)       (Author)          │
                                                     Gate 1: Review ⇄ Fix
                                                              ▼
   Rendered Views ◀─ MOCs ◀─ CANONICAL ◀─ Gate 2 ◀─ Enrich ◀─ Link ◀─ VALIDATED
     (OKF Bundle)                (Review ⇄ Fix)
```

Nine phases, two frontier-review gates, sequenced by a script-enforced **Pipeline Ledger** — no LLM ever dictates workflow. Agents run on the [Hermes Agent](https://github.com/NousResearch/hermes-agent) harness with tiered tool scoping; all state mutations flow through deterministic, Pydantic-validating Python scripts.

- **Harness:** [Hermes Agent](https://github.com/NousResearch/hermes-agent) v0.18.2, pinned to upstream commit `e0e7cfa6` (2026-07-16). The git installer tracks `main`, so the **sha is the pin** — verify with `hermes --version`, install reproducibly with the installer's `--commit` flag, and never run `hermes update` casually (updates are deliberate events: register #50). Runtime machines additionally require the Constitutional Bootstrap config (register #49). Required by ADR 018 (supersedes ADR 016); see `docs/hermes-migration-plan.md`.

## Repository map

| Path | Contents |
| --- | --- |
| `Foundry.md` | Vision, design principles, pipeline overview |
| `docs/constitution.md` | Mission, non-goals, binding principles |
| `docs/ubiquitous-language.md` | The exact vocabulary — mandatory in all code and prompts |
| `docs/adr/` | 18 Architecture Decision Records (the "why") |
| `docs/taxonomy.md` · `docs/classification-predicates.md` · `docs/classification-axioms.md` | The 10-type classification system: canonical order, entry predicates, collision tie-breakers |
| `docs/pipeline-ledger.md` | Sequencing authority: state machine, preconditions, storage model |
| `docs/decision-register.md` | Ratified sub-ADR judgment calls with rationale and enforcement pointers |
| `docs/implementation-plan.md` | Phased walking-skeleton plan (Phase 0–7) with exit criteria |
| `docs/hermes-migration-plan.md` | ForgeCode → Hermes harness migration: rationale, ADR impact, spike verification |
| `schemas/` | Pydantic v2 contracts: `taxonomy.py`, `discoverer_schema.py`, `review.py`, `pipeline_ledger.py`, `enrichment.py`, `moc.py` |
| `AGENTS.md` | Binding rules for AI coding agents working in this repo |

**Read order for newcomers (human or agent):** `docs/constitution.md` → `docs/ubiquitous-language.md` → `Foundry.md` → `docs/pipeline-ledger.md` → the ADRs.

## Development setup

Requires Python ≥ 3.12.

```bash
# with uv (preferred)
uv sync
uv run python -c "import sys; sys.path.insert(0, 'schemas'); import taxonomy, discoverer_schema, pipeline_ledger; print('schemas OK')"

# or with pip
python3 -m venv .venv && source .venv/bin/activate
pip install -e . --group dev   # or: pip install pydantic pytest ruff mypy
```

Checks (once implementation lands): `uv run pytest` · `uv run ruff check .` · `uv run mypy schemas/`

## License

MIT — see [LICENSE](LICENSE).
