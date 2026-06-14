from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from zyfangji_retrieval.domain.index_models import ActiveIndexRecord
from zyfangji_retrieval.indexing.embeddings import EmbeddingProvider


class VectorRecallCandidate(BaseModel):
    entry_id: str
    rank: int
    score: float
    payload: dict[str, Any] = Field(default_factory=dict)


class VectorRetriever:
    def __init__(self, embedding_provider: EmbeddingProvider, qdrant_client: Any) -> None:
        self.embedding_provider = embedding_provider
        self.qdrant_client = qdrant_client

    def recall(
        self,
        query_text: str,
        active: ActiveIndexRecord,
        recall_topk: int,
    ) -> list[VectorRecallCandidate]:
        query_vector = self.embedding_provider.embed_documents([query_text])[0]
        response = self.qdrant_client.query_points(
            collection_name=active.qdrant_collection,
            query=query_vector,
            limit=recall_topk,
            with_payload=True,
            with_vectors=False,
        )
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
