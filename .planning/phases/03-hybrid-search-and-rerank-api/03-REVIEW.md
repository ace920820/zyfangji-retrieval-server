---
phase: 03-hybrid-search-and-rerank-api
reviewed: 2026-06-14T17:46:48Z
depth: standard
files_reviewed: 18
files_reviewed_list:
  - src/zyfangji_retrieval/config.py
  - src/zyfangji_retrieval/domain/search_models.py
  - src/zyfangji_retrieval/search/query.py
  - src/zyfangji_retrieval/search/bm25.py
  - src/zyfangji_retrieval/search/embedding_factory.py
  - src/zyfangji_retrieval/search/vector.py
  - src/zyfangji_retrieval/search/fusion.py
  - src/zyfangji_retrieval/search/rerank.py
  - src/zyfangji_retrieval/search/service.py
  - src/zyfangji_retrieval/search/evidence.py
  - src/zyfangji_retrieval/api/app.py
  - src/zyfangji_retrieval/api/routes/search.py
  - tests/test_search_contracts.py
  - tests/test_search_pipeline.py
  - tests/test_search_api.py
  - tests/test_status_api.py
findings:
  critical: 0
  warning: 1
  info: 0
  total: 1
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-06-14T17:46:48Z
**Depth:** standard
**Files Reviewed:** 18
**Status:** issues_found

## Summary

Reviewed the Phase 03 hybrid search API, retrieval orchestration, provider boundaries, evidence projection, route error contracts, and related tests. The implementation preserves retrieval-only scope and does not add chatbot, diagnosis, or prescription-advice behavior. One reliability issue was found in operational error handling: Qdrant/vector-store failures can escape as 500 responses despite the API contract reserving a stable vector-store unavailable envelope.

Verification run during review:

`PYTHONDONTWRITEBYTECODE=1 UV_PROJECT_ENVIRONMENT=/tmp/zyfangji-retrieval-venv uv run pytest tests/test_search_contracts.py tests/test_search_pipeline.py tests/test_search_api.py tests/test_status_api.py -q` -> 58 passed, 18 warnings.

## Warnings

### WR-01: Qdrant Vector Store Failures Bypass Stable 503 Error Envelope

**File:** `src/zyfangji_retrieval/search/service.py:66-85`

**Issue:** `SearchService.search()` only converts `EmbeddingProviderError` from the recall block into a typed `SearchServiceError`. If `VectorRetriever.recall()` reaches Qdrant and `query_points()` raises a client/network/runtime exception, that exception is not wrapped as `vector_store_unavailable`. The route already includes `vector_store_unavailable` in `SERVICE_UNAVAILABLE_CODES`, but the service never emits it, so a live Qdrant outage can become an unstructured 500 instead of the planned stable Java-facing 503 envelope.

**Fix:** Add a typed vector-store boundary around Qdrant calls. Keep embedding failures distinct, but wrap Qdrant/client failures before they reach the route.

```python
# src/zyfangji_retrieval/search/vector.py
class VectorStoreError(RuntimeError):
    pass


class VectorRetriever:
    ...
    def recall(...):
        query_vector = self._embedding_provider().embed_documents([query_text])[0]
        try:
            response = self.qdrant_client.query_points(
                collection_name=active.qdrant_collection,
                query=query_vector,
                limit=recall_topk,
                with_payload=True,
                with_vectors=False,
            )
        except Exception as exc:
            raise VectorStoreError("vector store unavailable") from exc
        ...
```

```python
# src/zyfangji_retrieval/search/service.py
from zyfangji_retrieval.search.vector import VectorRetriever, VectorStoreError

...
        except EmbeddingProviderError as exc:
            raise SearchServiceError(
                code="embedding_provider_unavailable",
                message="Embedding provider unavailable.",
                details={
                    "provider": self.settings.embedding_provider,
                    "model_id": self.settings.embedding_model_id,
                },
            ) from exc
        except VectorStoreError as exc:
            raise SearchServiceError(
                code="vector_store_unavailable",
                message="Vector store unavailable.",
                details={"vector_store": "qdrant"},
            ) from exc
```

Add a service or route test where fake Qdrant raises and assert `/api/search` returns HTTP 503 with `detail.error.code == "vector_store_unavailable"`.

---

_Reviewed: 2026-06-14T17:46:48Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
