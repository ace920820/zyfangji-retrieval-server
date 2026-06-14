from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field

from zyfangji_retrieval.domain.index_models import ActiveIndexRecord
from zyfangji_retrieval.indexing.embeddings import EmbeddingProvider


class VectorRecallCandidate(BaseModel):
    entry_id: str
    rank: int
    score: float
    payload: dict[str, Any] = Field(default_factory=dict)


class VectorStoreError(RuntimeError):
    pass


class VectorRetriever:
    def __init__(
        self,
        embedding_provider: EmbeddingProvider | None = None,
        qdrant_client: Any | None = None,
        embedding_provider_factory: Callable[[], EmbeddingProvider] | None = None,
    ) -> None:
        if embedding_provider is None and embedding_provider_factory is None:
            raise ValueError("embedding_provider or embedding_provider_factory is required")
        self.embedding_provider = embedding_provider
        self.embedding_provider_factory = embedding_provider_factory
        self.qdrant_client = qdrant_client

    def recall(
        self,
        query_text: str,
        active: ActiveIndexRecord,
        recall_topk: int,
    ) -> list[VectorRecallCandidate]:
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
        points = getattr(response, "points", response)
        candidates: list[VectorRecallCandidate] = []
        for rank, point in enumerate(points, start=1):
            payload = dict(getattr(point, "payload", {}) or {})
            entry_id = str(payload.get("entry_id") or getattr(point, "id", ""))
            if not entry_id:
                continue
            candidates.append(
                VectorRecallCandidate(
                    entry_id=entry_id,
                    rank=rank,
                    score=float(getattr(point, "score", 0.0)),
                    payload=payload,
                )
            )
        return candidates

    def _embedding_provider(self) -> EmbeddingProvider:
        if self.embedding_provider is None:
            if self.embedding_provider_factory is None:
                raise ValueError("embedding provider is not configured")
            self.embedding_provider = self.embedding_provider_factory()
        return self.embedding_provider
