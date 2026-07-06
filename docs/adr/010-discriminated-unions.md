# ADR 010: Pydantic v2 Discriminated Unions

- **Date:** 2026-06-21
- **Status:** Accepted

## Context

Standard Pydantic unions score schema matches based on field overlap. If an LLM hallucinates slightly, this results in massive tracebacks that Forge cannot parse for automated self-correction.

## Decision

The base extraction schema utilizes strict Tagged (Discriminated) Unions. The LLM must explicitly output a `primary_kind` literal (e.g., `"Algorithm"`). Pydantic uses this field to route validation in O(1) time.

## Consequences

- **Positive:** Generates highly specific, targeted validation errors (e.g., "Field 'time_complexity' missing in Algorithm schema"), enabling automatic LLM retry loops.
- **Negative:** The schema enforces strict model configuration (`extra='forbid'`), dropping any payload with stray fields.