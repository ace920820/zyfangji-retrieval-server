from zyfangji_retrieval.config import AppSettings
from zyfangji_retrieval.domain.index_models import ActiveIndexRecord, IndexBuildRecord, IndexStatus
from zyfangji_retrieval.persistence.index_state import SQLiteIndexStateStore


class IndexStatusService:
    def __init__(self, index_state_store: SQLiteIndexStateStore, settings: AppSettings) -> None:
        self.index_state_store = index_state_store
        self.settings = settings

    def status(self) -> IndexStatus:
        active = self.index_state_store.get_active()
        latest_build = self.index_state_store.get_latest_build()
        latest_error = self._latest_failed_error(latest_build)
        if active is None:
            return IndexStatus(
                ready=False,
                active_version=None,
                indexed_count=0,
                vector_store="qdrant",
                retrieval_strategy="bm25+dense",
                reranker_enabled=False,
                reranker_model_id=None,
                reranker_status="not_configured",
                last_build_time=self._latest_build_time(latest_build),
                last_error=latest_error,
            )

        ready = self._active_is_consistent(active)
        return IndexStatus(
            ready=ready,
            active_version=active.index_version,
            metadata_version=active.metadata_version,
            indexed_count=active.entry_count or 0,
            entry_count=active.entry_count or 0,
            vector_count=active.vector_count or 0,
            bm25_doc_count=active.bm25_doc_count or 0,
            provider_id=active.provider_id,
            model_id=active.model_id,
            vector_size=active.vector_size,
            updated_at=active.updated_at,
            last_build_time=self._latest_build_time(latest_build),
            last_error=latest_error,
            qdrant_collection=active.qdrant_collection,
            qdrant_alias=active.qdrant_alias,
            bm25_path=active.bm25_path,
            vector_store="qdrant",
            retrieval_strategy="bm25+dense",
            reranker_enabled=False,
            reranker_model_id=None,
            reranker_status="not_configured",
        )

    def _active_is_consistent(self, active: ActiveIndexRecord) -> bool:
        if active.entry_count is None or active.entry_count <= 0:
            return False
        return (
            active.vector_count == active.entry_count
            and active.bm25_doc_count == active.entry_count
            and bool(active.bm25_path)
        )

    def _latest_failed_error(self, latest_build: IndexBuildRecord | None) -> str | None:
        if latest_build is not None and latest_build.status == "failed":
            return latest_build.last_error
        return None

    def _latest_build_time(self, latest_build: IndexBuildRecord | None) -> object:
        if latest_build is None:
            return None
        return latest_build.finished_at or latest_build.updated_at or latest_build.started_at
