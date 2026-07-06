# ADR 007: Deterministic Classification Decision Tree

- **Date:** 2026-06-21
- **Status:** Accepted

## Context

Large Language Models are probabilistic and will frequently trap rich structural concepts in shallow buckets if left unconstrained (e.g., misclassifying a cryptographic protocol as a generic "Tool"). This is known as "Richness Inversion."

## Decision

The `Discoverer` role must utilize a strict, sequentially inverted Decision Tree State Machine. The hierarchy must be evaluated from the lowest semantic entropy (Attack Vector) down to the highest (Concept). The LLM must output a Sequential Chain-of-Thought reasoning trace before evaluating a boolean condition for each level. The first `TRUE` locks the classification permanently.

## Consequences

- **Positive:** Eliminates early-cascade capture and guarantees ontological purity.
- **Negative:** Requires more tokens generated per classification due to the mandated reasoning traces.