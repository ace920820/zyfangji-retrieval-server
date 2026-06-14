from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from zyfangji_retrieval.domain.index_models import ActiveIndexRecord, IndexBuildRecord
from zyfangji_retrieval.ingestion.importer import load_entries_for_rebuild
from zyfangji_retrieval.indexing.embeddings import EmbeddingProvider, validate_embedding_batch
from zyfangji_retrieval.indexing.validation import merge_validation_results


class IndexLifecycleError(RuntimeError):
    pass


def build_index_version(prefix: str = "idx") -> str:
    return f"{prefix}-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"


class IndexLifecycleService:
    def __init__(
        self,
        db_path: Path,
        metadata_version: str,
        embedding_provider: EmbeddingProvider,
        qdrant_index: object,
        bm25_store: object,
        index_state_store: object,
    ) -> None:
        self.db_path = db_path
        self.metadata_version = metadata_version
        self.embedding_provider = embedding_provider
        self.qdrant_index = qdrant_index
        self.bm25_store = bm25_store
        self.index_state_store = index_state_store

    def rebuild(self, activate: bool = True) -> IndexBuildRecord:
        index_version = build_index_version()
        entries = load_entries_for_rebuild(self.db_path, index_version=self.metadata_version)
        record = IndexBuildRecord(
            index_version=index_version,
            metadata_version=self.metadata_version,
            status="building",
            entry_count=len(entries),
            vector_count=0,
            bm25_doc_count=0,
            provider_id=self.embedding_provider.provider_id,
            model_id=self.embedding_provider.model_id,
            vector_size=self.embedding_provider.vector_size,
            started_at=datetime.now(UTC),
        )
        self.index_state_store.start_build(record)
        try:
            texts = [entry.retrieval_text for entry in entries]
            vectors = self.embedding_provider.embed_documents(texts)
            validate_embedding_batch(texts, vectors, self.embedding_provider.vector_size)

            qdrant_collection = self.qdrant_index.create_collection(index_version)
            vector_count = self.qdrant_index.upsert_entries(index_version, entries, vectors)
            qdrant_result = self.qdrant_index.validate_collection(
                index_version,
                expected_count=len(entries),
            )

            bm25_metadata = self.bm25_store.build(index_version, entries)
            bm25_result = self.bm25_store.validate(index_version, expected_count=len(entries))
            validation = merge_validation_results(
                index_version,
                expected_count=len(entries),
                vector_result=qdrant_result,
                bm25_result=bm25_result,
            )
            if not validation.valid:
                raise IndexLifecycleError(validation.last_error or "index validation failed")

            validated = self.index_state_store.mark_validated(
                index_version,
                vector_count=vector_count,
                bm25_doc_count=bm25_metadata.doc_count,
                qdrant_collection=qdrant_collection,
                bm25_path=validation.bm25_path or "",
            )
            if not activate:
                return validated

            qdrant_alias = self.qdrant_index.activate_alias(index_version)
            active = ActiveIndexRecord(
                index_version=index_version,
                metadata_version=self.metadata_version,
                qdrant_collection=qdrant_collection,
                qdrant_alias=qdrant_alias,
                bm25_path=validation.bm25_path or "",
                updated_at=datetime.now(UTC),
                entry_count=len(entries),
                vector_count=vector_count,
                bm25_doc_count=bm25_metadata.doc_count,
                provider_id=self.embedding_provider.provider_id,
                model_id=self.embedding_provider.model_id,
                vector_size=self.embedding_provider.vector_size,
            )
            self.index_state_store.activate(active)
            active_build = self.index_state_store.get_build(index_version)
            if active_build is None:
                raise IndexLifecycleError(f"active build missing: {index_version}")
            return active_build
        except Exception as error:
            self.index_state_store.mark_failed(index_version, str(error))
            if isinstance(error, IndexLifecycleError):
                raise
            raise IndexLifecycleError(str(error)) from error
