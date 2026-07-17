---
name: foundry-discover
description: Run the Discoverer (first LLM stage) — classify topics from an EXTRACTED document into Topic Metadata via the structured-output endpoint, with verified evidence quotes and DISCOVER ledger transitions. Bounded retries; never work around a refusal or failure.
---

# foundry-discover

Turns Extracted Text into `DISCOVERED` nodes with schema-valid Topic Metadata.
The LLM emits only classifications; this script owns every fact: chunking,
canonical ids, provenance spans recovered from the source, and all ledger
transitions.

## Prerequisites

- The document is `EXTRACTED` (run `foundry-ingest` first; confirm with `foundry-status`).
- `<repo>/.env` (never committed) carries the surface-2 provider config —
  copy `.env.example` and fill in the prepaid, hard-capped key (register #47):
  `FOUNDRY_DISCOVERER_BASE_URL`, `FOUNDRY_DISCOVERER_API_KEY`,
  `FOUNDRY_DISCOVERER_MODEL`.

## Commands

```bash
python3 skills/foundry-discover/scripts/run_discover.py <document_id>
python3 skills/foundry-discover/scripts/run_discover.py <document_id> --max-chunks 2   # spot-check
```

Prints a one-line JSON summary (chunks, discovered, reified_ghosts, duplicates,
failed_chunks). Exit 0 with `"ok": false` means some chunks failed after bounded
retries — inspect `.skills-data/pipeline/discovery-failures.jsonl` and report to
the Operator. **Do not loop, retry manually beyond the script's own bounds, or
edit any `.skills-data/` file to "help".**

## Guarantees (enforced by the script, not by prompts)

- Every `evidence_quote` is verified against the chunk via `normalize_quote()`
  and the **recovered source span** (with its original markdown) is what gets
  stored in provenance (register #36/#43). Unverifiable quotes trigger the
  bounded retry, then the failures report — never a workaround.
- `DISCOVER` transitions go through the ledger write protocol; re-discovering
  an existing node is a benign dedupe; discovering a `GHOST` reifies it.
- At most 3 LLM attempts per chunk. The failures report is data for the eval
  set, not an error to suppress.
