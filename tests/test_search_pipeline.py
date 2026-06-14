from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from zyfangji_retrieval.config import AppSettings
from zyfangji_retrieval.domain.index_models import ActiveIndexRecord
from zyfangji_retrieval.domain.models import FormulaMention, KnowledgeEntry
from zyfangji_retrieval.domain.search_models import PatientSearchRequest
from zyfangji_retrieval.indexing.bm25_store import BM25IndexMetadata, BM25IndexSnapshot
from zyfangji_retrieval.search.bm25 import BM25Retriever
from zyfangji_retrieval.search.embedding_factory import (
    BgeM3HttpEmbeddingProvider,
    EmbeddingProviderError,
    build_embedding_provider,
)
from zyfangji_retrieval.search.fusion import fuse_candidates
from zyfangji_retrieval.search.rerank import (
    BGERerankerProvider,
    DeterministicRerankerProvider,
    DisabledRerankerProvider,
    RerankCandidate,
    RerankerProviderError,
)
from zyfangji_retrieval.search.service import SearchService, SearchServiceError
from zyfangji_retrieval.search.vector import VectorRetriever, VectorStoreError


def _active(tmp_path: Path) -> ActiveIndexRecord:
    return ActiveIndexRecord(
        index_version="idx-20260614120000",
        metadata_version="meta-20260614120000",
        qdrant_collection="zyfangji_entries_idx_20260614120000",
        qdrant_alias="zyfangji_entries_active",
        bm25_path=str(tmp_path / "bm25" / "idx-20260614120000"),
        updated_at=datetime.now(UTC),
        activated_at=datetime.now(UTC),
        entry_count=2,
        vector_count=2,
        bm25_doc_count=2,
        provider_id="bge_m3",
        model_id="BAAI/bge-m3",
        vector_size=4,
    )


class FakeBM25Index:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def retrieve(
        self,
        tokenized_queries: list[list[str]],
        *,
        corpus: list[str],
        k: int,
        show_progress: bool,
    ) -> tuple[list[list[str]], list[list[float]]]:
        self.calls.append(
            {
                "tokenized_queries": tokenized_queries,
                "corpus": corpus,
                "k": k,
                "show_progress": show_progress,
            }
        )
        return [["entry-2", "entry-1"]], [[9.5, 3.0]]


class FakeBM25Store:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.loaded_versions: list[str] = []
        self.index = FakeBM25Index()

    def load(self, index_version: str) -> BM25IndexSnapshot:
        self.loaded_versions.append(index_version)
        return BM25IndexSnapshot(
            metadata=BM25IndexMetadata(
                index_version=index_version,
                doc_count=2,
                entry_ids=["entry-1", "entry-2"],
                created_at=datetime.now(UTC),
            ),
            index=self.index,
            path=self.root / index_version,
        )


def test_bm25_recall_loads_active_path_and_requests_top50(tmp_path: Path) -> None:
    active = _active(tmp_path)
    retriever = BM25Retriever(index_store_factory=FakeBM25Store)

    candidates = retriever.recall("太阳病 脉浮紧", active=active, recall_topk=50)

    assert [candidate.entry_id for candidate in candidates] == ["entry-2", "entry-1"]
    assert [candidate.rank for candidate in candidates] == [1, 2]
    assert [candidate.score for candidate in candidates] == [9.5, 3.0]
    store = retriever._last_store
    assert store.root == Path(active.bm25_path).parent
    assert store.loaded_versions == [active.index_version]
    assert store.index.calls[0]["k"] == 50
    assert store.index.calls[0]["corpus"] == ["entry-1", "entry-2"]
    assert store.index.calls[0]["show_progress"] is False
    assert store.index.calls[0]["tokenized_queries"][0]


class FakeHttpResponse:
    def __init__(self, payload: Any, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.text = "provider response body must not leak into errors"

    def json(self) -> Any:
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class FakeHttpClient:
    def __init__(self, response: FakeHttpResponse) -> None:
        self.response = response
        self.posts: list[dict[str, Any]] = []

    def post(
        self,
        endpoint_url: str,
        *,
        json: dict[str, Any],
        headers: dict[str, str] | None = None,
        timeout: float,
    ) -> FakeHttpResponse:
        self.posts.append(
            {
                "endpoint_url": endpoint_url,
                "json": json,
                "headers": headers,
                "timeout": timeout,
            }
        )
        return self.response


def test_bge_m3_http_provider_parses_openai_compatible_response() -> None:
    client = FakeHttpClient(FakeHttpResponse({"data": [{"embedding": [0.1, 0.2, 0.3, 0.4]}]}))
    provider = BgeM3HttpEmbeddingProvider(
        endpoint_url="https://example.test/embeddings",
        api_key="secret-key",
        model_id="BAAI/bge-m3",
        vector_size=4,
        timeout_seconds=12.5,
        client=client,
    )

    vectors = provider.embed_documents(["患者文本不应出现在错误中"])

    assert vectors == [[0.1, 0.2, 0.3, 0.4]]
    assert client.posts == [
        {
            "endpoint_url": "https://example.test/embeddings",
            "json": {"model": "BAAI/bge-m3", "input": ["患者文本不应出现在错误中"]},
            "headers": {"Authorization": "Bearer secret-key"},
            "timeout": 12.5,
        }
    ]


def test_bge_m3_http_provider_parses_compact_embeddings_response() -> None:
    client = FakeHttpClient(FakeHttpResponse({"embeddings": [[0.4, 0.3, 0.2, 0.1]]}))
    provider = BgeM3HttpEmbeddingProvider(
        endpoint_url="https://example.test/embeddings",
        api_key=None,
        vector_size=4,
        client=client,
    )

    assert provider.embed_documents(["太阳病"]) == [[0.4, 0.3, 0.2, 0.1]]
    assert client.posts[0]["headers"] is None


@pytest.mark.parametrize(
    ("payload", "match"),
    [
        ({"embeddings": [[0.1, 0.2]]}, "vector_size"),
        ({"embeddings": [[0.1, 0.2, 0.3, 0.4], [0.4, 0.3, 0.2, 0.1]]}, "count"),
        (ValueError("bad json"), "malformed"),
    ],
)
def test_bge_m3_http_provider_rejects_invalid_responses(payload: Any, match: str) -> None:
    provider = BgeM3HttpEmbeddingProvider(
        endpoint_url="https://example.test/embeddings",
        api_key=None,
        vector_size=4,
        client=FakeHttpClient(FakeHttpResponse(payload)),
    )

    with pytest.raises(EmbeddingProviderError, match=match):
        provider.embed_documents(["太阳病"])


def test_bge_m3_http_provider_rejects_http_failure_without_patient_text() -> None:
    provider = BgeM3HttpEmbeddingProvider(
        endpoint_url="https://example.test/embeddings",
        api_key=None,
        vector_size=4,
        client=FakeHttpClient(FakeHttpResponse({"error": "bad"}, status_code=503)),
    )

    with pytest.raises(EmbeddingProviderError) as error:
        provider.embed_documents(["隐私患者文本"])

    assert "embedding provider unavailable" in str(error.value)
    assert "隐私患者文本" not in str(error.value)
    assert "provider response body" not in str(error.value)


def test_build_embedding_provider_requires_bge_endpoint_and_explicit_deterministic() -> None:
    bge_settings = AppSettings(
        embedding_provider="bge_m3",
        embedding_endpoint_url="https://example.test/embeddings",
        embedding_vector_size=4,
    )
    bge_provider = build_embedding_provider(bge_settings)
    assert isinstance(bge_provider, BgeM3HttpEmbeddingProvider)

    with pytest.raises(EmbeddingProviderError, match="bge_m3 embedding endpoint is not configured"):
        build_embedding_provider(AppSettings(embedding_provider="bge_m3", embedding_endpoint_url=None))

    deterministic = build_embedding_provider(
        AppSettings(embedding_provider="deterministic", embedding_vector_size=4)
    )
    assert deterministic.provider_id == "deterministic"

    default_provider = AppSettings().embedding_provider
    assert default_provider == "bge_m3"


class FakeEmbeddingProvider:
    provider_id = "fake"
    model_id = "fake-bge"
    vector_size = 4

    def __init__(self) -> None:
        self.texts: list[list[str]] = []

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.texts.append(list(texts))
        return [[0.1, 0.2, 0.3, 0.4]]


class FakeQdrantClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def query_points(
        self,
        *,
        collection_name: str,
        query: list[float],
        limit: int,
        with_payload: bool,
        with_vectors: bool,
    ) -> Any:
        self.calls.append(
            {
                "collection_name": collection_name,
                "query": query,
                "limit": limit,
                "with_payload": with_payload,
                "with_vectors": with_vectors,
            }
        )
        point = type(
            "Point",
            (),
            {"payload": {"entry_id": "entry-1", "retrieval_text": "太阳病"}, "score": 0.87},
        )()
        return type("QueryResult", (), {"points": [point]})()


class BrokenQdrantClient:
    def query_points(self, **_kwargs: Any) -> Any:
        raise RuntimeError("qdrant connection failed with patient text")


def test_vector_recall_embeds_query_and_uses_active_collection_top50(tmp_path: Path) -> None:
    active = _active(tmp_path)
    embedding_provider = FakeEmbeddingProvider()
    qdrant_client = FakeQdrantClient()
    retriever = VectorRetriever(
        embedding_provider=embedding_provider,
        qdrant_client=qdrant_client,
    )

    candidates = retriever.recall("主症:\n太阳病", active=active, recall_topk=50)

    assert embedding_provider.texts == [["主症:\n太阳病"]]
    assert qdrant_client.calls == [
        {
            "collection_name": active.qdrant_collection,
            "query": [0.1, 0.2, 0.3, 0.4],
            "limit": 50,
            "with_payload": True,
            "with_vectors": False,
        }
    ]
    assert candidates[0].entry_id == "entry-1"
    assert candidates[0].rank == 1
    assert candidates[0].score == 0.87
    assert candidates[0].payload == {"entry_id": "entry-1", "retrieval_text": "太阳病"}


def test_vector_recall_wraps_qdrant_failure_without_patient_text(tmp_path: Path) -> None:
    retriever = VectorRetriever(
        embedding_provider=FakeEmbeddingProvider(),
        qdrant_client=BrokenQdrantClient(),
    )

    with pytest.raises(VectorStoreError) as error:
        retriever.recall("隐私患者文本", active=_active(tmp_path), recall_topk=50)

    assert "vector store unavailable" in str(error.value)
    assert "隐私患者文本" not in str(error.value)


def test_rrf_fusion_preserves_signal_ranks_and_scores() -> None:
    bm25_candidates = [
        type("BM25", (), {"entry_id": "entry-1", "rank": 1, "score": 8.0})(),
        type("BM25", (), {"entry_id": "entry-2", "rank": 2, "score": 4.0})(),
    ]
    vector_candidates = [
        type(
            "Vector",
            (),
            {"entry_id": "entry-2", "rank": 1, "score": 0.91, "payload": {"retrieval_text": "桂枝汤"}},
        )(),
        type(
            "Vector",
            (),
            {"entry_id": "entry-3", "rank": 2, "score": 0.72, "payload": {"retrieval_text": "麻黄汤"}},
        )(),
    ]

    fused = fuse_candidates(bm25_candidates, vector_candidates, strategy="rrf", rrf_k=60, limit=50)

    assert [candidate.entry_id for candidate in fused] == ["entry-2", "entry-1", "entry-3"]
    assert fused[0].bm25_rank == 2
    assert fused[0].bm25_score == 4.0
    assert fused[0].vector_rank == 1
    assert fused[0].vector_score == 0.91
    assert fused[0].fused_rank == 1
    assert fused[0].fused_score == pytest.approx((1.0 / (60 + 2)) + (1.0 / (60 + 1)))
    assert fused[0].payload == {"retrieval_text": "桂枝汤"}


def test_fusion_rejects_unknown_strategy() -> None:
    with pytest.raises(ValueError, match="unsupported fusion strategy"):
        fuse_candidates([], [], strategy="unknown")


class FakeFlagReranker:
    constructed: list[tuple[str, bool]] = []

    def __init__(self, model_id: str, use_fp16: bool) -> None:
        self.constructed.append((model_id, use_fp16))

    def compute_score(self, pairs: list[list[str]]) -> list[float]:
        assert pairs == [["主症:\n太阳病", "条文 A"], ["主症:\n太阳病", "条文 B"]]
        return [0.1, 0.9]


def test_bge_reranker_provider_constructs_flag_reranker_and_sorts() -> None:
    FakeFlagReranker.constructed = []

    def fake_loader() -> type[FakeFlagReranker]:
        return FakeFlagReranker

    provider = BGERerankerProvider(reranker_loader=fake_loader)
    candidates = [
        RerankCandidate(entry_id="entry-a", text="条文 A"),
        RerankCandidate(entry_id="entry-b", text="条文 B"),
    ]

    reranked = provider.rerank("主症:\n太阳病", candidates)

    assert FakeFlagReranker.constructed == [("BAAI/bge-reranker-v2-m3", True)]
    assert [candidate.entry_id for candidate in reranked] == ["entry-b", "entry-a"]
    assert [candidate.rerank_score for candidate in reranked] == [0.9, 0.1]
    assert provider.model_id == "BAAI/bge-reranker-v2-m3"


def test_bge_reranker_provider_wraps_scoring_failures_without_patient_text() -> None:
    class BrokenReranker:
        def compute_score(self, pairs: list[list[str]]) -> list[float]:
            raise RuntimeError("provider leaked low-level failure")

    provider = BGERerankerProvider(reranker=BrokenReranker())

    with pytest.raises(RerankerProviderError) as error:
        provider.rerank("隐私患者文本", [RerankCandidate(entry_id="entry-a", text="证据文本")])

    assert "reranker provider unavailable" in str(error.value)
    assert "隐私患者文本" not in str(error.value)
    assert "证据文本" not in str(error.value)


def test_deterministic_reranker_orders_by_query_candidate_overlap() -> None:
    provider = DeterministicRerankerProvider()
    candidates = [
        RerankCandidate(entry_id="entry-a", text="少阴病"),
        RerankCandidate(entry_id="entry-b", text="太阳病 脉浮紧"),
    ]

    reranked = provider.rerank("太阳病 脉浮紧", candidates)

    assert provider.model_id == "BAAI/bge-reranker-v2-m3"
    assert [candidate.entry_id for candidate in reranked] == ["entry-b", "entry-a"]
    assert reranked[0].rerank_score > reranked[1].rerank_score


def test_disabled_reranker_raises_typed_error() -> None:
    with pytest.raises(RerankerProviderError, match="reranker is disabled"):
        DisabledRerankerProvider().rerank(
            "太阳病",
            [RerankCandidate(entry_id="entry-a", text="太阳病")],
        )


def _entry(entry_id: str, text: str, formula: str) -> KnowledgeEntry:
    return KnowledgeEntry(
        entry_id=entry_id,
        source_book="伤寒论",
        source_sheet="Sheet1",
        source_row=int(entry_id.rsplit("-", maxsplit=1)[-1]),
        source_code=f"CODE-{entry_id}",
        formula_raw=formula,
        formula_mentions=[FormulaMention(name=formula, code=f"F-{entry_id}")],
        formula_mapping_status="parsed",
        retrieval_text=text,
        raw_record={"推荐方剂": formula},
        normalized_record={"推荐方剂": formula},
        therapy="解肌发表",
        tcm_disease="太阳病",
        western_disease="感冒",
        source_article=text,
        contraindication="禁忌文本",
        effect="疗效文本",
    )


class FakeIndexStore:
    def __init__(self, active: ActiveIndexRecord | None) -> None:
        self.active = active
        self.calls: list[str] = []

    def get_active(self) -> ActiveIndexRecord | None:
        self.calls.append("get_active")
        return self.active


class FakeMetadataStore:
    def __init__(self, entries: list[KnowledgeEntry]) -> None:
        self.entries = entries
        self.loaded_versions: list[str | None] = []

    def load_entries(self, index_version: str | None = None) -> list[KnowledgeEntry]:
        self.loaded_versions.append(index_version)
        return self.entries


class FakeBM25Retriever:
    def __init__(self) -> None:
        self.calls: list[tuple[str, ActiveIndexRecord, int]] = []

    def recall(self, query_text: str, active: ActiveIndexRecord, recall_topk: int) -> list[Any]:
        self.calls.append((query_text, active, recall_topk))
        return [
            type("BM25", (), {"entry_id": "entry-1", "rank": 1, "score": 8.0})(),
            type("BM25", (), {"entry_id": "entry-2", "rank": 2, "score": 4.0})(),
        ]


class FakeVectorRetrieverForService:
    def __init__(self, fail: bool = False, vector_store_fail: bool = False) -> None:
        self.fail = fail
        self.vector_store_fail = vector_store_fail
        self.calls: list[tuple[str, ActiveIndexRecord, int]] = []

    def recall(self, query_text: str, active: ActiveIndexRecord, recall_topk: int) -> list[Any]:
        self.calls.append((query_text, active, recall_topk))
        if self.fail:
            raise EmbeddingProviderError("embedding provider unavailable")
        if self.vector_store_fail:
            raise VectorStoreError("vector store unavailable")
        return [
            type(
                "Vector",
                (),
                {
                    "entry_id": "entry-2",
                    "rank": 1,
                    "score": 0.91,
                    "payload": {"retrieval_text": "桂枝汤"},
                },
            )(),
            type(
                "Vector",
                (),
                {
                    "entry_id": "entry-1",
                    "rank": 2,
                    "score": 0.72,
                    "payload": {"retrieval_text": "麻黄汤"},
                },
            )(),
        ]


class FakeServiceReranker:
    model_id = "BAAI/bge-reranker-v2-m3"

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[tuple[str, list[RerankCandidate]]] = []

    def rerank(self, query_text: str, candidates: list[RerankCandidate]) -> list[Any]:
        self.calls.append((query_text, list(candidates)))
        if self.fail:
            raise RerankerProviderError("reranker provider unavailable")
        scores = {"entry-1": 0.95, "entry-2": 0.1}
        reranked = [
            type(
                "Reranked",
                (),
                {
                    "entry_id": candidate.entry_id,
                    "text": candidate.text,
                    "payload": candidate.payload,
                    "rerank_score": scores[candidate.entry_id],
                    "rerank_rank": 1 if candidate.entry_id == "entry-1" else 2,
                },
            )()
            for candidate in candidates
        ]
        return sorted(reranked, key=lambda candidate: -candidate.rerank_score)


def _service(
    tmp_path: Path,
    *,
    active: ActiveIndexRecord | None = None,
    reranker_required: bool = True,
    vector_fail: bool = False,
    vector_store_fail: bool = False,
    reranker_fail: bool = False,
) -> tuple[SearchService, FakeIndexStore, FakeMetadataStore, FakeBM25Retriever, FakeVectorRetrieverForService]:
    active_record = active if active is not None else _active(tmp_path)
    index_store = FakeIndexStore(active_record)
    metadata_store = FakeMetadataStore(
        [
            _entry("entry-1", "麻黄汤 条文", "麻黄汤"),
            _entry("entry-2", "桂枝汤 条文", "桂枝汤"),
        ]
    )
    bm25_retriever = FakeBM25Retriever()
    vector_retriever = FakeVectorRetrieverForService(
        fail=vector_fail,
        vector_store_fail=vector_store_fail,
    )
    service = SearchService(
        settings=AppSettings(
            recall_topk=50,
            fusion_strategy="rrf",
            rrf_k=60,
            reranker_required=reranker_required,
        ),
        index_store=index_store,
        metadata_store=metadata_store,
        bm25_retriever=bm25_retriever,
        vector_retriever=vector_retriever,
        reranker=FakeServiceReranker(fail=reranker_fail),
    )
    return service, index_store, metadata_store, bm25_retriever, vector_retriever


def test_search_service_requires_active_index_before_recall(tmp_path: Path) -> None:
    service, index_store, metadata_store, bm25_retriever, vector_retriever = _service(
        tmp_path,
        active=None,
    )
    index_store.active = None

    with pytest.raises(SearchServiceError) as error:
        service.search(PatientSearchRequest(main_symptom="太阳病"))

    assert error.value.code == "index_not_ready"
    assert index_store.calls == ["get_active"]
    assert metadata_store.loaded_versions == []
    assert bm25_retriever.calls == []
    assert vector_retriever.calls == []


def test_search_service_orchestrates_active_index_recall_fusion_and_rerank(tmp_path: Path) -> None:
    service, index_store, metadata_store, bm25_retriever, vector_retriever = _service(tmp_path)

    response = service.search(PatientSearchRequest(main_symptom="太阳病", topk=1))

    assert index_store.calls == ["get_active"]
    assert metadata_store.loaded_versions == [index_store.active.metadata_version]
    assert bm25_retriever.calls[0][2] == 50
    assert vector_retriever.calls[0][2] == 50
    assert response.query.text == "主症:\n太阳病"
    assert [result.entry_id for result in response.results] == ["entry-1"]
    assert response.results[0].signal_scores.bm25_score == 8.0
    assert response.results[0].signal_scores.vector_score == 0.72
    assert response.results[0].signal_scores.rerank_score == 0.95
    assert response.results[0].formula_raw == "麻黄汤"
    assert response.metadata.index_version == index_store.active.index_version
    assert response.metadata.metadata_version == index_store.active.metadata_version
    assert response.metadata.requested_topk == 1
    assert response.metadata.recall_topk == 50
    assert response.metadata.fusion_strategy == "rrf"
    assert response.metadata.reranker_model_id == "BAAI/bge-reranker-v2-m3"
    assert response.metadata.pipeline_status == "reranked"


def test_search_service_maps_embedding_failure_to_typed_error(tmp_path: Path) -> None:
    service, *_ = _service(tmp_path, vector_fail=True)

    with pytest.raises(SearchServiceError) as error:
        service.search(PatientSearchRequest(main_symptom="太阳病"))

    assert error.value.code == "embedding_provider_unavailable"
    assert "太阳病" not in error.value.message


def test_search_service_maps_vector_store_failure_to_typed_error(tmp_path: Path) -> None:
    service, *_ = _service(tmp_path, vector_store_fail=True)

    with pytest.raises(SearchServiceError) as error:
        service.search(PatientSearchRequest(main_symptom="太阳病"))

    assert error.value.code == "vector_store_unavailable"
    assert error.value.details == {"vector_store": "qdrant"}
    assert "太阳病" not in error.value.message


def test_search_service_required_reranker_failure_raises_typed_error(tmp_path: Path) -> None:
    service, *_ = _service(tmp_path, reranker_required=True, reranker_fail=True)

    with pytest.raises(SearchServiceError) as error:
        service.search(PatientSearchRequest(main_symptom="太阳病"))

    assert error.value.code == "reranker_unavailable"


def test_search_service_optional_reranker_failure_returns_degraded_fused_results(tmp_path: Path) -> None:
    service, *_ = _service(tmp_path, reranker_required=False, reranker_fail=True)

    response = service.search(PatientSearchRequest(main_symptom="太阳病", topk=2))

    assert response.metadata.pipeline_status == "reranker_degraded"
    assert [warning.code for warning in response.warnings] == [
        "query_too_sparse",
        "query_broad",
        "reranker_degraded",
    ]
    assert [result.entry_id for result in response.results] == ["entry-1", "entry-2"]
    assert all(result.signal_scores.rerank_score is None for result in response.results)
