# Design Reference

The production architecture, knowledge graph, GraphRAG workflow, media pipelines, storage design, scale plan, migration status, and roadmap are maintained in [PLATFORM_ARCHITECTURE.md](PLATFORM_ARCHITECTURE.md).

Core invariants:

1. Raw observations are immutable and point-in-time safe.
2. Derived intelligence always resolves to raw evidence IDs.
3. Every query begins with broad evidence recall.
4. Memory projections guide expansion only after evidence is discovered.
5. Answers expose context quality, retrieval provenance, and claim validation.
6. Hosted APIs are optional; no heavyweight local model is required.
7. Mutable runtime data is centralized under project-local `storage\` by default.
