import hashlib
from collections.abc import Sequence
from typing import Protocol

from zyfangji_retrieval.domain.index_models import EmbeddingBatchResult


class EmbeddingProviderError(ValueError):
    pass


class EmbeddingProvider(Protocol):
    provider_id: str
    model_id: str
    vector_size: int

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        ...


class DeterministicEmbeddingProvider:
    provider_id = "deterministic"
    model_id = "deterministic-bge-m3-compatible"

    def __init__(self, vector_size: int = 4) -> None:
        if vector_size <= 0:
            raise EmbeddingProviderError("vector_size must be positive")
        self.vector_size = vector_size

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        vectors = [self._embed_text(text) for text in texts]
        validate_embedding_batch(texts, vectors, self.vector_size)
        return vectors

    def embed_batch(self, texts: Sequence[str]) -> EmbeddingBatchResult:
        vectors = self.embed_documents(texts)
        return EmbeddingBatchResult(
            texts_count=len(texts),
            vectors=vectors,
            provider_id=self.provider_id,
            model_id=self.model_id,
            vector_size=self.vector_size,
        )

    def _embed_text(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values: list[float] = []
        for index in range(self.vector_size):
            byte = digest[index % len(digest)]
            values.append(round((byte / 255.0) * 2.0 - 1.0, 8))
        return values


def validate_embedding_batch(
    texts: Sequence[str],
    vectors: Sequence[Sequence[float]],
    expected_vector_size: int,
) -> None:
    if expected_vector_size <= 0:
        raise EmbeddingProviderError("expected_vector_size must be positive")
    if len(vectors) != len(texts):
        raise EmbeddingProviderError(
            f"embedding count mismatch: got {len(vectors)} vectors for {len(texts)} texts"
        )
    for index, vector in enumerate(vectors):
        if len(vector) != expected_vector_size:
            raise EmbeddingProviderError(
                "embedding dimension mismatch: "
                f"vector {index} has {len(vector)} dimensions, expected {expected_vector_size}"
            )
