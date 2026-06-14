from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from zyfangji_retrieval.config import AppSettings
from zyfangji_retrieval.domain.index_models import ActiveIndexRecord
from zyfangji_retrieval.indexing.bm25_store import BM25IndexMetadata, BM25IndexSnapshot
from zyfangji_retrieval.search.bm25 import BM25Retriever
from zyfangji_retrieval.search.embedding_factory import (
    BgeM3HttpEmbeddingProvider,
    EmbeddingProviderError,
    build_embedding_provider,
)
from zyfangji_retrieval.search.vector import VectorRetriever


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
