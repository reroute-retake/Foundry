# Deterministic Classification Axioms

The `Discoverer` agent relies on 6 absolute, structure-bound tie-breakers to resolve ontological collisions. These rules must be injected into the Discoverer's prompt as "minimal pairs" to calibrate the LLM's understanding without causing instruction amnesia.

## 1. The Structural Autonomy Rule (Data Structure vs. Pattern)

- **Conflict:** Does the entity describe a layout (e.g., Distributed Hash Table)?
- **Axiom:** If the text defines the concrete mathematical layout of bits (regardless of network distribution), it is a **Data Structure**. If it defines a choreography of roles (Leader/Follower) agnostic to the physical storage, it is a **Pattern**.

## 2. The Threat-Signal Gating Rule (Mitigation vs. Algorithm)

- **Conflict:** Does a mathematical procedure exist for computation or protection?
- **Axiom:** If the mechanism takes a dynamic threat or load signal as an explicit runtime input to throttle or drop execution, it is a **Mitigation**. If it computes a transformation irrespective of external pressure, it is an **Algorithm**.

## 3. The Actor Boundary Rule (Algorithm vs. Pattern)

- **Conflict:** Is this a distributed process or a local one?
- **Axiom:** If the logic is expressible as the sequence of a _single logical actor_ (even within a larger system), it is an **Algorithm**. If it fundamentally mandates the message-passing arrangement between _multiple distinct roles_, it is a **Pattern**.

## 4. The Trigger Genesis Rule (Attack Vector vs. Failure Mode)

- **Conflict:** The system crashed due to resource exhaustion. Why?
- **Axiom:** If the text explicitly describes a crafted payload or adversarial technique alien to the intended contract, it is an **Attack Vector**. If the degradation emerges organically from thresholds being breached under normal operational flow, it is a **Failure Mode**.

## 5. The Temporal State Rule (Data Structure vs. Algorithm)

- **Conflict:** Resolving the Wirth Duality (e.g., a Tree vs. traversing the Tree).
- **Axiom:** If the text defines the invariant geometric arrangement of data at rest, it is a **Data Structure**. If it defines the active transformation or pathway over that data, it is an **Algorithm**.

## 6. The Boundary Contract Rule (Interface vs. Pattern)

- **Conflict:** Is this a protocol or the architecture built around the protocol?
- **Axiom:** If the text isolates the precise contract at a single seam (e.g., HTTP verbs, headers), it is an **Interface**. If it describes the routing logic and arrangement of systems utilizing that boundary (e.g., Pub/Sub Broker routing), it is a **Pattern**.