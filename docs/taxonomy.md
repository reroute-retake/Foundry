# Foundry Note Taxonomy

To eliminate MECE (Mutually Exclusive, Collectively Exhaustive) violations, all extracted entities must map to exactly one of these 10 categories.

## The 10 Canonical Note Types

1. **Concept**: A theoretical invariant, foundational principle, or paradigm. (e.g., _Eventual Consistency, ACID_).
2. **Algorithm**: A finite sequence of rigorous, step-by-step logical instructions. Must include complexities. (e.g., _Two-Phase Commit_).
3. **Pattern**: A topological layout, structural design, or reusable architectural blueprint. (e.g., _Leaderless Replication_).
4. **Data Structure**: A specialized format for organizing and storing physical bytes. (e.g., _Write-Ahead Log, Bloom Filter_).
5. **Tool**: A concrete, deployable software implementation or platform. (e.g., _PostgreSQL, Kafka_).
6. **Interface**: A shared boundary or protocol specification between systems. (e.g., _REST, gRPC_).
7. **Metric**: A quantifiable measure, formula, or diagnostic constraint. (e.g., _P99 Latency, Quorum w+r>n_).
8. **Failure Mode**: An operational breakdown, error state, or systemic collapse. (e.g., _Split-Brain, Deadlock_).
9. **Attack Vector**: A malicious exploit or vulnerability used by an adversary. (e.g., _SQL Injection_).
10. **Mitigation**: A specific remediation procedure or defense mechanism to resolve a Failure Mode or block an Attack. (e.g., _Rate Limiting, Circuit Breaker_).