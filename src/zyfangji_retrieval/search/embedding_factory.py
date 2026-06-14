from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import httpx

from zyfangji_retrieval.config import AppSettings
from zyfangji_retrieval.indexing.embeddings import (
    DeterministicEmbeddingProvider,
    EmbeddingProvider,
    EmbeddingProviderError,
)


class BgeM3HttpEmbeddingProvider:
    provider_id = "bge_m3"

    def __init__(
        self,
        endpoint_url: str,
        api_key: str | None,
        model_id: str = "BAAI/bge-m3",
        vector_size: int = 1024,
        timeout_seconds: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        if not endpoint_url:
            raise EmbeddingProviderError("bge_m3 embedding endpoint is not configured")
        if vector_size <= 0:
            raise EmbeddingProviderError("vector_size must be positive")
        self.endpoint_url = endpoint_url
        self.api_key = api_key
        self.model_id = model_id
        self.vector_size = vector_size
        self.timeout_seconds = timeout_seconds
        self.client = client or httpx.Client()

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        text_list = list(texts)
        try:
            response = self.client.post(
                self.endpoint_url,
                json={"model": self.model_id, "input": text_list},
                headers=(
                    {"Authorization": f"Bearer {self.api_key}"}
                    if self.api_key
                    else None
                ),
                timeout=self.timeout_seconds,
            )
        except Exception as exc:
            raise EmbeddingProviderError("embedding provider unavailable") from exc

        if getattr(response, "status_code", 500) < 200 or getattr(response, "status_code", 500) >= 300:
            raise EmbeddingProviderError("embedding provider unavailable")

        try:
            payload = response.json()
        except Exception as exc:
            raise EmbeddingProviderError("malformed embedding provider response") from exc

        vectors = self._extract_vectors(payload)
        self._validate_vectors(text_list, vectors)
        return vectors

    def _extract_vectors(self, payload: Any) -> list[list[float]]:
        if not isinstance(payload, dict):
            raise EmbeddingProviderError("malformed embedding provider response")
        if "data" in payload:
            data = payload["data"]
            if not isinstance(data, list):
                raise EmbeddingProviderError("malformed embedding provider response")
            try:
                return [list(item["embedding"]) for item in data]
            except (KeyError, TypeError) as exc:
                raise EmbeddingProviderError("malformed embedding provider response") from exc
        if "embeddings" in payload:
            embeddings = payload["embeddings"]
            if not isinstance(embeddings, list):
                raise EmbeddingProviderError("malformed embedding provider response")
            return [list(vector) for vector in embeddings]
        raise EmbeddingProviderError("malformed embedding provider response")

    def _validate_vectors(self, texts: list[str], vectors: list[list[float]]) -> None:
        if len(vectors) != len(texts):
            raise EmbeddingProviderError(
                f"embedding count mismatch: got {len(vectors)} vectors for {len(texts)} texts"
            )
        for index, vector in enumerate(vectors):
            if len(vector) != self.vector_size:
                raise EmbeddingProviderError(
                    "embedding vector_size mismatch: "
                    f"vector {index} has {len(vector)} dimensions, expected {self.vector_size}"
                )
            try:
                vectors[index] = [float(value) for value in vector]
            except (TypeError, ValueError) as exc:
                raise EmbeddingProviderError("malformed embedding provider response") from exc


def build_embedding_provider(settings: AppSettings) -> EmbeddingProvider:
    if settings.embedding_provider == "bge_m3":
        if not settings.embedding_endpoint_url:
            raise EmbeddingProviderError("bge_m3 embedding endpoint is not configured")
        return BgeM3HttpEmbeddingProvider(
            endpoint_url=settings.embedding_endpoint_url,
            api_key=settings.embedding_api_key,
            model_id=settings.embedding_model_id,
            vector_size=settings.embedding_vector_size,
            timeout_seconds=getattr(settings, "embedding_timeout_seconds", 30.0),
        )
    if settings.embedding_provider == "deterministic":
        return DeterministicEmbeddingProvider(vector_size=settings.embedding_vector_size)
    raise EmbeddingProviderError(f"unsupported embedding provider: {settings.embedding_provider}")
