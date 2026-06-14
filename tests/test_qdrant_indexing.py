from typing import Any

import pytest

from zyfangji_retrieval.domain.models import FormulaMention, KnowledgeEntry
from zyfangji_retrieval.indexing.embeddings import EmbeddingProviderError
from zyfangji_retrieval.indexing.qdrant_store import QdrantVectorIndex, build_qdrant_payload


class FakeQdrantClient:
    def __init__(self) -> None:
        self.collections: dict[str, dict[str, Any]] = {}
        self.upserts: list[tuple[str, list[Any]]] = []
        self.alias_actions: list[Any] = []

    def collection_exists(self, collection_name: str) -> bool:
        return collection_name in self.collections

    def create_collection(self, collection_name: str, vectors_config: Any) -> None:
        self.collections[collection_name] = {
            "vectors_config": vectors_config,
            "points": [],
        }

    def upsert(self, collection_name: str, points: list[Any]) -> None:
        self.upserts.append((collection_name, points))
        self.collections[collection_name]["points"].extend(points)

    def count(self, collection_name: str, exact: bool = True) -> Any:
        class CountResult:
            def __init__(self, count: int) -> None:
                self.count = count

        return CountResult(len(self.collections[collection_name]["points"]))

    def update_collection_aliases(self, change_aliases_operations: list[Any]) -> None:
        self.alias_actions.extend(change_aliases_operations)


def _entry() -> KnowledgeEntry:
    return KnowledgeEntry(
        entry_id="shl_test_0001",
        source_book="伤寒论",
        source_sheet="Sheet1",
        source_row=4,
        source_code="A001",
        formula_raw="桂枝汤",
        formula_mentions=[
            FormulaMention(
                name="桂枝汤",
                code="F001",
                branch_label="太阳中风",
                needs_review=False,
                raw_text="桂枝汤",
            )
        ],
        formula_mapping_status="parsed",
        retrieval_text="主症:\n头痛\n\n脉象:\n浮缓",
        raw_record={"编码": "A001", "推荐方剂": "桂枝汤"},
        normalized_record={"主病主症": "头痛", "推荐方剂": "桂枝汤"},
        therapy="解肌发表",
        tcm_disease="太阳病",
        western_disease="感冒",
        source_article="太阳病，头痛，发热，汗出，恶风，桂枝汤主之。",
        contraindication="高热持续先排除急症",
        effect="汗出热退",
    )


def test_build_qdrant_payload_preserves_canonical_entry_fields() -> None:
    payload = build_qdrant_payload(_entry())

    assert payload["entry_id"] == "shl_test_0001"
    assert payload["source_book"] == "伤寒论"
    assert payload["source_sheet"] == "Sheet1"
    assert payload["source_row"] == 4
    assert payload["source_code"] == "A001"
    assert payload["formula_raw"] == "桂枝汤"
    assert payload["formula_mapping_status"] == "parsed"
    assert payload["formula_mentions"] == [
        {
            "name": "桂枝汤",
            "code": "F001",
            "branch_label": "太阳中风",
            "needs_review": False,
            "raw_text": "桂枝汤",
        }
    ]
    assert payload["source_article"] == "太阳病，头痛，发热，汗出，恶风，桂枝汤主之。"
    assert payload["therapy"] == "解肌发表"
    assert payload["contraindication"] == "高热持续先排除急症"
    assert payload["effect"] == "汗出热退"
    assert payload["retrieval_text"] == "主症:\n头痛\n\n脉象:\n浮缓"
    assert "api_key" not in payload


def test_collection_name_is_deterministic_and_sanitized() -> None:
    store = QdrantVectorIndex(
        client=FakeQdrantClient(),
        collection_prefix="zyfangji_entries",
        alias_name="zyfangji_entries_active",
        vector_size=4,
    )

    assert store.collection_name("idx-20260614090000") == "zyfangji_entries_idx_20260614090000"


def test_upsert_entries_validates_shape_before_client_call() -> None:
    client = FakeQdrantClient()
    store = QdrantVectorIndex(
        client=client,
        collection_prefix="zyfangji_entries",
        alias_name="zyfangji_entries_active",
        vector_size=4,
    )
    store.create_collection("idx-20260614090000")

    with pytest.raises(EmbeddingProviderError, match="count"):
        store.upsert_entries("idx-20260614090000", [_entry()], [])

    with pytest.raises(EmbeddingProviderError, match="dimension"):
        store.upsert_entries("idx-20260614090000", [_entry()], [[0.1, 0.2]])

    assert client.upserts == []


def test_repository_uses_fake_client_without_network_service() -> None:
    client = FakeQdrantClient()
    store = QdrantVectorIndex(
        client=client,
        collection_prefix="zyfangji_entries",
        alias_name="zyfangji_entries_active",
        vector_size=4,
    )

    collection_name = store.create_collection("idx-20260614090000")
    upserted = store.upsert_entries("idx-20260614090000", [_entry()], [[0.1, 0.2, 0.3, 0.4]])
    validation = store.validate_collection("idx-20260614090000", expected_count=1)
    alias = store.activate_alias("idx-20260614090000")

    assert collection_name == "zyfangji_entries_idx_20260614090000"
    assert upserted == 1
    assert validation.valid is True
    assert validation.vector_count == 1
    assert validation.qdrant_collection == collection_name
    assert alias == "zyfangji_entries_active"
    assert client.alias_actions
    assert client.collections[collection_name]["points"][0].payload["entry_id"] == "shl_test_0001"
