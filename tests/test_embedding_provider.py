from datetime import UTC, datetime
from pathlib import Path

import pytest

from zyfangji_retrieval.config import AppSettings, get_settings
from zyfangji_retrieval.domain.index_models import (
    ActiveIndexRecord,
    IndexBuildRecord,
    IndexStatus,
    IndexValidationResult,
)
from zyfangji_retrieval.indexing.embeddings import (
    DeterministicEmbeddingProvider,
    EmbeddingProviderError,
    validate_embedding_batch,
)


def test_deterministic_embedding_provider_returns_stable_metadata_and_vectors() -> None:
    provider = DeterministicEmbeddingProvider(vector_size=4)
    texts = ["太阳病 头痛", "桂枝汤"]

    first = provider.embed_documents(texts)
    second = provider.embed_documents(texts)

    assert provider.provider_id == "deterministic"
    assert provider.model_id == "deterministic-bge-m3-compatible"
    assert provider.vector_size == 4
    assert first == second
    assert len(first) == len(texts)
    assert all(len(vector) == 4 for vector in first)
    assert all(isinstance(value, float) for vector in first for value in vector)


def test_validate_embedding_batch_accepts_matching_count_and_dimensions() -> None:
    vectors = [[0.1, 0.2, 0.3, 0.4], [0.5, 0.6, 0.7, 0.8]]

    validate_embedding_batch(["a", "b"], vectors, expected_vector_size=4)


def test_validate_embedding_batch_rejects_count_mismatch() -> None:
    with pytest.raises(EmbeddingProviderError, match="count"):
        validate_embedding_batch(["a", "b"], [[0.1, 0.2, 0.3, 0.4]], expected_vector_size=4)


def test_validate_embedding_batch_rejects_dimension_mismatch() -> None:
    with pytest.raises(EmbeddingProviderError, match="dimension"):
        validate_embedding_batch(["a"], [[0.1, 0.2]], expected_vector_size=4)


def test_app_settings_exposes_index_defaults() -> None:
    settings = AppSettings()

    assert settings.db_path.as_posix() == "var/metadata/knowledge.db"
    assert settings.qdrant_url == "http://localhost:6333"
    assert settings.qdrant_collection_prefix == "zyfangji_entries"
    assert settings.qdrant_alias == "zyfangji_entries_active"
    assert settings.embedding_provider == "bge_m3"
    assert settings.embedding_model_id == "BAAI/bge-m3"
    assert settings.embedding_vector_size == 1024
    assert settings.bm25_index_root.as_posix() == "var/indexes/bm25"
    assert settings.api_title == "Zyfangji Retrieval Service"


def test_get_settings_loads_project_dotenv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "ZYFANGJI_EMBEDDING_PROVIDER=silicon",
                "ZYFANGJI_EMBEDDING_ENDPOINT_URL=https://example.test/embeddings",
                "ZYFANGJI_EMBEDDING_API_KEY=secret-key",
                "ZYFANGJI_QDRANT_URL=http://localhost:6333",
            ]
        ),
        encoding="utf-8",
    )

    settings = get_settings()

    assert settings.embedding_provider == "silicon"
    assert settings.embedding_endpoint_url == "https://example.test/embeddings"
    assert settings.embedding_api_key == "secret-key"
    assert settings.qdrant_url == "http://localhost:6333"


def test_index_models_serialize_stable_status_fields() -> None:
    started_at = datetime(2026, 6, 14, 9, 0, tzinfo=UTC)
    finished_at = datetime(2026, 6, 14, 9, 1, tzinfo=UTC)
    updated_at = datetime(2026, 6, 14, 9, 2, tzinfo=UTC)

    build = IndexBuildRecord(
        index_version="idx-20260614090000",
        metadata_version="local-20260614080000",
        status="validated",
        entry_count=1248,
        vector_count=1248,
        bm25_doc_count=1248,
        provider_id="deterministic",
        model_id="deterministic-bge-m3-compatible",
        vector_size=4,
        started_at=started_at,
        finished_at=finished_at,
    )
    active = ActiveIndexRecord(
        index_version=build.index_version,
        metadata_version=build.metadata_version,
        qdrant_collection="zyfangji_entries_idx_20260614090000",
        qdrant_alias="zyfangji_entries_active",
        bm25_path="var/indexes/bm25/idx-20260614090000",
        updated_at=updated_at,
    )
    validation = IndexValidationResult(
        index_version=build.index_version,
        valid=True,
        expected_count=1248,
        vector_count=1248,
        bm25_doc_count=1248,
    )
    status = IndexStatus(
        ready=True,
        index_version=active.index_version,
        metadata_version=active.metadata_version,
        entry_count=build.entry_count,
        vector_count=build.vector_count,
        bm25_doc_count=build.bm25_doc_count,
        provider_id=build.provider_id,
        model_id=build.model_id,
        vector_size=build.vector_size,
        updated_at=updated_at,
        qdrant_collection=active.qdrant_collection,
        qdrant_alias=active.qdrant_alias,
        bm25_path=active.bm25_path,
        vector_store="qdrant",
        retrieval_strategy="bm25_dense_hybrid",
    )

    payload = {
        "build": build.model_dump(mode="json"),
        "active": active.model_dump(mode="json"),
        "validation": validation.model_dump(mode="json"),
        "status": status.model_dump(mode="json"),
    }

    assert payload["build"]["status"] == "validated"
    assert payload["active"]["qdrant_alias"] == "zyfangji_entries_active"
    assert payload["validation"]["valid"] is True
    assert payload["status"]["ready"] is True
    assert payload["status"]["reranker_enabled"] is False
    assert payload["status"]["reranker_model_id"] is None
    assert payload["status"]["reranker_status"] == "not_configured"
