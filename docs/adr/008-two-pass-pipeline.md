# ADR 008: The Two-Pass Pipeline (Ontology vs. Enrichment)

- **Date:** 2026-06-21
- **Status:** Accepted

## Context

Forcing an LLM to extract highly dense ontological facts while simultaneously generating complex pedagogical artifacts (like Mermaid.js diagrams and spaced-repetition flashcards) exhausts its context window and causes schema hallucination. Furthermore, if pedagogical artifacts are generated simultaneously with the base ontology, hallucinations in the base facts will infect the generated flashcards and graph edges.

## Decision

The pipeline executes in two strict phases, each protected by an independent Expert Review & Resolution Gate:

1. **Pass 1 (Ontological Extraction):** The `Author` extracts the base JSON schema. Pedagogical fields are forbidden.
    
    - **Gate 1:** The `Reviewer` and `Fixer` critique and repair the base facts.
        
2. **Pass 2 (Pedagogical Enrichment & Linking):** An asynchronous `Enricher` and `Linker` query the validated base node to generate visual diagrams, flashcards, and semantic edges.
    
    - **Gate 2:** The `Reviewer` and `Fixer` critique the newly appended pedagogical and relational data to ensure no hallucinations leaked into the flashcards or graph connections. The node is then locked as "Canonical."
        

## Consequences

- **Positive:** Prevents schema hallucinations, ensures diagrams are based on mathematically validated facts, and guarantees that no AI-generated content (including flashcards and links) enters the Canonical Graph without frontier-model validation.
    
- **Negative:** Increases pipeline latency and compute costs by requiring two distinct review/fix cycles per node.