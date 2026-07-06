# Classification Predicates (The 10 Level Criteria)

This document defines the **positive entry predicate** for each level of the Discoverer's decision tree. The canonical evaluation order and first-`TRUE`-locks semantics are mandated by ADR 007 and mirrored in `docs/taxonomy.md` and `schemas/discoverer_schema.py`. The tie-breakers in `docs/classification-axioms.md` resolve collisions between levels; each axiom is **enforced at the earlier level** of its pair (its discipline is built into that level's predicate) and echoed at the later level.

## Global Evaluation Rules

1. **Sequential Lock (ADR 007):** Evaluate Levels 1 → 10 in the canonical order. The first `TRUE` locks the classification permanently. No lookahead, no revision.
2. **Entity Locus:** Predicates apply to the extracted entity itself — never to entities merely mentioned in its context. Text about Rate Limiting mentions DoS attacks; the entity is the defense, so Level 1 is `FALSE` and Level 2 is `TRUE`.
3. **Text-Grounded Evaluation:** Evaluate what the source text presents the entity *as*. World knowledge may calibrate understanding but never substitutes for textual evidence, and no property absent from the text may be invented (ADR 003).
4. **Deferral Discipline:** When a "Defer when" clause fires, emit `condition_met: false` and continue to the next level. The clause names where the entity will correctly lock.
5. **Dual-Nature Tie-Break:** When an entity legitimately embodies two natures (e.g., a protocol that is also a product), the sequential order *is* the tie-break by design. The first `TRUE` wins; do not deliberate beyond the predicates.

---

## Level 1 — Attack Vector

**Predicate:** `TRUE` iff the text presents the entity as an offensive technique — a crafted payload, input, or procedure used by an adversary to violate a system's intended contract.

- **All of:** (a) deliberate adversarial agency — the mechanism is alien to intended use (Axiom 4); (b) the entity **is** the offensive technique itself.
- **Defer when:** the breakdown emerges organically from normal operation → Level 6 (Failure Mode); the entity is the *defense* against an attack → Level 2 (Mitigation).
- **Minimal pair:** `TRUE`: "SQL Injection — attacker-crafted query fragments in user input execute unintended SQL." / `FALSE`: "Retry storms amplify load until the cluster collapses" → organic genesis → locks at Level 6.
- **Axioms in force:** #4 (Trigger Genesis).

## Level 2 — Mitigation

**Predicate:** `TRUE` iff the text presents the entity as a defense mechanism that consumes a dynamic threat, load, or failure signal as an explicit runtime input and gates execution — throttling, dropping, blocking, isolating, or rejecting — to protect the system.

- **All of:** (a) declared protective or remedial purpose against a threat, overload, or fault; (b) a dynamic signal consumed at runtime (Axiom 2); (c) the action is a gate on execution or traffic.
- **Defer when:** the mechanism computes a transformation irrespective of external pressure → Level 4 (Algorithm); the defense is a *static structural arrangement* consuming no runtime signal (e.g., Bulkhead partitioning) → Level 5 (Pattern); the entity only *measures* without gating → Level 8 (Metric).
- **Minimal pair:** `TRUE`: "Rate Limiting — drops requests when arrival rate exceeds a threshold." / `FALSE`: "Merkle-tree anti-entropy repair reconciles replica differences on a schedule, regardless of load" → unconditional computation → Level 4.
- **Axioms in force:** #2 (Threat-Signal Gating).

## Level 3 — Data Structure

**Predicate:** `TRUE` iff the text presents the entity as the invariant arrangement of data at rest — the concrete organizational geometry (fields, buckets, trees, logs, rings, tables) whose layout invariants hold independent of any operation sequence.

- **All of:** (a) concrete bit/byte/record layout with stated invariants; (b) defined at the storage-arrangement level, regardless of whether that storage is local or distributed (Axiom 1 — a Distributed Hash Table is a Data Structure).
- **Defer when:** the text defines the active transformation or traversal *over* the arrangement → Level 4 (Algorithm, Axiom 5); it defines a choreography of roles agnostic to physical storage → Level 5 (Pattern, Axiom 1).
- **Minimal pair:** `TRUE`: "Write-Ahead Log — an append-only record sequence persisted before page writes." / `FALSE`: "B-tree rebalancing after insertion" → active transformation → locks at Level 4.
- **Axioms in force:** #1 (Structural Autonomy), #5 (Temporal State).

## Level 4 — Algorithm

**Predicate:** `TRUE` iff the text presents the entity as a finite, ordered sequence of steps transforming defined inputs to defined outputs — expressible as the decision sequence of a **single logical actor**, treating other parties as message sources and sinks.

- **All of:** (a) step-by-step executable logic with a start, an end, and a termination condition; (b) single-logical-actor expressibility, even when embedded in a larger distributed system (Axiom 3 — Two-Phase Commit is the *coordinator's* sequence).
- **Defer when:** the entity fundamentally *is* the arrangement of multiple distinct roles rather than any one actor's script → Level 5 (Pattern, Axiom 3); the entity is a formula or constraint with no procedure → Level 8 (Metric).
- **Minimal pair:** `TRUE`: "Two-Phase Commit — the coordinator sends prepare, collects votes, decides, broadcasts the outcome." / `FALSE`: "Leaderless Replication — any replica accepts writes; readers query several replicas" → mandated multi-role arrangement → locks at Level 5.
- **Axioms in force:** #3 (Actor Boundary), #5 (Temporal State), #2 (already enforced at Level 2 — anything reaching this level is not signal-gated).

## Level 5 — Pattern

**Predicate:** `TRUE` iff the text presents the entity as a reusable arrangement of two or more cooperating roles or components — who talks to whom, what is placed where — agnostic to physical storage layout and to any single actor's step sequence.

- **All of:** (a) mandates ≥ 2 distinct roles/components and their relationship or message flow (Axiom 3); (b) an instantiable blueprint, not a named product.
- **Defer when:** the entity isolates the precise interaction contract at **one seam** (verbs, message shapes, headers, encodings) without prescribing the surrounding arrangement — a **pure single-seam contract is NOT a Pattern** → Level 7 (Interface, Axiom 6); concrete byte geometry → would have locked at Level 3; a breakdown state → Level 6; a deployable product → Level 9.
- **Minimal pair:** `TRUE`: "Publish/Subscribe — a broker routes messages from publishers to subscribing consumers." / `FALSE`: "gRPC — the contract for typed RPC calls over HTTP/2" → single-seam contract → survives to lock at Level 7.
- **Axioms in force:** #6 (Boundary Contract), #3 (Actor Boundary), #1 (Structural Autonomy).

## Level 6 — Failure Mode

**Predicate:** `TRUE` iff the text presents the entity as a distinct degraded or broken system **state or event** that emerges organically from operation — thresholds breached, resources exhausted, coordination lost — without adversarial crafting.

- **All of:** (a) the entity is the failure state/event itself, with how it manifests; (b) organic genesis under normal operational flow (Axiom 4 — adversarial genesis locked at Level 1).
- **Defer when:** the entity is a continuous measurable *quantity* whose magnitude degrades service rather than a discrete broken state → Level 8 (Metric).
- **Minimal pair:** `TRUE`: "Split-Brain — two partitions each elect a leader and accept conflicting writes." / `FALSE`: "Replication Lag — the time delta between leader and follower state" → a quantity → locks at Level 8.
- **Axioms in force:** #4 (Trigger Genesis).

## Level 7 — Interface

**Predicate:** `TRUE` iff the text presents the entity as the precise interaction contract at a single boundary between parties — operations, message shapes, encodings, headers, status semantics, invocation rules — that both sides must honor.

- **All of:** (a) exactly one seam (Axiom 6); (b) the entity is the normative contract, independent of any particular implementation.
- **Defer when:** the text describes the routing logic or arrangement of systems *around* the boundary → would have locked at Level 5 (Axiom 6); the entity is a named product that merely *implements* a contract → Level 9 (Tool) — "the PostgreSQL wire protocol" is an Interface; "PostgreSQL" is a Tool.
- **Minimal pair:** `TRUE`: "REST — resource-oriented operations expressed through HTTP verbs and status semantics." / `FALSE`: "An API gateway routing requests across microservices" → arrangement around boundaries → Level 5.
- **Axioms in force:** #6 (Boundary Contract).

## Level 8 — Metric

**Predicate:** `TRUE` iff the text presents the entity as a quantifiable measure — a named quantity with a unit or dimension, a formula, or a diagnostic constraint or inequality used to evaluate or bound system behavior.

- **All of:** (a) quantification is the entity's essence (number, ratio, distribution, inequality); (b) a unit, mathematical formalism, or well-defined measurement procedure is stated.
- **Defer when:** the entity is the *procedure* that enforces or optimizes the quantity → would have locked at Level 2 or 4; the entity is the broken *state* reached when the quantity degrades → would have locked at Level 6.
- **Minimal pair:** `TRUE`: "Quorum constraint w + r > n." / `FALSE`: "Load shedding drops requests when P99 exceeds the SLO" → signal-gated defense → Level 2.
- **Axioms in force:** none original — boundaries inherited from Levels 2, 4, 6.

## Level 9 — Tool

**Predicate:** `TRUE` iff the text presents the entity as a concrete, named, deployable software artifact, platform, or service — something that can be installed, executed, or subscribed to, with implementation identity (vendor, versions, runtime).

- **All of:** (a) proper-noun product identity; (b) deployable, executable existence.
- **Defer when:** the entity is the abstract mechanism a product implements (extract the mechanism as its own entity per Entity Locus); the entity is a non-deployable principle or guarantee → Level 10 (Concept). Note: entities that are both contract and product (e.g., gRPC) lock at Level 7 by sequential order — this matches `docs/taxonomy.md`'s examples and Global Rule 5.
- **Minimal pair:** `TRUE`: "PostgreSQL — a relational database server." / `FALSE`: "Eventual Consistency" → not deployable → locks at Level 10.
- **Axioms in force:** none original — order resolves the Interface overlap.

## Level 10 — Concept (Terminal Accumulator)

**Predicate:** `TRUE` iff the text presents the entity as a theoretical invariant, principle, property, guarantee, model, or paradigm — a knowledge unit that holds independent of any particular layout, procedure, arrangement, contract, or product.

- **All of:** (a) an abstract technical knowledge unit (property, guarantee, principle, theorem, paradigm); (b) Levels 1–9 all evaluated `FALSE`.
- **Terminal role:** Concept is deliberately permissive — any genuine technical entity that survives Levels 1–9 belongs here. Non-entities (prose fragments, publisher boilerplate) must be filtered *upstream* during entity isolation: `ClassificationResult` offers no "not an entity" outcome by design.
- **Minimal pair:** `TRUE`: "Eventual Consistency — the guarantee that, absent new writes, all replicas converge." / (Contrast: "Kafka" never reaches this level — it locks at Level 9.)
