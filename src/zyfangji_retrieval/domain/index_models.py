from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


IndexBuildStatus = Literal["building", "validated", "active", "failed"]


class EmbeddingBatchResult(BaseModel):
    texts_count: int
    vectors: list[list[float]]
    provider_id: str
    model_id: str
    vector_size: int


class IndexBuildRecord(BaseModel):
    index_version: str
    metadata_version: str
    status: IndexBuildStatus
    entry_count: int
    vector_count: int
    bm25_doc_count: int
    provider_id: str
    model_id: str
    vector_size: int
    started_at: datetime
    finished_at: datetime | None = None
    updated_at: datetime | None = None
    last_error: str | None = None
    qdrant_collection: str | None = None
    qdrant_alias: str | None = None
    bm25_path: str | None = None


class ActiveIndexRecord(BaseModel):
    index_version: str
    metadata_version: str
    qdrant_collection: str
    qdrant_alias: str
    bm25_path: str
    updated_at: datetime
    activated_at: datetime | None = None
    entry_count: int | None = None
    vector_count: int | None = None
    bm25_doc_count: int | None = None
    provider_id: str | None = None
    model_id: str | None = None
    vector_size: int | None = None
    last_error: str | None = None


class IndexStatus(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    ready: bool = False
    active_version: str | None = None
    indexed_count: int = 0
    index_version: str | None = None
    metadata_version: str | None = None
    entry_count: int = 0
    vector_count: int = 0
    bm25_doc_count: int = 0
    provider_id: str | None = None
    model_id: str | None = None
    vector_size: int | None = None
    last_build_time: datetime | None = None
    updated_at: datetime | None = None
    last_error: str | None = None
    qdrant_collection: str | None = None
    qdrant_alias: str | None = None
    bm25_path: str | None = None
    vector_store: str = "qdrant"
    retrieval_strategy: str = "bm25+dense"
    reranker_enabled: bool = False
    reranker_model_id: str | None = None
    reranker_status: str = "not_configured"


class IndexValidationResult(BaseModel):
    index_version: str
    valid: bool
    expected_count: int
    vector_count: int
    bm25_doc_count: int
    errors: list[str] = Field(default_factory=list)
    qdrant_collection: str | None = None
    qdrant_alias: str | None = None
    bm25_path: str | None = None
    updated_at: datetime | None = None
    last_error: str | None = None
