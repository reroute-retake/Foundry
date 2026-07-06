# ADR 011: Constrained Decoding and Grammar-Compiled FSMs

- **Date:** 2026-06-21
- **Status:** Accepted

## Context

Zero-shot LLMs (specifically 14B–32B local models) suffer from instruction amnesia and context rot when forced to evaluate complex, multi-level state machines. Relying on prompt engineering and post-generation Python validation results in high hallucination rates and latency-inducing retry loops.

## Decision

The `Discoverer` phase will abandon open-ended text generation. It must utilize Constrained Decoding (via frameworks like Outlines, XGrammar, or vLLM guided decoding). The JSON schema will be compiled into a strict Finite State Machine (FSM) that masks token probabilities in real-time, physically preventing the LLM from sampling invalid sequence outputs.

## Consequences

- **Positive:** Mathematically guarantees 100% adherence to the taxonomy and decision tree, completely offloading the ruleset from the LLM's fragile attention mechanism to the deterministic inference backend.
- **Negative:** Heavily restricts the choice of LLM serving infrastructure to those that explicitly support fast guided decoding.