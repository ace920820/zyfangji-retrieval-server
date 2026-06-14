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


class SearchQuery(BaseModel):
    text: str


class SearchResultSource(BaseModel):
    book: str
    sheet: str
    row: int
    article: str | None = None


class EvidenceFields(BaseModel):
    main_symptom: str | None = None
    complex_symptom: str | None = None
    detail_symptom: str | None = None
    alias: str | None = None
    tongue: str | None = None
    pulse: str | None = None
    source_article: str | None = None
    syndrome: str | None = None
    tcm_disease: str | None = None
    western_disease: str | None = None
    therapy: str | None = None
    contraindication: str | None = None
    effect: str | None = None
    western_medicine_priority: str | None = None


class SearchResult(BaseModel):
    rank: int
    retrieval_score: float
    score_type: str = "rerank_score"
    entry_id: str
    source: SearchResultSource
    formula_raw: str
    formula_mentions: list[object] = Field(default_factory=list)
    formula_code: str | None = None
    formula_mapping_status: str
    evidence: EvidenceFields
    signal_scores: SignalScores = Field(default_factory=SignalScores)


class SearchPipelineMetadata(BaseModel):
    index_version: str | None = None
    metadata_version: str | None = None
    requested_topk: int = 10
    recall_topk: int = 50
    fusion_strategy: str = "rrf"
    reranker_model_id: str | None = "BAAI/bge-reranker-v2-m3"
    pipeline_status: str = "not_run"


class SearchResponse(BaseModel):
    query: SearchQuery
    results: list[SearchResult]
    warnings: list[QueryWarning] = Field(default_factory=list)
    metadata: SearchPipelineMetadata = Field(default_factory=SearchPipelineMetadata)
    score_semantics: str = SCORE_SEMANTICS


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
