from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from fastapi import FastAPI

from zyfangji_retrieval.api.app import create_app
from zyfangji_retrieval.config import AppSettings


README_PATH = Path("README.md")
API_DOC_PATH = Path("docs/API.md")
DEMO_DOC_PATH = Path("docs/DEMO.md")
DEPLOYMENT_DOC_PATH = Path("docs/DEPLOYMENT.md")
ENV_EXAMPLE_PATH = Path(".env.example")


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def _openapi() -> dict[str, object]:
    app: FastAPI = create_app(
        AppSettings(
            embedding_provider="deterministic",
            reranker_provider="deterministic",
        )
    )
    return app.openapi()


def test_openapi_exposes_current_http_routes_only() -> None:
    spec = _openapi()
    paths = set(spec["paths"])

    assert {"/api/search", "/status", "/health/live", "/health/ready"} <= paths
    assert "/api/import" not in paths
    assert "/import" not in paths
    assert "/api/rebuild" not in paths
    assert "/rebuild" not in paths

    search = spec["paths"]["/api/search"]["post"]
    request_schema = search["requestBody"]["content"]["application/json"]["schema"]
    assert request_schema["$ref"].endswith("PatientSearchRequest")
    assert {"200", "422", "503"} <= set(search["responses"].keys())

    patient_schema = spec["components"]["schemas"]["PatientSearchRequest"]
    assert {"main_symptom", "symptoms", "tongue", "pulse", "syndrome", "topk"} <= set(
        patient_schema["properties"]
    )


def test_readme_documents_mvp_boundaries_and_links() -> None:
    text = _read("README.md")
    assert "只做检索" in text
    assert "OpenAPI is available at /docs and /openapi.json" in text
    assert "CLI-only operator workflows in v1" in text
    assert "uv run zyfangji-retrieval import-excel" in text
    assert "uv run zyfangji-retrieval index-rebuild" in text
    assert "docs/API.md" in text
    assert "docs/DEMO.md" in text
    assert "docs/DEPLOYMENT.md" in text
    assert "检索分数不是 medical confidence, diagnosis probability, or prescription certainty" in text
    assert "v1 不做聊天机器人，不做自动诊断，不做自动处方，不直连客户 MySQL 同步，也不提供后台管理系统" in text


def test_api_docs_cover_http_cli_and_java_examples() -> None:
    text = _read("docs/API.md")
    assert "# API and Java Integration Guide" in text
    assert "## HTTP Surface" in text
    assert "## OpenAPI" in text
    assert "## Operator Import and Indexing Workflow" in text
    assert "## POST /api/search" in text
    assert "## GET /status" in text
    assert "## GET /health/live" in text
    assert "## GET /health/ready" in text
    assert "## Error Envelope" in text
    assert "## Java 11 HttpClient Examples" in text
    assert "## curl Examples" in text
    assert "## Score and Medical Safety Semantics" in text
    assert "There is no HTTP import or rebuild endpoint in v1; import and rebuild are CLI-only operator workflows." in text
    assert "HttpClient.newHttpClient()" in text
    assert 'HttpRequest.newBuilder(URI.create(baseUrl + "/api/search"))' in text
    assert "main_symptom" in text
    assert "score_semantics" in text
    assert "SearchErrorEnvelope" in text


def test_demo_smoke_script_offline_json_output() -> None:
    result = subprocess.run(
        [
            "uv",
            "run",
            "python",
            "scripts/demo_smoke.py",
            "--queries",
            "tests/fixtures/smoke_queries.json",
            "--mode",
            "offline",
            "--limit",
            "2",
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "UV_PROJECT_ENVIRONMENT": "/tmp/zyfangji-retrieval-venv"},
    )
    payload = json.loads(result.stdout)
    assert payload["mode"] == "offline"
    assert payload["query_count"] == 7
    assert payload["results"]
    assert "diagnosis" not in result.stdout
    assert "medical_advice" not in result.stdout
    assert "autonomous_prescription" not in result.stdout


def test_demo_guide_documents_offline_live_and_safety_boundaries() -> None:
    text = _read("docs/DEMO.md")
    assert "# Reviewer Demo Guide" in text
    assert "## Demo Modes" in text
    assert "## Offline Smoke Demo" in text
    assert "## Live API Demo" in text
    assert "## How to Read Results Safely" in text
    assert "Demo results are retrieval references for physician review, not diagnosis, medical advice, or autonomous prescription." in text
    assert "Scores are ranking/reference signals, not medical confidence." in text
    assert "scripts/demo_smoke.py --mode live" in text
    assert "docs/DEMO.md" in _read("README.md")


def test_env_example_covers_all_app_settings() -> None:
    text = _read(".env.example")
    for field_name in AppSettings.model_fields:
        env_name = f"ZYFANGJI_{field_name.upper()}"
        assert env_name in text


def test_deployment_docs_cover_config_docker_privacy_and_scope() -> None:
    text = _read("docs/DEPLOYMENT.md")
    assert "# Deployment and Operations Runbook" in text
    assert "## Runtime Components" in text
    assert "## Environment Variables" in text
    assert "## Local uv Run" in text
    assert "## Docker Compose Run" in text
    assert "## Provider and Reranker Configuration" in text
    assert "## Import and Rebuild Workflow" in text
    assert "## Health and Status Checks" in text
    assert "## Smoke, Latency, and Manual UAT" in text
    assert "## Privacy-Conscious Logging" in text
    assert "## Out of Scope for v1" in text
    assert "## Troubleshooting" in text
    assert "cp .env.example .env" in text
    assert "docker compose up --build" in text
    assert "uv run zyfangji-retrieval import-excel" in text
    assert "uv run zyfangji-retrieval index-rebuild" in text
    assert "BGE-M3" in text
    assert "BGE-Reranker-v2-m3" in text
    assert "Do not log raw patient presentation text, provider API keys, or full provider error bodies." in text
    assert "Local Excel / local structured files are the v1 data source." in text
    assert "No customer MySQL sync, admin console, chat UI, symptom NER, autonomous diagnosis, or autonomous prescription in v1." in text
    readme = _read("README.md")
    assert "docs/DEPLOYMENT.md" in readme
    assert ".env.example" in readme
    assert "Dockerfile" in readme
    assert "docker-compose.yml" in readme
