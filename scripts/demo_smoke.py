from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from zyfangji_retrieval.demo_service import build_offline_demo_service
from zyfangji_retrieval.domain.search_models import PatientSearchRequest
from zyfangji_retrieval.search.service import SearchService


def main() -> int:
    args = _parse_args()
    cases = _load_cases(args.queries)
    requests = [PatientSearchRequest.model_validate(case["request"]) for case in cases]
    runner = _live_runner(args.base_url) if args.mode == "live" else _offline_runner()

    rows: list[dict[str, Any]] = []
    for case, request in zip(cases, requests, strict=True):
        payload = runner(request)
        results = payload.get("results", [])[: args.limit]
        row = {
            "id": case["id"],
            "category": case["category"],
            "query": payload.get("query", {}),
            "results": [
                {
                    "formula_raw": result.get("formula_raw"),
                    "source_article": result.get("evidence", {}).get("source_article"),
                    "pipeline_status": payload.get("metadata", {}).get("pipeline_status"),
                }
                for result in results
            ],
            "warnings": [warning.get("code") for warning in payload.get("warnings", [])],
            "score_semantics": "Retrieval scores are relative ranking/reference signals only.",
        }
        rows.append(row)

    if args.json:
        print(
            json.dumps(
                {
                    "mode": args.mode,
                    "query_count": len(requests),
                    "results": rows,
                    "score_semantics": "Retrieval scores are relative ranking/reference signals only.",
                },
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
    else:
        for row in rows:
            print(f"{row['id']} [{row['category']}]")
            print(f"  warnings: {', '.join(row['warnings']) or 'none'}")
            print(f"  score semantics: {row['score_semantics']}")
            for result in row["results"]:
                article = result["source_article"] or "-"
                print(f"  - {result['formula_raw']} | {article}")

    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reviewer smoke demo over offline fixture or live /api/search."
    )
    parser.add_argument(
        "--queries",
        type=Path,
        default=Path("tests/fixtures/smoke_queries.json"),
        help="Path to smoke query fixture JSON.",
    )
    parser.add_argument(
        "--mode",
        choices=("offline", "live"),
        default="offline",
        help="offline uses deterministic in-process demo behavior; live posts to --base-url /api/search.",
    )
    parser.add_argument("--base-url", help="Base URL for live mode, for example http://127.0.0.1:8000.")
    parser.add_argument("--limit", type=int, default=3, help="Max results to show per query.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON output.")
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be >= 1")
    if args.mode == "live" and not args.base_url:
        parser.error("--base-url is required when --mode live")
    return args


def _load_cases(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def _offline_runner() -> "_OfflineRunner":
    return _OfflineRunner(_offline_service())


def _live_runner(base_url: str | None) -> "_LiveRunner":
    if not base_url:
        raise ValueError("base_url is required")
    return _LiveRunner(base_url)


class _OfflineRunner:
    def __init__(self, service: SearchService) -> None:
        self.service = service

    def __call__(self, request: PatientSearchRequest) -> dict[str, Any]:
        return self.service.search(request).model_dump(mode="json")


class _LiveRunner:
    def __init__(self, base_url: str) -> None:
        self.url = f"{base_url.rstrip('/')}/api/search"

    def __call__(self, request: PatientSearchRequest) -> dict[str, Any]:
        payload = request.model_dump(mode="json")
        http_request = Request(
            self.url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urlopen(http_request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"live demo failed with HTTP {exc.code}: {body}") from exc
        except URLError as exc:
            raise RuntimeError(f"live demo failed: {exc.reason}") from exc


def _offline_service() -> SearchService:
    return build_offline_demo_service()


if __name__ == "__main__":
    raise SystemExit(main())
