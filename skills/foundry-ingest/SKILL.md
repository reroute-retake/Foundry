---
name: foundry-ingest
description: Register and extract Source Material into the Foundry Pipeline Ledger. Deterministic only (ADR 003) — run the bundled scripts via the terminal; never create or edit ledger state by hand.
---

# foundry-ingest

Brings a Source Material file (v1: one markdown chapter) into the pipeline as
Extracted Text, recorded in the Pipeline Ledger. Two steps, two scripts, both
deterministic — no LLM is involved at any point in ingestion (ADR 003).

## Commands

```bash
# 1. REGISTER — record the document and its content hash
python3 skills/foundry-ingest/scripts/register_document.py works/sources/<chapter>.md

# 2. EXTRACT — markdown identity transform (copy + hash) → Extracted Text artifact
python3 skills/foundry-ingest/scripts/extract_document.py works/sources/<chapter>.md
```

Both print a one-line JSON result. On refusal they exit 1 with a structured
error on stderr — **do not retry, rephrase, or work around a refusal**; report
it to the Operator. Refusals you may see:

- `ALREADY_REGISTERED` / `ALREADY_EXTRACTED` — the ledger is append-only (ADR 002)
- `SOURCE_CHANGED` — the file was modified after registration; re-register under a new id
- `UNSUPPORTED_FORMAT` — v1 ingests markdown only (register #40)

## Rules

- All outputs land under `.skills-data/` (documents/<id>/extracted_text.md);
  this skill's own directory is immutable at runtime (ADR 013).
- The document id is derived deterministically from the filename
  (snake_case, ≤64 chars); `--document-id` overrides it when the Operator says so.
- The extracted artifact's sha256 provably equals the source hash (identity
  transform, hash-what-you-write — register #41).
