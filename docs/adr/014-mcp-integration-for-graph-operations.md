# ADR 014: MCP Integration for Graph and Vector Operations

- **Date:** 2026-06-21
- **Status:** Accepted

## Context

The `Linker` role requires immense context to identify "Canonical IDs" across thousands of extracted JSON files. Asking the LLM to read raw files or relying solely on fuzzy grep/semantic search results in high latency and low accuracy.

## Decision

Foundry will integrate the Model Context Protocol (MCP) to manage graph traversal and memory.

1. **Discovery (Read):** Tier-1 agents will access read-only MCP tools (e.g., `mcp_neo4j_read-cypher` or `mcp_qdrant_find`) to surface highly accurate candidate nodes.
2. **Mutation (Write):** Write operations to the graph database will not be done via MCP LLM tools. They will remain deterministic, executed via Python scripts by Tier-2 agents.

## Consequences

- **Positive:** Offloads heavy search and relation-mapping context from the LLM to highly optimized databases (SQLite-vec, Neo4j, Qdrant).
- **Negative:** Adds architectural complexity, requiring the configuration and background execution of local MCP servers during a pipeline run.