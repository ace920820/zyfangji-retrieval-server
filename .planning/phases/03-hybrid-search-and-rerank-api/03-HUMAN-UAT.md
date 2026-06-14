---
status: partial
phase: 03-hybrid-search-and-rerank-api
source: [03-VERIFICATION.md]
started: 2026-06-14T17:51:21Z
updated: 2026-06-14T17:51:21Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Run /api/search against a live active index with configured BGE-M3 embedding endpoint, Qdrant, and BGE-Reranker-v2-m3 provider

expected: POST /api/search returns ranked TopK formula results after BM25 Top50 recall, Qdrant vector Top50 recall, hybrid fusion, and reranking without provider/index errors
result: [pending]

### 2. Inspect a real broad or sparse clinical query response from the sample Shanghanlun index

expected: Response contains ranked results plus query-quality warnings, and score text is not presented as medical confidence or prescription certainty
result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps
