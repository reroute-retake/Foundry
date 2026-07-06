# ADR 002: Immutability of Phase Outputs

* **Date:** 2026-06-20
* **Status:** Accepted

## Context
As AI refines text, replacing the previous iteration destroys the audit trail. If a note is malformed, it is impossible to know which LLM role caused the hallucination.

## Decision
Every phase in the Foundry pipeline must produce a net-new, immutable artifact. The Fixer does not overwrite the Draft; it generates a new Canonical Knowledge artifact alongside the Draft and Review Report.

## Consequences
* **Positive:** Flawless traceability and debugging. Enables precise prompt tuning. You can re-run a step without starting from scratch.
* **Negative:** Increased storage overhead for intermediate JSON files.
