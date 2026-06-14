import pytest
from pydantic import ValidationError

from zyfangji_retrieval.domain.ids import make_entry_id
from zyfangji_retrieval.domain.models import FormulaMention, KnowledgeEntry


def test_make_entry_id_is_deterministic_with_shl_prefix() -> None:
    parts = ["伤寒论", "Sheet1", "4", "太阳病", "桂枝汤"]

    entry_id = make_entry_id(parts)

    assert entry_id == make_entry_id(parts)
    assert entry_id.startswith("shl_")
    assert len(entry_id) == len("shl_") + 16


def test_sparse_source_code_outside_parts_does_not_change_entry_id() -> None:
    base_parts = ["伤寒论", "Sheet1", "4", "太阳病", "桂枝汤"]
    source_code = "A001"
    changed_source_code = "B999"

    assert source_code != changed_source_code
    assert make_entry_id(base_parts) == make_entry_id(base_parts)


def test_knowledge_entry_separates_source_code_from_entry_id_and_records() -> None:
    mention = FormulaMention(name="桂枝汤")
    entry = KnowledgeEntry(
        entry_id=make_entry_id(["伤寒论", "Sheet1", "4", "太阳病", "桂枝汤"]),
        source_sheet="Sheet1",
        source_row=4,
        source_code="A001",
        formula_raw="桂枝汤",
        formula_mentions=[mention],
        formula_mapping_status="parsed",
        retrieval_text="主症:\n太阳病",
        raw_record={"编码": "A001", "推荐方剂": "桂枝汤"},
        normalized_record={"主病主症": "太阳病", "推荐方剂": "桂枝汤"},
    )

    payload = entry.model_dump()

    assert payload["entry_id"].startswith("shl_")
    assert payload["source_code"] == "A001"
    assert payload["source_code"] != payload["entry_id"]
    assert payload["raw_record"] == {"编码": "A001", "推荐方剂": "桂枝汤"}
    assert payload["normalized_record"] == {"主病主症": "太阳病", "推荐方剂": "桂枝汤"}


@pytest.mark.parametrize("status", ["parsed", "needs_review", "unmapped", "missing"])
def test_formula_mapping_status_accepts_defined_values(status: str) -> None:
    entry = KnowledgeEntry(
        entry_id=make_entry_id(["伤寒论", "Sheet1", "4", "太阳病", status]),
        source_sheet="Sheet1",
        source_row=4,
        formula_raw="",
        formula_mentions=[],
        formula_mapping_status=status,
        retrieval_text="主症:\n太阳病",
        raw_record={},
        normalized_record={},
    )

    assert entry.formula_mapping_status == status


def test_formula_mapping_status_rejects_unknown_value() -> None:
    with pytest.raises(ValidationError):
        KnowledgeEntry(
            entry_id=make_entry_id(["伤寒论", "Sheet1", "4", "太阳病", "bad"]),
            source_sheet="Sheet1",
            source_row=4,
            formula_raw="桂枝汤",
            formula_mentions=[],
            formula_mapping_status="unknown",
            retrieval_text="主症:\n太阳病",
            raw_record={},
            normalized_record={},
        )


def test_formula_mention_preserves_business_code_separate_from_formula_raw() -> None:
    mention = FormulaMention(name="麻黄汤", code="1001")
    entry = KnowledgeEntry(
        entry_id=make_entry_id(["伤寒论", "Sheet1", "35", "太阳伤寒证", "麻黄汤"]),
        source_sheet="Sheet1",
        source_row=35,
        source_code=None,
        formula_raw="麻黄汤（业务方剂编码另行映射）",
        formula_mentions=[mention],
        formula_mapping_status="parsed",
        retrieval_text="证型:\n太阳伤寒证",
        raw_record={"推荐方剂": "麻黄汤（业务方剂编码另行映射）"},
        normalized_record={"中医证型": "太阳伤寒证"},
    )

    payload = entry.model_dump()

    assert payload["formula_raw"] == "麻黄汤（业务方剂编码另行映射）"
    assert payload["formula_mentions"] == [
        {
            "name": "麻黄汤",
            "code": "1001",
            "branch_label": None,
            "needs_review": False,
            "raw_text": None,
        }
    ]
