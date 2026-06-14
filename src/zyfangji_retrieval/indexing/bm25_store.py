from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import bm25s
from pydantic import BaseModel, ConfigDict, Field

from zyfangji_retrieval.domain.models import KnowledgeEntry
from zyfangji_retrieval.domain.index_models import IndexValidationResult
from zyfangji_retrieval.indexing.tokenizer import tokenize_chinese_text


class BM25IndexMetadata(BaseModel):
    index_version: str
    doc_count: int
    entry_ids: list[str] = Field(default_factory=list)
    created_at: datetime
    tokenizer: str = "jieba+tcm_terms"


class BM25IndexSnapshot(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    metadata: BM25IndexMetadata
    index: Any
    path: Path


class BM25IndexStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def build(self, index_version: str, entries: list[KnowledgeEntry]) -> BM25IndexMetadata:
        version_dir = self._version_dir(index_version)
        version_dir.mkdir(parents=True, exist_ok=True)
        documents = [self._compose_document(entry) for entry in entries]
        tokenized_corpus = [tokenize_chinese_text(document) for document in documents]

        index = bm25s.BM25()
        index.index(tokenized_corpus)
        index.save(version_dir)

        metadata = BM25IndexMetadata(
            index_version=index_version,
            doc_count=len(entries),
            entry_ids=[entry.entry_id for entry in entries],
            created_at=datetime.now(UTC),
        )
        self._write_metadata(version_dir, metadata)
        return metadata

    def load(self, index_version: str) -> BM25IndexSnapshot:
        version_dir = self._version_dir(index_version)
        metadata = self._read_metadata(version_dir)
        index = bm25s.BM25.load(version_dir, load_corpus=True)
        return BM25IndexSnapshot(metadata=metadata, index=index, path=version_dir)

    def validate(self, index_version: str, expected_count: int) -> IndexValidationResult:
        version_dir = self._version_dir(index_version)
        errors: list[str] = []
        metadata: BM25IndexMetadata | None = None
        bm25_doc_count = 0
        if not version_dir.exists():
            errors.append(f"bm25 version directory missing: {version_dir}")
        else:
            metadata_path = version_dir / "metadata.json"
            if not metadata_path.exists():
                errors.append(f"metadata.json missing: {metadata_path}")
            else:
                metadata = self._read_metadata(version_dir)
                bm25_doc_count = metadata.doc_count
                if metadata.doc_count != expected_count:
                    errors.append(
                        f"bm25 doc count mismatch: got {metadata.doc_count}, expected {expected_count}"
                    )
                if not self._index_files_present(version_dir):
                    errors.append(f"bm25 index files missing in: {version_dir}")
                if len(metadata.entry_ids) != metadata.doc_count:
                    errors.append("bm25 metadata entry_ids count mismatch")
        return IndexValidationResult(
            index_version=index_version,
            valid=not errors,
            expected_count=expected_count,
            vector_count=0,
            bm25_doc_count=bm25_doc_count,
            errors=errors,
            bm25_path=str(version_dir),
            updated_at=datetime.now(UTC),
            last_error="; ".join(errors) if errors else None,
        )

    def _compose_document(self, entry: KnowledgeEntry) -> str:
        mention_names = " ".join(
            mention.name.strip() for mention in entry.formula_mentions if mention.name.strip()
        )
        parts = [
            entry.retrieval_text,
            entry.formula_raw,
            mention_names,
            entry.source_article or "",
            entry.therapy or "",
            entry.contraindication or "",
            entry.effect or "",
        ]
        return "\n".join(part.strip() for part in parts if part and part.strip())

    def _version_dir(self, index_version: str) -> Path:
        return self.root / index_version

    def _metadata_path(self, version_dir: Path) -> Path:
        return version_dir / "metadata.json"

    def _write_metadata(self, version_dir: Path, metadata: BM25IndexMetadata) -> None:
        self._metadata_path(version_dir).write_text(
            metadata.model_dump_json(indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _read_metadata(self, version_dir: Path) -> BM25IndexMetadata:
        return BM25IndexMetadata.model_validate_json(
            self._metadata_path(version_dir).read_text(encoding="utf-8")
        )

    def _index_files_present(self, version_dir: Path) -> bool:
        required_suffixes = {
            "data.csc.index.npy",
            "indices.csc.index.npy",
            "indptr.csc.index.npy",
            "vocab.index.json",
            "params.index.json",
        }
        present = {path.name for path in version_dir.iterdir()}
        return required_suffixes.issubset(present)
