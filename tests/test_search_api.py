from __future__ import annotations

from datetime import UTC, datetime
import importlib
from typing import Any

import pytest
from fastapi.testclient import TestClient

from zyfangji_retrieval.config import AppSettings
from zyfangji_retrieval.domain.index_models import ActiveIndexRecord
from zyfangji_retrieval.domain.models import FormulaMention, KnowledgeEntry
from zyfangji_retrieval.domain.search_models import (
    EvidenceFields,
    PatientSearchRequest,
    QueryWarning,
    SearchPipelineMetadata,
    SearchQuery,
    SearchResponse,
    SearchResult,
    SearchResultSource,
    SignalScores,
)
from zyfangji_retrieval.indexing.embeddings import EmbeddingProviderError
from zyfangji_retrieval.search.embedding_factory import build_embedding_provider
from zyfangji_retrieval.search.rerank import (
    BGERerankerProvider,
    DeterministicRerankerProvider,
    RerankCandidate,
    RerankerProviderError,
)
from zyfangji_retrieval.search.service import SearchService

app_module = importlib.import_module("zyfangji_retrieval.api.app")


def _active() -> ActiveIndexRecord:
    return ActiveIndexRecord(
        index_version="idx-20260614120000",
        metadata_version="meta-20260614120000",
        qdrant_collection="zyfangji_entries_idx_20260614120000",
        qdrant_alias="zyfangji_entries_active",
        bm25_path="/tmp/bm25/idx-20260614120000",
        updated_at=datetime.now(UTC),
        entry_count=2,
        vector_count=2,
        bm25_doc_count=2,
        provider_id="bge_m3",
        model_id="BAAI/bge-m3",
        vector_size=4,
    )


def _entry(entry_id: str, formula: str, code: str | None) -> KnowledgeEntry:
    return KnowledgeEntry(
        entry_id=entry_id,
        source_book="伤寒论",
        source_sheet="病症信息",
        source_row=12 if entry_id == "entry-1" else 13,
        source_code=None,
        formula_raw=formula,
        formula_mentions=[FormulaMention(name=formula, code=code)],
        formula_mapping_status="parsed" if code else "unmapped",
        retrieval_text="主症:\n发热恶寒\n\n脉象:\n脉浮紧",
        raw_record={
            "中西先后（先看中医？先看西医？）": "高热不退先看西医",
        },
        normalized_record={
            "main_symptom": "发热恶寒",
            "complex_symptom": "头痛身疼",
            "detail_symptom": "无汗",
            "alias": "伤寒",
            "tongue": "舌淡苔白",
            "pulse": "脉浮紧",
            "source_article": "第35条",
            "syndrome": "太阳伤寒证",
            "tcm_disease": "太阳病",
            "western_disease": "上呼吸道感染",
            "therapy": "发汗解表",
            "contraindication": "阴虚者慎用",
            "effect": "汗出热退",
        },
        therapy="发汗解表",
        tcm_disease="太阳病",
        western_disease="上呼吸道感染",
        source_article="第35条",
        contraindication="阴虚者慎用",
        effect="汗出热退",
    )


class _IndexStore:
    def get_active(self) -> ActiveIndexRecord:
        return _active()


class _MetadataStore:
    def load_entries(self, index_version: str | None = None) -> list[KnowledgeEntry]:
        return [
            _entry("entry-1", "麻黄汤", "F-MHT"),
            _entry("entry-2", "桂枝汤", None),
        ]


class _BM25Retriever:
    def recall(self, query_text: str, active: ActiveIndexRecord, recall_topk: int) -> list[Any]:
        return [
            type("BM25", (), {"entry_id": "entry-1", "rank": 1, "score": 8.0})(),
            type("BM25", (), {"entry_id": "entry-2", "rank": 2, "score": 4.0})(),
        ]


class _VectorRetriever:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail

    def recall(self, query_text: str, active: ActiveIndexRecord, recall_topk: int) -> list[Any]:
        if self.fail:
            raise EmbeddingProviderError("bge_m3 embedding endpoint is not configured")
        return [
            type(
                "Vector",
                (),
                {
                    "entry_id": "entry-1",
                    "rank": 1,
                    "score": 0.91,
                    "payload": {"entry_id": "entry-1"},
                },
            )(),
            type(
                "Vector",
                (),
                {
                    "entry_id": "entry-2",
                    "rank": 2,
                    "score": 0.72,
                    "payload": {"entry_id": "entry-2"},
                },
            )(),
        ]


class _Reranker:
    model_id = "BAAI/bge-reranker-v2-m3"

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail

    def rerank(self, query_text: str, candidates: list[RerankCandidate]) -> list[Any]:
        if self.fail:
            raise RerankerProviderError("reranker provider unavailable")
        scores = {"entry-1": 0.95, "entry-2": 0.2}
        return sorted(
            [
                type(
                    "Reranked",
                    (),
                    {
                        "entry_id": candidate.entry_id,
                        "text": candidate.text,
                        "payload": candidate.payload,
                        "rerank_score": scores[candidate.entry_id],
                    },
                )()
                for candidate in candidates
            ],
            key=lambda candidate: -candidate.rerank_score,
        )


def _service(*, vector_fail: bool = False, reranker_fail: bool = False) -> SearchService:
    return SearchService(
        settings=AppSettings(
            recall_topk=50,
            fusion_strategy="rrf",
            rrf_k=60,
            reranker_required=True,
        ),
        index_store=_IndexStore(),
        metadata_store=_MetadataStore(),
        bm25_retriever=_BM25Retriever(),
        vector_retriever=_VectorRetriever(fail=vector_fail),
        reranker=_Reranker(fail=reranker_fail),
    )


def test_search_response_projects_java_friendly_evidence_shape() -> None:
    response = _service().search(PatientSearchRequest(main_symptom="发热恶寒", topk=1))

    payload = response.model_dump(mode="json")
    assert set(payload) == {"query", "results", "warnings", "metadata", "score_semantics"}
    assert payload["query"] == {"text": "主症:\n发热恶寒"}
    assert payload["metadata"]["requested_topk"] == 1
    assert payload["metadata"]["recall_topk"] == 50
    assert payload["metadata"]["pipeline_status"] == "reranked"
    assert "not medical confidence, diagnosis probability, or prescription certainty" in payload[
        "score_semantics"
    ]

    result = payload["results"][0]
    assert set(result) == {
        "rank",
        "retrieval_score",
        "score_type",
        "entry_id",
        "source",
        "formula_raw",
        "formula_mentions",
        "formula_code",
        "formula_mapping_status",
        "evidence",
        "signal_scores",
    }
    assert result["rank"] == 1
    assert result["retrieval_score"] == 0.95
    assert result["score_type"] == "rerank_score"
    assert result["entry_id"] == "entry-1"
    assert result["source"] == {
        "book": "伤寒论",
        "sheet": "病症信息",
        "row": 12,
        "article": "第35条",
    }
    assert result["formula_raw"] == "麻黄汤"
    assert result["formula_mentions"] == [
        {
            "name": "麻黄汤",
            "code": "F-MHT",
            "branch_label": None,
            "needs_review": False,
            "raw_text": None,
        }
    ]
    assert result["formula_code"] == "F-MHT"
    assert result["formula_mapping_status"] == "parsed"
    assert result["signal_scores"] == {
        "bm25_score": 8.0,
        "vector_score": 0.91,
        "fused_score": pytest.approx((1.0 / 61) + (1.0 / 61)),
        "rerank_score": 0.95,
    }
    assert result["evidence"] == {
        "main_symptom": "发热恶寒",
        "complex_symptom": "头痛身疼",
        "detail_symptom": "无汗",
        "alias": "伤寒",
        "tongue": "舌淡苔白",
        "pulse": "脉浮紧",
        "source_article": "第35条",
        "syndrome": "太阳伤寒证",
        "tcm_disease": "太阳病",
        "western_disease": "上呼吸道感染",
        "therapy": "发汗解表",
        "contraindication": "阴虚者慎用",
        "effect": "汗出热退",
        "western_medicine_priority": "高热不退先看西医",
    }


def test_formula_code_uses_first_non_empty_mention_code() -> None:
    response = _service().search(PatientSearchRequest(main_symptom="发热恶寒", topk=2))

    assert [result.formula_code for result in response.results] == ["F-MHT", None]


def test_create_app_attaches_lazy_search_service() -> None:
    app = app_module.create_app(AppSettings(embedding_provider="bge_m3", embedding_endpoint_url=None))

    assert app.state.search_service is not None


def test_embedding_provider_deterministic_fallback_is_explicit() -> None:
    provider = build_embedding_provider(
        AppSettings(embedding_provider="deterministic", embedding_vector_size=4)
    )

    assert provider.provider_id == "deterministic"


def test_reranker_provider_bge_and_deterministic_are_explicit() -> None:
    bge = app_module.build_reranker_provider(AppSettings(reranker_provider="bge"))
    deterministic = app_module.build_reranker_provider(
        AppSettings(reranker_provider="deterministic")
    )

    assert isinstance(bge, BGERerankerProvider)
    assert isinstance(deterministic, DeterministicRerankerProvider)


def test_missing_bge_endpoint_keeps_health_status_callable_and_search_fails_typed(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeIndexStateStore:
        def __init__(self, db_path) -> None:
            self.db_path = db_path

        def get_active(self) -> ActiveIndexRecord:
            return _active()

    class FakeMetadataStore:
        def __init__(self, db_path) -> None:
            self.db_path = db_path

        def load_entries(self, index_version: str | None = None) -> list[KnowledgeEntry]:
            return [_entry("entry-1", "麻黄汤", "F-MHT")]

    class FakeBM25Retriever:
        def recall(self, query_text: str, active: ActiveIndexRecord, recall_topk: int) -> list[Any]:
            return [type("BM25", (), {"entry_id": "entry-1", "rank": 1, "score": 8.0})()]

    class FakeQdrantClient:
        def __init__(self, url: str) -> None:
            self.url = url

    monkeypatch.setattr(app_module, "SQLiteIndexStateStore", FakeIndexStateStore)
    monkeypatch.setattr(app_module, "SQLiteMetadataStore", FakeMetadataStore)
    monkeypatch.setattr(app_module, "BM25Retriever", FakeBM25Retriever)
    monkeypatch.setattr(app_module, "QdrantClient", FakeQdrantClient)

    app = app_module.create_app(
        AppSettings(
            db_path=tmp_path / "metadata.db",
            embedding_provider="bge_m3",
            embedding_endpoint_url=None,
        )
    )
    client = TestClient(app)

    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").status_code in {200, 503}
    assert client.get("/status").status_code in {200, 503}

    response = client.post("/api/search", json={"main_symptom": "发热恶寒"})

    assert response.status_code == 503
    assert response.json()["detail"]["error"]["code"] == "embedding_provider_unavailable"
    assert response.json()["detail"]["error"]["message"] == "Embedding provider unavailable."


class _EchoSearchService:
    def search(self, request: PatientSearchRequest) -> SearchResponse:
        return SearchResponse(
            query=SearchQuery(text=f"主症:\n{request.main_symptom}"),
            results=[
                SearchResult(
                    rank=1,
                    retrieval_score=0.9,
                    score_type="rerank_score",
                    entry_id="entry-1",
                    source=SearchResultSource(
                        book="伤寒论",
                        sheet="病症信息",
                        row=12,
                        article="第35条",
                    ),
                    formula_raw="麻黄汤",
                    formula_mentions=[{"name": "麻黄汤", "code": "F-MHT"}],
                    formula_code="F-MHT",
                    formula_mapping_status="parsed",
                    evidence=EvidenceFields(
                        main_symptom="发热恶寒",
                        western_medicine_priority="高热不退先看西医",
                    ),
                    signal_scores=SignalScores(
                        bm25_score=8.0,
                        vector_score=0.9,
                        fused_score=0.95,
                        rerank_score=0.9,
                    ),
                )
            ],
            warnings=[
                QueryWarning(code="query_too_sparse", severity="info", message="sparse"),
                QueryWarning(code="query_broad", severity="info", message="broad"),
            ],
            metadata=SearchPipelineMetadata(
                index_version="idx-1",
                metadata_version="meta-1",
                requested_topk=request.topk,
                recall_topk=50,
                fusion_strategy="rrf",
                reranker_model_id="BAAI/bge-reranker-v2-m3",
                pipeline_status="reranked",
            ),
        )


def test_search_route_defaults_topk_to_ten_and_returns_score_semantics() -> None:
    app = app_module.create_app()
    app.state.search_service = _EchoSearchService()
    client = TestClient(app)

    response = client.post("/api/search", json={"main_symptom": "发热恶寒"})

    payload = response.json()
    assert response.status_code == 200
    assert payload["metadata"]["requested_topk"] == 10
    assert payload["warnings"][0]["code"] == "query_too_sparse"
    assert payload["warnings"][1]["code"] == "query_broad"
    assert "not medical confidence, diagnosis probability, or prescription certainty" in payload[
        "score_semantics"
    ]
    assert "confidence" not in payload
    assert "diagnosis_probability" not in payload
    assert "prescription_certainty" not in payload


def test_search_route_respects_explicit_topk_two() -> None:
    app = app_module.create_app()
    app.state.search_service = _EchoSearchService()
    client = TestClient(app)

    response = client.post("/api/search", json={"main_symptom": "发热恶寒", "topk": 2})

    assert response.status_code == 200
    assert response.json()["metadata"]["requested_topk"] == 2


def test_search_route_rejects_topk_over_50_with_stable_validation_envelope() -> None:
    client = TestClient(app_module.create_app())

    response = client.post("/api/search", json={"main_symptom": "发热", "topk": 51})

    assert response.status_code == 422
    assert response.json()["detail"]["error"]["code"] == "validation_error"
    assert response.json()["detail"]["error"]["message"] == "Request validation failed."
