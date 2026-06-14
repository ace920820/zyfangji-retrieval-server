from typing import Literal

from pydantic import BaseModel


FormulaMappingStatus = Literal["parsed", "needs_review", "unmapped", "missing"]


class FormulaMention(BaseModel):
    name: str
    code: str | None = None
    branch_label: str | None = None
    needs_review: bool = False
    raw_text: str | None = None


class RawSourceRecord(BaseModel):
    values: dict[str, str]


class KnowledgeEntry(BaseModel):
    entry_id: str
    source_book: str = "伤寒论"
    source_sheet: str
    source_row: int
    source_code: str | None = None
    formula_raw: str
    formula_mentions: list[FormulaMention]
    formula_mapping_status: FormulaMappingStatus
    retrieval_text: str
    raw_record: dict[str, str]
    normalized_record: dict[str, str]
    therapy: str | None = None
    tcm_disease: str | None = None
    western_disease: str | None = None
    source_article: str | None = None
    contraindication: str | None = None
    effect: str | None = None
