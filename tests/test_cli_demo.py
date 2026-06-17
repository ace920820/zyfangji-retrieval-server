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
    assert "article=第35条" in result.output
    assert "row=1" in result.output
    assert "signals: bm25=" in result.output
    assert "vector=" in result.output
    assert "fused=" in result.output
    assert "rerank=" in result.output
    assert "主症: 头痛" in result.output
    assert "复合症: 头痛 发热 恶风 无汗" in result.output
    assert "舌象: 舌淡苔白" in result.output
    assert "脉象: 脉浮紧" in result.output
    assert "证型: 太阳伤寒证" in result.output
    assert "禁忌: 阴虚者慎用" in result.output
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


def test_demo_interactive_accepts_one_query_then_quits() -> None:
    result = runner.invoke(
        app,
        ["demo", "interactive", "--topk", "2"],
        input="头痛\n发热，恶风\n舌淡苔白\n脉浮紧\n太阳伤寒证\nq\n",
    )

    assert result.exit_code == 0
    assert "中医方剂检索 CLI" in result.output
    assert "结果仅作为检索参考" in result.output
    assert "麻黄汤" in result.output
    assert "signals: bm25=" in result.output
    assert "主症: 头痛" in result.output
    assert "舌象: 舌淡苔白" in result.output
    assert "桂枝汤" in result.output
    assert "已退出。" in result.output


def test_demo_interactive_rejects_empty_presentation_and_continues() -> None:
    result = runner.invoke(
        app,
        ["demo", "interactive"],
        input="\n\n\n\n\nq\n",
    )

    assert result.exit_code == 0
    assert "输入无效:" in result.output
    assert "已退出。" in result.output
