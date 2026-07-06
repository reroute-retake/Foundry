# Foundry Note Taxonomy

To eliminate MECE (Mutually Exclusive, Collectively Exhaustive) violations, all extracted entities must map to exactly one of these 10 categories.

## The 10 Canonical Note Types (Canonical Evaluation Order)

The numbering below is the **canonical evaluation sequence** mandated by ADR 007: the Discoverer evaluates levels 1 → 10, from lowest to highest semantic entropy, and the first `TRUE` locks the classification permanently. Every listing, schema, and prompt in this repository must preserve this exact order (`schemas/discoverer_schema.py` is the machine-readable source of truth).

1. **Attack Vector**: A malicious exploit or vulnerability used by an adversary. (e.g., _SQL Injection_).
2. **Mitigation**: A specific remediation procedure or defense mechanism to resolve a Failure Mode or block an Attack. (e.g., _Rate Limiting, Circuit Breaker_).
3. **Data Structure**: A specialized format for organizing and storing physical bytes. (e.g., _Write-Ahead Log, Bloom Filter_).
4. **Algorithm**: A finite sequence of rigorous, step-by-step logical instructions. Must include complexities. (e.g., _Two-Phase Commit_).
5. **Pattern**: A topological layout, structural design, or reusable architectural blueprint. (e.g., _Leaderless Replication_).
6. **Failure Mode**: An operational breakdown, error state, or systemic collapse. (e.g., _Split-Brain, Deadlock_).
7. **Interface**: A shared boundary or protocol specification between systems. (e.g., _REST, gRPC_).
8. **Metric**: A quantifiable measure, formula, or diagnostic constraint. (e.g., _P99 Latency, Quorum w+r>n_).
9. **Tool**: A concrete, deployable software implementation or platform. (e.g., _PostgreSQL, Kafka_).
10. **Concept**: A theoretical invariant, foundational principle, or paradigm. (e.g., _Eventual Consistency, ACID_).