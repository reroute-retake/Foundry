# ADR 003: Deterministic Document Extraction

* **Date:** 2026-06-20
* **Status:** Accepted

## Context
LLMs with large context windows can summarize PDFs directly, but they frequently skip dense data, hallucinate numbers, or silently drop paragraphs.

## Decision
The Extraction phase must use purely deterministic tools (Marker, Docling, MarkItDown). Generative AI is forbidden in Phase 1.

## Consequences
* **Positive:** Eliminates "Day 0" hallucinations. The downstream pipeline always works from complete, grounded text.
* **Negative:** The Extracted Text may contain OCR errors, weird line breaks, or artifacts that the Discoverer model must be robust enough to ignore.
