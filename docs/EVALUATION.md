# Evaluation Framework

Memorae is evaluated as a connected data, graph, retrieval, context, and answer system. A fluent answer fails if discovery missed required evidence, graph links are wrong, temporal state is stale, or a claim lacks provenance.

## Gold case schema

Each case stores the query, snapshot, graded evidence IDs, entity aliases, graph edges, required facets, temporal change chain, dependency path, acceptable claims, and claim-to-evidence links. Splits hold out projects, source threads, time ranges, aliases, and query phrasings.

## Metrics

| Stage | Primary metrics |
|---|---|
| Data | schema validity, duplicate rate, lineage coverage, cursor continuity, future leakage |
| Entity resolution | entity precision/recall, alias accuracy, ambiguity calibration |
| Relationships | edge precision/recall, provenance coverage, orphan rate |
| Memory extraction | task/commitment precision/recall, deadline accuracy, current-state accuracy |
| Broad recall | Recall@20/50/100, MRR, source/entity slices |
| Expansion | recall gain, expansion precision, useful path rate, graph nodes visited |
| Reranking | nDCG@10/20, hard-negative win rate |
| Temporal/dependency | change-chain and dependency-path recall |
| Context | evidence/facet coverage, density, redundancy, stale-as-current rate, quality calibration |
| Answer | claim support coverage, faithfulness, hallucination rate, incomplete-evidence disclosure |
| Trace | broad-first invariant, provenance validity, executed-route accuracy, stop consistency |

## Regression suites

- unseen paraphrases of risk, priority, blocker, history, and ownership questions;
- entity aliases and renamed projects;
- corrections requiring both old and new evidence;
- dependencies requiring two-hop traversal;
- older authoritative evidence against recent distractors;
- multi-project vocabulary collisions;
- ambiguous conflicts that must remain unresolved;
- media events with supplied transcripts and no configured API;
- post-snapshot observations that must never enter context.

## Initial gates

| Gate | Target |
|---|---:|
| Broad Recall@50 | >= 0.92 |
| Expanded Recall@50 | >= 0.97 |
| Expansion precision | >= 0.55 |
| nDCG@10 | >= 0.85 |
| Entity resolution accuracy | >= 0.95 |
| Relationship precision | >= 0.93 |
| Weighted evidence/facet coverage | >= 0.95 |
| Claim support coverage | 1.00 |
| Stale-as-current rate | 0.00 |
| Future-evidence violations | 0 |
| Trace validity rate | 1.00 |

## Continuous evaluation

Replay frozen event logs for every extractor, graph, index, or reranker version. Store dataset hash, code version, snapshot, API/model version, storage schema, and retrieval trace. Compare overall and sliced metrics, inspect changed graph communities, and shadow candidate versions before promotion.

The metric implementations are in `app/evaluation/metrics.py`; a durable labeled-case runner is the next roadmap item.

