# ADR 005: Enforcement of the Minimum Information Principle

- **Date:** 2026-06-21
- **Status:** Accepted

## Context

Standard AI summarization generates encyclopedic, monolithic notes that attempt to cover an entire chapter. These notes fail as learning tools because they exceed human working memory and trap semantic relationships inside blocks of text.

## Decision

Foundry strictly enforces the Minimum Information Principle.

1. **Context Independence:** A single artifact must answer exactly one question or describe one mechanism.
2. **Prohibition of Enumeration:** Lists must be broken down into individual atomic artifacts and linked via structure notes or edges.

## Consequences

- **Positive:** Optimizes artifacts for algorithmic parsing and mathematically superior spaced-repetition (flashcard) generation.
- **Negative:** Greatly increases the total node count in the graph, requiring robust Maps of Content (MOCs).