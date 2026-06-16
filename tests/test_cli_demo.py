from __future__ import annotations

import json

from typer.testing import CliRunner

from zyfangji_retrieval.cli import app


runner = CliRunner()


def test_demo_preset_prints_readable_formula_results() -> None:
    result = runner.invoke(app, ["demo", "preset", "--name", "headache", "--limit", "2"])

    assert result.exit_code == 0
    assert "query:" in result.output
    assert "麻黄汤" in result.output
    assert "第35条" in result.output
    assert "score semantics:" in result.output
    assert "not medical confidence" in result.output


def test_demo_search_accepts_patient_presentation_fields() -> None:
    result = runner.invoke(
        app,
        [
            "demo",
            "search",
            "--main-symptom",
            "头痛",
            "--symptom",
            "发热",
            "--symptom",
            "恶风",
            "--tongue",
            "舌淡苔白",
            "--pulse",
            "脉浮紧",
            "--syndrome",
            "太阳伤寒证",
            "--topk",
            "2",
        ],
    )

    assert result.exit_code == 0
    assert "麻黄汤" in result.output
    assert "桂枝汤" in result.output
    assert "warnings: none" in result.output


def test_demo_search_json_output_matches_search_contract() -> None:
    result = runner.invoke(
        app,
        ["demo", "search", "--main-symptom", "麻黄汤", "--topk", "1", "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert set(payload) == {"query", "results", "warnings", "metadata", "score_semantics"}
    assert payload["results"][0]["formula_raw"] == "麻黄汤"
    assert payload["metadata"]["pipeline_status"] == "reranked"


def test_demo_preset_rejects_unknown_name() -> None:
    result = runner.invoke(app, ["demo", "preset", "--name", "missing"])

    assert result.exit_code != 0
    assert "unknown preset: missing" in result.output
