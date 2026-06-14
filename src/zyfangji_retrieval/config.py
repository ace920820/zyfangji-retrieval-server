from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ZYFANGJI_", extra="ignore")

    db_path: Path = Path("var/metadata/knowledge.db")
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection_prefix: str = "zyfangji_entries"
    qdrant_alias: str = "zyfangji_entries_active"
    embedding_provider: str = "deterministic"
    embedding_model_id: str = "deterministic-bge-m3-compatible"
    embedding_vector_size: int = 4
    bm25_index_root: Path = Path("var/indexes/bm25")
    api_title: str = "Zyfangji Retrieval Service"


def get_settings() -> AppSettings:
    return AppSettings()
