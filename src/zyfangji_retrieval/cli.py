import json
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import typer
from qdrant_client import QdrantClient

from zyfangji_retrieval.config import get_settings
from zyfangji_retrieval.demo_service import build_offline_demo_service
from zyfangji_retrieval.domain.models import KnowledgeEntry
from zyfangji_retrieval.domain.search_models import PatientSearchRequest
from zyfangji_retrieval.indexing.bm25_store import BM25IndexStore
from zyfangji_retrieval.indexing.embeddings import DeterministicEmbeddingProvider
from zyfangji_retrieval.indexing.lifecycle import IndexLifecycleService
from zyfangji_retrieval.indexing.qdrant_store import QdrantVectorIndex
from zyfangji_retrieval.indexing.status import IndexStatusService
from zyfangji_retrieval.indexing.validation import validate_persisted_counts
from zyfangji_retrieval.ingestion.excel_reader import read_shanghanlun_workbook
from zyfangji_retrieval.ingestion.importer import (
    import_workbook_to_metadata,
    load_entries_for_rebuild,
)
from zyfangji_retrieval.ingestion.mapper import map_row_to_entry, validate_source_row
from zyfangji_retrieval.ingestion.reports import RowIssue, build_import_report
from zyfangji_retrieval.persistence.jsonl import export_entries_jsonl
from zyfangji_retrieval.persistence.index_state import SQLiteIndexStateStore
from zyfangji_retrieval.persistence.sqlite import SQLiteMetadataStore


app = typer.Typer(no_args_is_help=True)
demo_app = typer.Typer(help="User-facing demo search commands.")


class LocalQdrantVectorIndex(QdrantVectorIndex):
    def __init__(self, collection_prefix: str, alias_name: str, vector_size: int) -> None:
        super().__init__(
            client=QdrantClient(":memory:"),
            collection_prefix=collection_prefix,
            alias_name=alias_name,
            vector_size=vector_size,
        )

    def activate_alias(self, index_version: str) -> str:
        self.collection_name(index_version)
        return self.alias_name


def _map_workbook(path: Path) -> tuple[list[KnowledgeEntry], list[RowIssue]]:
    workbook_rows = read_shanghanlun_workbook(path)
    entries: list[KnowledgeEntry] = []
    issues: list[RowIssue] = []
    for row in workbook_rows.rows:
        row_issues = validate_source_row(row)
        issues.extend(row_issues)
        if any(issue.severity == "error" for issue in row_issues):
            continue
        entry = map_row_to_entry(row)
        if entry is not None:
            entries.append(entry)
    return entries, issues


@app.command("inspect-workbook")
def inspect_workbook(path: Path) -> None:
    workbook_rows = read_shanghanlun_workbook(path)
    typer.echo(f"Source file: {workbook_rows.source_file}")
    typer.echo(f"Sheet name: {workbook_rows.source_sheet}")
    typer.echo(f"Header count: {len(workbook_rows.headers)}")
    typer.echo(f"Row count: {len(workbook_rows.rows)}")
    typer.echo(f"Blank rows: {workbook_rows.blank_rows}")


@app.command("import-excel")
def import_excel(
    path: Path,
    dry_run: bool = typer.Option(False, "--dry-run/--no-dry-run"),
    db_path: Path = typer.Option(Path("var/metadata/knowledge.db"), "--db-path"),
    jsonl_export: Path | None = typer.Option(None, "--jsonl-export"),
) -> None:
    if dry_run:
        workbook_rows = read_shanghanlun_workbook(path)
        entries, issues = _map_workbook(path)
        report = build_import_report(
            workbook_rows,
            entries,
            issues,
            index_version="dry-run",
        )
    else:
        report = import_workbook_to_metadata(path, db_path)
        if jsonl_export is not None:
            entries = load_entries_for_rebuild(db_path, index_version=report.index_version)
            export_entries_jsonl(entries, jsonl_export)
    typer.echo(report.model_dump_json(indent=2, ensure_ascii=False))


@app.command("rebuild-source")
def rebuild_source(
    db_path: Path = typer.Option(Path("var/metadata/knowledge.db"), "--db-path"),
    index_version: str | None = typer.Option(None, "--index-version"),
) -> None:
    entries = load_entries_for_rebuild(db_path, index_version=index_version)
    latest_batch = SQLiteMetadataStore(db_path).latest_batch()
    resolved_index_version = index_version
    if resolved_index_version is None and latest_batch is not None:
        resolved_index_version = str(latest_batch["index_version"])
    source = "local_metadata"
    typer.echo(
        json.dumps(
            {
                "entry_count": len(entries),
                "index_version": resolved_index_version,
                "source": source,
            },
            ensure_ascii=False,
        )
    )


def _latest_metadata_version(db_path: Path, metadata_version: str | None) -> str:
    if metadata_version is not None:
        return metadata_version
    latest_batch = SQLiteMetadataStore(db_path).latest_batch()
    if latest_batch is None:
        raise typer.BadParameter("metadata database has no import batch")
    return str(latest_batch["index_version"])


@app.command("index-rebuild")
def index_rebuild(
    db_path: Path = typer.Option(Path("var/metadata/knowledge.db"), "--db-path"),
    metadata_version: str | None = typer.Option(None, "--metadata-version"),
    bm25_index_root: Path = typer.Option(Path("var/indexes/bm25"), "--bm25-index-root"),
    activate: bool = typer.Option(True, "--activate/--no-activate"),
) -> None:
    settings = get_settings()
    provider = DeterministicEmbeddingProvider(vector_size=settings.embedding_vector_size)
    qdrant_index = LocalQdrantVectorIndex(
        collection_prefix=settings.qdrant_collection_prefix,
        alias_name=settings.qdrant_alias,
        vector_size=provider.vector_size,
    )
    state_store = SQLiteIndexStateStore(db_path)
    service = IndexLifecycleService(
        db_path=db_path,
        metadata_version=_latest_metadata_version(db_path, metadata_version),
        embedding_provider=provider,
        qdrant_index=qdrant_index,
        bm25_store=BM25IndexStore(bm25_index_root),
        index_state_store=state_store,
    )
    record = service.rebuild(activate=activate)
    typer.echo(record.model_dump_json(indent=2, ensure_ascii=False))


@app.command("index-validate")
def index_validate(
    index_version: str = typer.Option(..., "--index-version"),
    db_path: Path = typer.Option(Path("var/metadata/knowledge.db"), "--db-path"),
    bm25_index_root: Path = typer.Option(Path("var/indexes/bm25"), "--bm25-index-root"),
) -> None:
    state_store = SQLiteIndexStateStore(db_path)
    build = state_store.get_build(index_version)
    if build is None:
        raise typer.BadParameter(f"index build does not exist: {index_version}")
    bm25_result = BM25IndexStore(bm25_index_root).validate(
        index_version,
        expected_count=build.entry_count,
    )
    validation = validate_persisted_counts(
        index_version=index_version,
        expected_count=build.entry_count,
        vector_count=build.vector_count,
        bm25_result=bm25_result,
        qdrant_collection=build.qdrant_collection,
        qdrant_alias=build.qdrant_alias,
    )
    typer.echo(validation.model_dump_json(indent=2, ensure_ascii=False))


@app.command("index-status")
def index_status(
    db_path: Path = typer.Option(Path("var/metadata/knowledge.db"), "--db-path"),
) -> None:
    settings = get_settings()
    state_store = SQLiteIndexStateStore(db_path)
    status = IndexStatusService(state_store, settings).status()
    typer.echo(status.model_dump_json(indent=2, ensure_ascii=False))


@demo_app.command("search")
def demo_search(
    main_symptom: str = typer.Option(..., "--main-symptom"),
    symptom: list[str] = typer.Option([], "--symptom"),
    tongue: str | None = typer.Option(None, "--tongue"),
    pulse: str | None = typer.Option(None, "--pulse"),
    syndrome: str | None = typer.Option(None, "--syndrome"),
    topk: int = typer.Option(5, "--topk", min=1, max=50),
    mode: str = typer.Option("offline", "--mode", case_sensitive=False),
    base_url: str | None = typer.Option(None, "--base-url"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    request = PatientSearchRequest(
        main_symptom=main_symptom,
        symptoms=symptom,
        tongue=tongue,
        pulse=pulse,
        syndrome=syndrome,
        topk=topk,
    )
    payload = _run_demo_search(request, mode=mode, base_url=base_url)
    _render_demo_search(payload, json_output=json_output, limit=topk)


@demo_app.command("preset")
def demo_preset(
    name: str = typer.Option("headache", "--name"),
    mode: str = typer.Option("offline", "--mode", case_sensitive=False),
    base_url: str | None = typer.Option(None, "--base-url"),
    limit: int = typer.Option(3, "--limit", min=1),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    request = _preset_request(name)
    payload = _run_demo_search(request, mode=mode, base_url=base_url)
    _render_demo_search(payload, json_output=json_output, limit=limit)


@demo_app.command("interactive")
def demo_interactive(
    mode: str = typer.Option("offline", "--mode", case_sensitive=False),
    base_url: str | None = typer.Option(None, "--base-url"),
    topk: int = typer.Option(5, "--topk", min=1, max=50),
) -> None:
    typer.echo("中医方剂检索 CLI")
    typer.echo("每轮输入患者表现；可直接回车跳过字段。输入 q 退出。")
    typer.echo("结果仅作为检索参考，不是诊断、医疗建议或自动处方。")
    while True:
        main_symptom = _prompt_optional("主症", allow_empty=True)
        if main_symptom is None:
            break
        symptoms_text = _prompt_optional("其他症状，多个用逗号分隔", allow_empty=True)
        if symptoms_text is None:
            break
        tongue = _prompt_optional("舌象", allow_empty=True)
        if tongue is None:
            break
        pulse = _prompt_optional("脉象", allow_empty=True)
        if pulse is None:
            break
        syndrome = _prompt_optional("证型", allow_empty=True)
        if syndrome is None:
            break

        if not any([main_symptom, symptoms_text, tongue, pulse, syndrome]):
            typer.echo("输入无效: 至少填写一项症状、舌象、脉象或证型。")
            continue

        symptoms = _split_symptoms(symptoms_text)
        try:
            request = PatientSearchRequest(
                main_symptom=main_symptom,
                symptoms=symptoms,
                tongue=tongue,
                pulse=pulse,
                syndrome=syndrome,
                topk=topk,
            )
        except ValueError as exc:
            typer.echo(f"输入无效: {exc}")
            continue

        payload = _run_demo_search(request, mode=mode, base_url=base_url)
        _render_demo_search(payload, json_output=False, limit=topk)
        typer.echo("")
    typer.echo("已退出。")


app.add_typer(demo_app, name="demo")


def _run_demo_search(
    request: PatientSearchRequest,
    *,
    mode: str,
    base_url: str | None,
) -> dict[str, Any]:
    if mode == "live":
        if not base_url:
            raise typer.BadParameter("--base-url is required when --mode live")
        return _post_live_search(base_url, request)
    if mode != "offline":
        raise typer.BadParameter("--mode must be offline or live")
    return build_offline_demo_service().search(request).model_dump(mode="json")


def _post_live_search(base_url: str, request: PatientSearchRequest) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/api/search"
    http_request = Request(
        url,
        data=json.dumps(request.model_dump(mode="json"), ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urlopen(http_request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise typer.BadParameter(f"live search failed with HTTP {exc.code}: {body}") from exc
    except URLError as exc:
        raise typer.BadParameter(f"live search failed: {exc.reason}") from exc


def _render_demo_search(payload: dict[str, Any], *, json_output: bool, limit: int) -> None:
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    typer.echo(f"query: {payload.get('query', {}).get('text', '')}")
    typer.echo(f"warnings: {', '.join(item.get('code', '') for item in payload.get('warnings', [])) or 'none'}")
    typer.echo(f"score semantics: {payload.get('score_semantics', '')}")
    for result in payload.get("results", [])[:limit]:
        source = result.get("source", {})
        typer.echo(
            f"- {result.get('formula_raw', '')} | {source.get('article') or '-'} | "
            f"score={result.get('retrieval_score', '')}"
        )


def _preset_request(name: str) -> PatientSearchRequest:
    presets: dict[str, dict[str, object]] = {
        "headache": {
            "main_symptom": "头痛",
            "symptoms": ["发热", "恶风"],
            "tongue": "舌淡苔白",
            "pulse": "脉浮紧",
            "syndrome": "太阳伤寒证",
            "topk": 5,
        },
        "fever": {
            "main_symptom": "发热恶风",
            "symptoms": ["无汗"],
            "tongue": "舌淡",
            "pulse": "脉浮缓",
            "syndrome": "太阳中风证",
            "topk": 5,
        },
        "formula": {
            "main_symptom": "麻黄汤",
            "topk": 5,
        },
    }
    try:
        return PatientSearchRequest.model_validate(presets[name])
    except KeyError as exc:
        raise typer.BadParameter(f"unknown preset: {name}") from exc


def _prompt_optional(label: str, *, allow_empty: bool = False) -> str | None:
    value = typer.prompt(label, default="", show_default=False).strip()
    if value.lower() in {"q", "quit", "exit"}:
        return None
    if value:
        return value
    return "" if allow_empty else None


def _split_symptoms(value: str | None) -> list[str]:
    if not value:
        return []
    normalized = value.replace("，", ",").replace("、", ",")
    return [part.strip() for part in normalized.split(",") if part.strip()]


if __name__ == "__main__":
    app()
