from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator


SymptomText = Annotated[str, Field(max_length=200)]

SCORE_SEMANTICS = (
    "Retrieval scores are relative ranking/reference signals only, "
    "not medical confidence, diagnosis probability, or prescription certainty."
)


class PatientSearchRequest(BaseModel):
    main_symptom: str | None = Field(default=None, max_length=500)
    symptoms: list[SymptomText] = Field(default_factory=list, max_length=20)
    tongue: str | None = Field(default=None, max_length=500)
    pulse: str | None = Field(default=None, max_length=500)
    syndrome: str | None = Field(default=None, max_length=500)
    topk: int = Field(default=10, ge=1, le=50)

    @model_validator(mode="after")
    def strip_and_require_presentation(self) -> "PatientSearchRequest":
        self.main_symptom = _strip_optional(self.main_symptom)
        self.symptoms = [_strip for item in self.symptoms if (_strip := item.strip())]
        self.tongue = _strip_optional(self.tongue)
        self.pulse = _strip_optional(self.pulse)
        self.syndrome = _strip_optional(self.syndrome)
        if not any(
            [
                self.main_symptom,
                self.symptoms,
                self.tongue,
                self.pulse,
                self.syndrome,
            ]
        ):
            raise ValueError("at least one patient presentation field is required")
        return self


class QueryWarning(BaseModel):
    code: str
    severity: Literal["info", "warning"] = "info"
    message: str


class SignalScores(BaseModel):
    bm25_score: float | None = None
    vector_score: float | None = None
    fused_score: float | None = None
    rerank_score: float | None = None


class EvidenceFields(BaseModel):
    entry_id: str
    source_book: str
    source_sheet: str
    source_row: int
    formula_name: str
    formula_code: str | None = None
    formula_mapping_status: str
    therapy: str | None = None
    tcm_disease: str | None = None
    western_disease: str | None = None
    source_article: str | None = None
    contraindication: str | None = None
    effect: str | None = None
    raw_record: dict[str, str] = Field(default_factory=dict)
    normalized_record: dict[str, str] = Field(default_factory=dict)


class SearchResult(BaseModel):
    rank: int
    match_score: float
    score_type: str = "retrieval_ranking"
    scores: SignalScores = Field(default_factory=SignalScores)
    evidence: EvidenceFields


class SearchPipelineMetadata(BaseModel):
    index_version: str | None = None
    metadata_version: str | None = None
    recall_topk: int = 50
    fusion_strategy: str = "rrf"
    reranker_model_id: str | None = "BAAI/bge-reranker-v2-m3"


class SearchResponse(BaseModel):
    query_text: str
    results: list[SearchResult]
    warnings: list[QueryWarning] = Field(default_factory=list)
    score_semantics: str = SCORE_SEMANTICS
    pipeline: SearchPipelineMetadata = Field(default_factory=SearchPipelineMetadata)


class SearchError(BaseModel):
    code: str
    message: str
    details: dict[str, object] = Field(default_factory=dict)


class SearchErrorEnvelope(BaseModel):
    error: SearchError


def _strip_optional(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
