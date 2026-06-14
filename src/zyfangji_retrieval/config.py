from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ZYFANGJI_", extra="ignore")

    db_path: Path = Path("var/metadata/knowledge.db")
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection_prefix: str = "zyfangji_entries"
    qdrant_alias: str = "zyfangji_entries_active"
    embedding_provider: str = "bge_m3"
    embedding_model_id: str = "BAAI/bge-m3"
    embedding_vector_size: int = 1024
    embedding_endpoint_url: str | None = None
    embedding_api_key: str | None = None
    bm25_index_root: Path = Path("var/indexes/bm25")
    search_default_topk: int = 10
    search_max_topk: int = 50
    recall_topk: int = 50
    fusion_strategy: str = "rrf"
    rrf_k: int = 60
    reranker_provider: str = "bge"
    reranker_model_id: str = "BAAI/bge-reranker-v2-m3"
    reranker_required: bool = True
    api_title: str = "Zyfangji Retrieval Service"


def get_settings() -> AppSettings:
    return AppSettings()
