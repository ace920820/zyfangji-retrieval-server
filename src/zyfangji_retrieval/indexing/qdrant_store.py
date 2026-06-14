import re
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from qdrant_client import models

from zyfangji_retrieval.domain.index_models import IndexValidationResult
from zyfangji_retrieval.domain.models import KnowledgeEntry
from zyfangji_retrieval.indexing.embeddings import validate_embedding_batch


_COLLECTION_SAFE_PATTERN = re.compile(r"[^a-zA-Z0-9_]+")


def build_qdrant_payload(entry: KnowledgeEntry) -> dict[str, object]:
    return {
        "entry_id": entry.entry_id,
        "source_book": entry.source_book,
        "source_sheet": entry.source_sheet,
        "source_row": entry.source_row,
        "source_code": entry.source_code,
        "formula_raw": entry.formula_raw,
        "formula_mapping_status": entry.formula_mapping_status,
        "formula_mentions": [
            mention.model_dump(mode="json", exclude_none=False)
            for mention in entry.formula_mentions
        ],
        "source_article": entry.source_article,
        "therapy": entry.therapy,
        "tcm_disease": entry.tcm_disease,
        "western_disease": entry.western_disease,
        "contraindication": entry.contraindication,
        "effect": entry.effect,
        "retrieval_text": entry.retrieval_text,
    }


class QdrantVectorIndex:
    def __init__(
        self,
        client: Any,
        collection_prefix: str,
        alias_name: str,
        vector_size: int,
    ) -> None:
        if vector_size <= 0:
            raise ValueError("vector_size must be positive")
        self.client = client
        self.collection_prefix = self._sanitize_name(collection_prefix)
        self.alias_name = self._sanitize_name(alias_name)
        self.vector_size = vector_size

    def collection_name(self, index_version: str) -> str:
        return f"{self.collection_prefix}_{self._sanitize_name(index_version)}"

    def create_collection(self, index_version: str) -> str:
        collection_name = self.collection_name(index_version)
        if self._collection_exists(collection_name):
            return collection_name
        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(size=self.vector_size, distance=models.Distance.COSINE),
        )
        return collection_name

    def upsert_entries(
        self,
        index_version: str,
        entries: Sequence[KnowledgeEntry],
        vectors: Sequence[Sequence[float]],
    ) -> int:
        validate_embedding_batch(
            [entry.retrieval_text for entry in entries],
            vectors,
            expected_vector_size=self.vector_size,
        )
        collection_name = self.collection_name(index_version)
        points = [
            models.PointStruct(
                id=self._point_id(index_version, entry.entry_id, position),
                vector=list(vector),
                payload=build_qdrant_payload(entry),
            )
            for position, (entry, vector) in enumerate(zip(entries, vectors, strict=True))
        ]
        if points:
            self.client.upsert(collection_name=collection_name, points=points)
        return len(points)

    def validate_collection(self, index_version: str, expected_count: int) -> IndexValidationResult:
        collection_name = self.collection_name(index_version)
        errors: list[str] = []
        if not self._collection_exists(collection_name):
            errors.append(f"collection does not exist: {collection_name}")
            vector_count = 0
        else:
            count_result = self.client.count(collection_name=collection_name, exact=True)
            vector_count = int(count_result.count)
            if vector_count != expected_count:
                errors.append(
                    f"vector count mismatch: got {vector_count}, expected {expected_count}"
                )
        return IndexValidationResult(
            index_version=index_version,
            valid=not errors,
            expected_count=expected_count,
            vector_count=vector_count,
            bm25_doc_count=0,
            errors=errors,
            qdrant_collection=collection_name,
            qdrant_alias=self.alias_name,
            updated_at=datetime.now(UTC),
            last_error="; ".join(errors) if errors else None,
        )

    def activate_alias(self, index_version: str) -> str:
        collection_name = self.collection_name(index_version)
        self.client.update_collection_aliases(
            change_aliases_operations=[
                models.DeleteAliasOperation(
                    delete_alias=models.DeleteAlias(alias_name=self.alias_name)
                ),
                models.CreateAliasOperation(
                    create_alias=models.CreateAlias(
                        collection_name=collection_name,
                        alias_name=self.alias_name,
                    )
                ),
            ]
        )
        return self.alias_name

    def _collection_exists(self, collection_name: str) -> bool:
        if hasattr(self.client, "collection_exists"):
            return bool(self.client.collection_exists(collection_name))
        try:
            self.client.get_collection(collection_name=collection_name)
        except Exception:
            return False
        return True

    @staticmethod
    def _sanitize_name(value: str) -> str:
        sanitized = _COLLECTION_SAFE_PATTERN.sub("_", value.strip()).strip("_")
        if not sanitized:
            raise ValueError("collection name component cannot be empty")
        return sanitized

    @staticmethod
    def _point_id(index_version: str, entry_id: str, position: int) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{index_version}:{position}:{entry_id}"))
