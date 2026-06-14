from pydantic import BaseModel

from zyfangji_retrieval.domain.search_models import PatientSearchRequest, QueryWarning


class PatientQuery(BaseModel):
    text: str
    terms_count: int
    warnings: list[QueryWarning]


def build_patient_query(request: PatientSearchRequest) -> PatientQuery:
    sections: list[str] = []
    terms: list[str] = []

    if request.main_symptom:
        _append_section(sections, terms, "主症", [request.main_symptom])
    if request.symptoms:
        _append_section(sections, terms, "复合症", request.symptoms)
    if request.tongue:
        _append_section(sections, terms, "舌诊", [request.tongue])
    if request.pulse:
        _append_section(sections, terms, "脉象", [request.pulse])
    if request.syndrome:
        _append_section(sections, terms, "证型", [request.syndrome])

    warnings: list[QueryWarning] = []
    if len(terms) < 2:
        warnings.append(
            QueryWarning(
                code="query_too_sparse",
                severity="info",
                message="Patient presentation contains fewer than two retrieval terms.",
            )
        )

    combined_text = "".join(terms)
    if len(combined_text) < 4:
        warnings.append(
            QueryWarning(
                code="query_broad",
                severity="info",
                message="Patient presentation is very short and may match broad results.",
            )
        )

    return PatientQuery(
        text="\n\n".join(sections),
        terms_count=len(terms),
        warnings=warnings,
    )


def _append_section(
    sections: list[str],
    terms: list[str],
    label: str,
    values: list[str],
) -> None:
    stripped_values = [value.strip() for value in values if value.strip()]
    if not stripped_values:
        return
    sections.append(f"{label}:\n" + "\n".join(stripped_values))
    terms.extend(stripped_values)
