# ADR 001: Structured JSON as the Canonical Source of Truth

* **Date:** 2026-06-20
* **Status:** Accepted

## Context
Traditional PKM (Personal Knowledge Management) systems treat human-readable Markdown as the primary database. This leads to inconsistent formatting, broken links, and makes programmatic analysis extremely difficult.

## Decision
All knowledge must be stored in strongly-typed JSON objects (Canonical Knowledge). Markdown is strictly a view layer generated from this JSON.

## Consequences
* **Positive:** Allows multiple output formats (Obsidian, flashcards, websites) from a single source. Guarantees structural consistency. Enables Forge to use programmatic validation.
* **Negative:** Requires a rendering step before a human can read the notes comfortably.
