# System Ontology

The ontology defines the strict, immutable state machine of the Foundry pipeline. It maps the transition of unstructured bytes into a highly interconnected, enriched learning graph.

## The Knowledge Life Cycle (Double-Gated Two-Pass Pipeline)

1. **Extraction:** `Source Material` **Yields** deterministic `Extracted Text`.
    
2. **Discovery:** `Extracted Text` **Is Shredded Into** `Topic Metadata` (Entities).
    
3. **Ontological Drafting (Pass 1):** `Topic Metadata` **Is Synthesized Into** a `Base Knowledge Draft` (JSON).
    
4. **Ontology Review Gate:** A `Base Knowledge Draft` + `Review Report` **Are Resolved Into** a `Validated Base Node`.
    
5. **Linking (Pass 2):** `Validated Base Nodes` **Connect To** other nodes via formal `Graph Edges`.
    
6. **Enrichment (Pass 2):** A `Validated Base Node` + its `Edges` **Are Synthesized Into** `Pedagogical Artifacts` (Flashcards, Diagrams).
    
7. **Enrichment Review Gate:** The newly added edges and pedagogical artifacts **Are Reviewed and Resolved**, upgrading the payload to a finalized `Canonical Node`.
    
8. **Curation:** `Canonical Nodes` **Are Organized By** `Maps of Content (MOCs)`.
    
9. **Rendering:** The completed Graph **Is Projected As** human-readable `Rendered Views` (Markdown).
