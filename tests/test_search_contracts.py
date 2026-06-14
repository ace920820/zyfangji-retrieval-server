import pytest
from pydantic import ValidationError

from zyfangji_retrieval.domain.search_models import (
    EvidenceFields,
    PatientSearchRequest,
    SearchResponse,
)


def test_patient_search_request_defaults_topk_to_10() -> None:
    request = PatientSearchRequest(main_symptom="发热恶寒")

    assert request.topk == 10


def test_patient_search_request_rejects_topk_above_50() -> None:
    with pytest.raises(ValidationError):
        PatientSearchRequest(main_symptom="发热恶寒", topk=51)


@pytest.mark.parametrize("field", ["main_symptom", "tongue", "pulse", "syndrome"])
def test_patient_search_request_rejects_oversized_presentation_fields(
    field: str,
) -> None:
    with pytest.raises(ValidationError):
        PatientSearchRequest(**{field: "x" * 501})


def test_patient_search_request_rejects_oversized_symptom_item() -> None:
    with pytest.raises(ValidationError):
        PatientSearchRequest(symptoms=["x" * 201])


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"main_symptom": "   "},
        {"symptoms": [" ", "\t"], "tongue": None, "pulse": "", "syndrome": " "},
    ],
)
def test_patient_search_request_rejects_empty_patient_presentation(
    payload: dict[str, object],
) -> None:
    with pytest.raises(
        ValidationError,
        match="at least one patient presentation field is required",
    ):
        PatientSearchRequest(**payload)


def test_evidence_fields_allows_nullable_formula_code() -> None:
    evidence = EvidenceFields(
        entry_id="entry-1",
        source_book="伤寒论",
        source_sheet="Sheet1",
        source_row=12,
        formula_name="桂枝汤",
        formula_code=None,
        formula_mapping_status="unmapped",
    )

    assert evidence.formula_code is None


def test_search_response_documents_score_semantics() -> None:
    response = SearchResponse(
        query_text="主症: 发热",
        results=[],
        warnings=[],
    )

    assert (
        "not medical confidence, diagnosis probability, or prescription certainty"
        in response.score_semantics
    )
