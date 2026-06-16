# API and Java Integration Guide

## HTTP Surface

| Method | Path | Purpose |
|--------|------|---------|
| POST | /api/search | Submit structured patient presentation and receive ranked formula retrieval results. |
| GET | /status | Inspect active index readiness and model/provider metadata. |
| GET | /health/live | Check process liveness. |
| GET | /health/ready | Check active-index readiness for integration. |

There is no HTTP import or rebuild endpoint in v1; import and rebuild are CLI-only operator workflows.

## OpenAPI

OpenAPI is available at `/docs` and `/openapi.json` when the API is running.

## Operator Import and Indexing Workflow

```bash
uv run zyfangji-retrieval inspect-workbook "data/伤寒论原文 病症信息对应表（内容齐全 1 稿）.xlsx"
uv run zyfangji-retrieval import-excel "data/伤寒论原文 病症信息对应表（内容齐全 1 稿）.xlsx" --db-path var/metadata/knowledge.db
uv run zyfangji-retrieval rebuild-source --db-path var/metadata/knowledge.db
uv run zyfangji-retrieval index-rebuild --db-path var/metadata/knowledge.db --bm25-index-root var/indexes/bm25 --activate
uv run zyfangji-retrieval index-status --db-path var/metadata/knowledge.db
```

## POST /api/search

Request body:

```json
{
  "main_symptom": "头痛",
  "symptoms": ["发热", "恶风"],
  "tongue": "舌淡苔白",
  "pulse": "脉浮紧",
  "syndrome": "太阳伤寒证",
  "topk": 5
}
```

Response top-level fields:

- `query`
- `results`
- `warnings`
- `metadata`
- `score_semantics`

Each result includes `rank`, `retrieval_score`, `score_type`, `entry_id`, `source`, `formula_raw`, `formula_mentions`, `formula_code`, `formula_mapping_status`, `evidence`, and `signal_scores`.

## GET /status

Returns readiness, active version, indexed count, vector store, retrieval strategy, provider/model identifiers, reranker metadata, and last error.

## GET /health/live

Returns:

```json
{"status":"ok"}
```

## GET /health/ready

Returns active index readiness. If no active validated index exists, it returns HTTP 503 with status details.

## Error Envelope

SearchErrorEnvelope:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed.",
    "details": {}
  }
}
```

Known codes include `validation_error`, `index_not_ready`, `vector_store_unavailable`, `embedding_provider_unavailable`, `reranker_unavailable`, and `search_internal_error`.

## Java 11 HttpClient Examples

```java
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;

public class ZyfangjiSearchExample {
  public static void main(String[] args) throws Exception {
    String baseUrl = "http://127.0.0.1:8000";
    HttpClient client = HttpClient.newHttpClient();
    String body = """
      {
        "main_symptom": "头痛",
        "symptoms": ["发热", "恶风"],
        "tongue": "舌淡苔白",
        "pulse": "脉浮紧",
        "syndrome": "太阳伤寒证",
        "topk": 5
      }
      """;
    HttpRequest request = HttpRequest.newBuilder(URI.create(baseUrl + "/api/search"))
        .header("Content-Type", "application/json")
        .POST(HttpRequest.BodyPublishers.ofString(body))
        .build();
    HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
    System.out.println(response.statusCode());
    System.out.println(response.body());
  }
}
```

Status check:

```java
HttpRequest request = HttpRequest.newBuilder(URI.create(baseUrl + "/status")).GET().build();
```

## curl Examples

```bash
curl http://127.0.0.1:8000/status
curl http://127.0.0.1:8000/health/ready
curl -X POST http://127.0.0.1:8000/api/search \
  -H 'Content-Type: application/json' \
  -d '{"main_symptom":"头痛","symptoms":["发热","恶风"],"tongue":"舌淡苔白","pulse":"脉浮紧","syndrome":"太阳伤寒证","topk":5}'
```

## Score and Medical Safety Semantics

Retrieval scores are relative ranking/reference signals only, not medical confidence, diagnosis probability, or prescription certainty.

The retrieval service returns evidence and formula references for physician review. It does not produce autonomous diagnosis, medical advice, treatment plans, or autonomous prescriptions.
