import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from zyfangji_retrieval.api.app import create_app
from zyfangji_retrieval.domain.search_models import (
    EvidenceFields,
    PatientSearchRequest,
    SearchQuery,
    SearchResponse,
)
from zyfangji_retrieval.search.query import build_patient_query
from zyfangji_retrieval.search.service import SearchServiceError


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
        main_symptom="发热",
        source_article="第12条",
        western_medicine_priority=None,
    )

    assert evidence.western_medicine_priority is None


def test_search_response_documents_score_semantics() -> None:
    response = SearchResponse(
        query=SearchQuery(text="主症: 发热"),
        results=[],
        warnings=[],
    )

    assert (
        "not medical confidence, diagnosis probability, or prescription certainty"
        in response.score_semantics
    )


def test_build_patient_query_uses_labeled_sections_and_separate_symptom_lines() -> None:
    query = build_patient_query(
        PatientSearchRequest(
            main_symptom="发热恶寒",
            symptoms=["发热", "恶风"],
            tongue="舌淡",
            pulse="脉浮",
            syndrome="太阳中风证",
        )
    )

    assert query.terms_count == 6
    assert query.text == (
        "主症:\n发热恶寒\n\n"
        "复合症:\n发热\n恶风\n\n"
        "舌诊:\n舌淡\n\n"
        "脉象:\n脉浮\n\n"
        "证型:\n太阳中风证"
    )


def test_build_patient_query_emits_sparse_warning() -> None:
    query = build_patient_query(PatientSearchRequest(main_symptom="发热恶寒"))

    assert query.terms_count == 1
    assert [warning.code for warning in query.warnings] == ["query_too_sparse"]
    assert query.warnings[0].severity == "info"


def test_build_patient_query_emits_broad_warning_for_short_one_token_query() -> None:
    query = build_patient_query(PatientSearchRequest(main_symptom="寒"))

    assert [warning.code for warning in query.warnings] == [
        "query_too_sparse",
        "query_broad",
    ]
    assert all(warning.severity == "info" for warning in query.warnings)


def test_search_route_is_registered() -> None:
    app = create_app()
    routes = {route.path for route in app.routes if hasattr(route, "methods")}

    assert "/api/search" in routes


def test_search_route_returns_unavailable_error_without_service() -> None:
    app = create_app()
    del app.state.search_service
    client = TestClient(app)

    response = client.post("/api/search", json={"main_symptom": "发热恶寒"})

    assert response.status_code == 503
    assert response.json() == {
        "detail": {
            "error": {
                "code": "search_service_unavailable",
                "message": "Search service is not configured.",
                "details": {},
            }
        }
    }


def test_search_route_validation_error_uses_stable_error_envelope() -> None:
    client = TestClient(create_app())

    response = client.post("/api/search", json={"main_symptom": "发热", "topk": 51})

    payload = response.json()
    assert response.status_code == 422
    assert payload["detail"]["error"]["code"] == "validation_error"
    assert payload["detail"]["error"]["message"] == "Request validation failed."
    assert "traceback" not in str(payload).lower()


class _FakeSearchService:
    def search(self, request: PatientSearchRequest) -> SearchResponse:
        return SearchResponse(
            query=SearchQuery(text=f"主症:\n{request.main_symptom}"),
            results=[],
            warnings=[],
        )


def test_search_route_calls_attached_search_service() -> None:
    app = create_app()
    app.state.search_service = _FakeSearchService()
    client = TestClient(app)

    response = client.post("/api/search", json={"main_symptom": "发热恶寒"})

    assert response.status_code == 200
    assert response.json()["query"]["text"] == "主症:\n发热恶寒"


class _FailingSearchService:
    def search(self, request: PatientSearchRequest) -> SearchResponse:
        raise SearchServiceError(
            code="embedding_provider_unavailable",
            message="Embedding provider is unavailable.",
            details={"provider": "bge_m3"},
        )


def test_search_route_returns_typed_service_error() -> None:
    app = create_app()
    app.state.search_service = _FailingSearchService()
    client = TestClient(app)

    response = client.post("/api/search", json={"main_symptom": "发热恶寒"})

    assert response.status_code == 503
    assert response.json() == {
        "detail": {
            "error": {
                "code": "embedding_provider_unavailable",
                "message": "Embedding provider is unavailable.",
                "details": {"provider": "bge_m3"},
            }
        }
    }
