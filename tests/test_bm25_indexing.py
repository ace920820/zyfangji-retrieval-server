import json
from pathlib import Path

from zyfangji_retrieval.domain.models import FormulaMention, KnowledgeEntry
from zyfangji_retrieval.indexing.bm25_store import BM25IndexStore
from zyfangji_retrieval.indexing.tokenizer import tokenize_chinese_text


def _entry(entry_id: str, retrieval_text: str, formula: str) -> KnowledgeEntry:
    return KnowledgeEntry(
        entry_id=entry_id,
        source_sheet="伤寒论",
        source_row=int(entry_id.rsplit("-", maxsplit=1)[-1]),
        formula_raw=formula,
        formula_mentions=[FormulaMention(name=formula)],
        formula_mapping_status="parsed",
        retrieval_text=retrieval_text,
        raw_record={},
        normalized_record={},
        source_article="太阳病，脉浮紧。",
        therapy="发汗解表",
        contraindication="不可误下",
        effect="汗出而解",
    )


def test_tokenize_chinese_text_preserves_project_tcm_terms() -> None:
    tokens = tokenize_chinese_text("太阳病 麻黄汤 脉浮紧")

    assert "太阳病" in tokens
    assert "麻黄汤" in tokens
    assert "脉浮紧" in tokens


def test_bm25_store_builds_versioned_index_with_metadata(tmp_path: Path) -> None:
    entries = [
        _entry("entry-1", "主症:\n恶风 发热\n\n脉象:\n脉浮紧", "麻黄汤"),
        _entry("entry-2", "主症:\n汗出 恶风\n\n脉象:\n脉浮缓", "桂枝汤"),
    ]

    metadata = BM25IndexStore(tmp_path).build("idx-20260614120000", entries)

    version_dir = tmp_path / "idx-20260614120000"
    assert version_dir.is_dir()
    assert (version_dir / "metadata.json").is_file()
    assert any(path.name != "metadata.json" for path in version_dir.iterdir())
    assert metadata.index_version == "idx-20260614120000"
    assert metadata.doc_count == 2
    assert metadata.entry_ids == ["entry-1", "entry-2"]
    assert metadata.created_at is not None
    assert metadata.tokenizer == "jieba+tcm_terms"

    metadata_json = json.loads((version_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata_json["index_version"] == "idx-20260614120000"
    assert metadata_json["doc_count"] == 2


def test_bm25_store_load_returns_same_doc_count_and_entry_ids(tmp_path: Path) -> None:
    entries = [
        _entry("entry-1", "主症:\n太阳病 伤寒", "麻黄汤"),
        _entry("entry-2", "主症:\n中风 恶风", "桂枝汤"),
    ]
    store = BM25IndexStore(tmp_path)
    store.build("idx-20260614120100", entries)

    loaded = store.load("idx-20260614120100")

    assert loaded.metadata.doc_count == 2
    assert loaded.metadata.entry_ids == ["entry-1", "entry-2"]
    assert loaded.index is not None
