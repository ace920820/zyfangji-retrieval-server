# Pitfalls Research

**Domain:** Medical-adjacent TCM formula retrieval / RAG-style semantic search demo
**Researched:** 2026-06-14
**Confidence:** HIGH for project-specific data pitfalls; MEDIUM for ecosystem practices because implementation stack is not finalized.

## Critical Pitfalls

### Pitfall 1: Treating Excel `编码` as a Stable Business Identifier

**What goes wrong:**
Search results return rows that cannot reliably reconnect to the business formula library. The demo may show a matching formula name, but the Java backend cannot safely map it to prescription details because the row identity, formula identity, and business formula code are mixed together.

**Why it happens:**
The sample spreadsheet looks structured, so it is tempting to pass through `编码` directly. A direct inspection of the current Excel file found 1,322 nonempty rows but 1,290 blank `编码` cells and only 12 unique nonblank `编码` values. That column is not sufficient as a stable row key or formula key.

**How to avoid:**
Create three separate identifiers during the data-contract phase:

- `entry_id`: deterministic internal ID for each normalized knowledge entry, generated from source book + source row + normalized clause index.
- `source_ref`: human-readable provenance, such as book name, sheet name, row number, and original article number.
- `formula_code`: business-system formula identifier, resolved through an explicit mapping table maintained by the customer/backend team.

Reject imports that lack either a recoverable `entry_id` or a declared unresolved formula mapping status. Return unresolved formulas as `formula_code: null` with `formula_mapping_status: "unmapped"` rather than inventing codes.

**Warning signs:**
- API examples use formula name as the only lookup key.
- Re-importing the same Excel file changes result IDs.
- Duplicate formula names point to different business records without an explicit mapping rule.
- Deleting or updating one row requires guessing by text content.

**Phase to address:**
Phase 1: Data contract and ingestion normalization. This must be solved before retrieval scoring or API documentation, because downstream APIs depend on stable IDs.

---

### Pitfall 2: Failing to Split Multi-Formula / Multi-Syndrome Rows

**What goes wrong:**
One retrieved row may contain several syndromes, treatment paths, and formulas. The UI then displays a single high-ranked result that appears to recommend all listed formulas together, or the backend chooses the wrong formula code from a compound cell.

**Why it happens:**
The source data often encodes clinical branching inside one row. In the inspected sample, roughly 485 `推荐方剂` cells contain separator or parenthetical patterns suggesting multiple formulas, variants, herbs, stages, or conditional branches. Examples include separate formulas for 阳明腑实证 vs 表邪郁闭, or stage-based combinations such as 初期 / 热盛伤津 / 热结腑实.

**How to avoid:**
Normalize rows into searchable "candidate entries" before indexing:

- Keep the original row intact for display and audit.
- Split candidate entries by syndrome/stage/formula branch where the text clearly indicates separate options.
- Store `branch_label`, `branch_condition`, `formula_name`, `formula_variant`, and `original_formula_text`.
- If automatic parsing is ambiguous, mark `split_status: "needs_review"` and keep the unsplit original out of production recommendations until reviewed.
- Add import reports that count unsplit multi-formula rows.

**Warning signs:**
- Top result contains numbered formula lists but the API returns only one `formula_code`.
- Search snippets include "或", "可选用", "类", "加减", "初期", "恢复期", or multiple semicolon-separated formulas with no branch metadata.
- QA cannot answer "why this exact formula, not the neighboring formula in the same cell?"

**Phase to address:**
Phase 1: Data contract and ingestion normalization. Phase 2 should not tune retrieval quality until multi-formula rows are represented honestly.

---

### Pitfall 3: Interpreting Similarity Scores as Medical Confidence

**What goes wrong:**
A score such as 0.86, 86%, or "匹配度 90%" is interpreted by doctors, customers, or sales demos as a probability that the formula is medically correct. This creates misleading clinical framing and makes small score differences look more meaningful than they are.

**Why it happens:**
Vector similarity, keyword relevance, and reranker scores are ranking signals, not calibrated medical probabilities. Retrieval vendors document score behavior as algorithm-specific ranking output, and the project conversation already noted that semantic scores may cluster tightly: a good result might score 85 while a weak one scores 78.

**How to avoid:**
Define score semantics in the API and UI contract:

- Use `rank` as the primary display signal.
- Return raw retrieval diagnostics only under names like `retrieval_score`, `keyword_score`, `vector_score`, and `rerank_score`.
- Avoid percent labels unless scores are explicitly calibrated for this dataset.
- Add a user-facing label such as "检索排序参考" rather than "医学置信度".
- Include matched fields and source evidence so the doctor can judge the result.
- Set acceptance tests that verify score wording in API docs and demo UI.

**Warning signs:**
- API docs call scores "准确率", "可信度", "诊断概率", or "治愈概率".
- Demo UI adds percent signs to raw similarity values.
- Product discussions compare score thresholds as if they were clinical cutoffs.

**Phase to address:**
Phase 3: Retrieval API and scoring contract. Safety wording should be verified again in Phase 5 demo hardening.

---

### Pitfall 4: Building Pure Vector Search and Missing Exact TCM Terms

**What goes wrong:**
The system retrieves semantically plausible but textually wrong entries, especially for formula names, pulse/tongue terms, classical symptom phrases, article numbers, and aliases. Doctors lose trust because exact terms they entered do not surface expected records.

**Why it happens:**
Semantic embeddings are useful for fuzzy symptom matching, but this domain also depends on exact terminology: 方剂名, 条文号, 脉象, 舌诊, 同症异名, 证型, and classical phrases. Current search platforms commonly support hybrid retrieval because keyword ranking and vector ranking solve different parts of the problem.

**How to avoid:**
Use hybrid retrieval from the first retrieval phase:

- BM25/keyword index for exact names, aliases, article numbers, and required terms.
- Dense vector index for fuzzy symptom and description matching.
- Optional reranker after candidate generation.
- Field weighting: symptoms and aliases should influence retrieval differently from display-only fields such as human-model annotations.
- Query analyzer for Chinese text, plus a curated TCM synonym dictionary from `同症异名`.

Add a regression test set where exact formula/symptom queries must include expected entries in topK.

**Warning signs:**
- Searching an exact formula or article number does not return its own row.
- Adding a rare but decisive term fails to change ranking.
- Results look semantically adjacent but ignore tongue/pulse constraints.
- Engineers tune embedding prompts instead of checking keyword recall.

**Phase to address:**
Phase 2: Retrieval baseline. Hybrid search should be part of the first quality benchmark, not a later optimization.

---

### Pitfall 5: Indexing Display Fields as If They Were Clinical Evidence

**What goes wrong:**
Results are ranked by verbose explanatory or UI-oriented text instead of clinically meaningful retrieval fields. Human-model display annotations, long explanatory passages, and Western medicine notes can drown out concise symptoms, tongue, pulse, syndrome, and treatment fields.

**Why it happens:**
The Excel file has rich 22-column rows, and the easiest implementation is to concatenate all columns into one embedding string. That creates a noisy document where repeated explanatory text has equal or greater influence than the fields doctors are actually querying.

**How to avoid:**
Create separate field groups:

- Retrieval core: `主病主症`, `复合症`, `细分主症`, `同症异名`, `舌诊`, `脉象`, `中医证型`, `中医病名`, `治法`.
- Evidence/display: source article number, original text, pathology, contraindications, efficacy notes.
- Integration fields: `entry_id`, `formula_code`, formula mapping status.
- Excluded or low-weight fields: human-model drawing instructions and long UI annotations unless explicitly needed.

Store the constructed retrieval text per entry and expose it in admin/debug endpoints so QA can see what was indexed.

**Warning signs:**
- Retrieval text is not inspectable after import.
- Top matches share generic display text but not the user's symptoms.
- A small change in verbose fields changes rankings more than a change in symptoms.
- Engineers cannot explain which fields contributed to a result.

**Phase to address:**
Phase 1: Data normalization and Phase 2: Retrieval baseline. The roadmap should require an indexed-field manifest before quality tuning.

---

### Pitfall 6: Returning Formula Recommendations Without Safety Boundaries

**What goes wrong:**
The service looks like it is prescribing treatment rather than retrieving classical references for doctor review. This is especially risky when results include contraindications, Western-priority notes, urgent symptoms, toxic/strong herbs, pregnancy-related concerns, or formulas from classical contexts that need professional interpretation.

**Why it happens:**
The user flow starts from patient symptoms and returns formulas, so even without generation it can be perceived as clinical decision support. Health AI guidance emphasizes transparency, human oversight, risk management, and clear role boundaries. The project has already scoped final judgment to doctors, but that boundary must appear in API fields, docs, and demo wording.

**How to avoid:**
Add safety framing as product behavior, not legal boilerplate:

- API response includes `intended_use: "classical_reference_retrieval"` or equivalent documentation.
- Always return source evidence, contraindications, and `中西先后` / Western-priority fields when available.
- UI labels use "参考条目", "典籍依据", and "医生复核" rather than "系统诊断" or "自动处方".
- Add a required "not for patient self-diagnosis" note in public demo pages.
- Add a safety review checklist for formulas with explicit禁忌, emergency/Western-priority notes, pregnancy/children wording, or toxic/strong herb references.

**Warning signs:**
- Demo copy says "推荐处方" without "参考" or "医生复核".
- The API omits contraindication fields because the frontend does not currently display them.
- Search results hide source article/evidence behind a secondary interaction.
- Customer asks to expose the demo directly to patients without clinician mediation.

**Phase to address:**
Phase 3: API contract and Phase 4: safety/documentation. Re-verify in Phase 5 demo hardening before external access.

---

### Pitfall 7: Demo Reliability Depends on Manual Rebuilds and Hidden Model/API State

**What goes wrong:**
The two-to-three-week demo works once on the developer machine but fails during customer review because embeddings were not rebuilt, model keys expired, data changed without index status updates, or the service silently serves stale vectors.

**Why it happens:**
Retrieval demos often treat ingestion, vectorization, reranking, and serving as one script. The project explicitly needs management APIs for import, rebuild, status, update/delete, and backend integration, so hidden index state will quickly become a support problem.

**How to avoid:**
Build minimal operational controls early:

- `POST /admin/import` or equivalent import trigger with job ID.
- `POST /admin/rebuild-index` for full rebuild.
- `GET /admin/index-status` showing data version, row count, entry count, embedding model, last build time, failed rows, and formula mapping counts.
- Idempotent update/delete by `entry_id`.
- Startup checks for required model API keys and collection/index existence.
- Demo seed dataset and smoke queries committed as reproducible fixtures.

**Warning signs:**
- There is no way to tell which Excel version the index represents.
- Import logs exist only in terminal output.
- Deleting a row from business data leaves it retrievable.
- A model provider failure returns empty results with HTTP 200.

**Phase to address:**
Phase 4: Admin APIs and index operations. Phase 5 should include deployment smoke tests and rollback/rebuild instructions.

---

### Pitfall 8: Planning for 200 Books Without a Source Schema Strategy

**What goes wrong:**
The first book works, but every additional classic requires custom parsing and ad hoc fields. Search quality becomes inconsistent because fields with similar meaning have different names, missing values, or incompatible levels of granularity.

**Why it happens:**
The conversation mentions up to 200 manually organized books, but the field consistency is not confirmed. If the roadmap hardcodes only the current 22-column `伤寒论` shape, expansion becomes a rewrite.

**How to avoid:**
Define a canonical knowledge-entry schema now, while only implementing one source adapter:

- Canonical required fields: source, row identity, symptoms, aliases, tongue, pulse, syndrome, disease, cause/pathology, treatment, formula branches, contraindications, evidence.
- Source adapter per book/table that maps raw columns into canonical fields.
- Import validation report showing missing required/recommended fields per source.
- Versioned mapping config, not hardcoded column positions.

Do not build auto-extraction from raw books in Phase 1; only design the adapter boundary so future structured sources can be added without changing retrieval logic.

**Warning signs:**
- Column names are referenced directly throughout retrieval code.
- Adding another Excel requires editing search API response models.
- Test fixtures contain only one book and no missing-field cases.
- Stakeholders cannot answer whether future books have the same fields.

**Phase to address:**
Phase 1: Data contract. Phase 6: multi-source expansion should be explicitly gated on receiving at least two representative non-`伤寒论` files.

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Use row number as public ID | Fast API examples | IDs change after sorting, filtering, or re-import | Only as internal `source_row` provenance, never as public `entry_id` |
| Concatenate all columns into one embedding string | Quick retrieval prototype | Noisy rankings and no explainability | Acceptable for a one-day spike, not for roadmap Phase 2 acceptance |
| Return only formula name | Simple backend integration | Ambiguous mapping and duplicate-name errors | Never acceptable for integration; include mapping status even if code is null |
| Treat multi-formula cells as display text only | Avoids parser work | Wrong formula-code selection and unsafe UI wording | Only if such rows are excluded or clearly marked `needs_review` |
| Hide raw retrieval diagnostics | Cleaner API | Impossible to debug poor ranking | Only for public endpoint after admin/debug endpoint exists |
| Manual rebuild by shell command | Fast demo setup | Stale or unreproducible demo | Acceptable before customer demo only if documented and smoke-tested |

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Java backend formula library | Matching by formula name text | Match by explicit `formula_code`; return `formula_mapping_status` and original name |
| Business MySQL / table source | Query live database for every search | Use import/rebuild/update flows into a search index; report source data version |
| Embedding provider | No startup validation or provider fallback behavior | Check API key/model availability at boot and fail admin jobs loudly |
| Vector database/search engine | Upsert without deterministic IDs | Upsert by stable `entry_id`; delete/update by same ID; record index version |
| Frontend demo | Display raw score as percent confidence | Display rank and evidence; label scores as retrieval diagnostics or hide them |
| Public model/reranker | Sending patient-identifying free text unnecessarily | Minimize and redact patient identifiers before model calls; log only safe query metadata |

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Re-embedding all rows on every small edit | Slow admin operations, provider cost spikes | Support full rebuild plus deterministic per-entry upsert for small updates | Once data grows from 1 book to dozens of books |
| No retrieval evaluation set | "Looks okay" demos but regressions after tuning | Maintain fixed smoke queries and expected topK/evidence checks | Immediately after changing chunking, weighting, or model |
| Overlarge retrieval documents | Similar rows blur together; scores cluster | Split by candidate branch and field-weight retrieval text | Already visible in current multi-branch rows |
| Synchronous rebuild in request path | API timeouts during import | Background job with status endpoint | Any customer-facing environment |
| No cache/version boundary | Users get mixed old/new results | Atomic index swap or index version field in responses | Any rebuild during active demo |

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Logging raw patient symptom narratives with identifiers | Health-adjacent privacy exposure and avoidable sensitive-data retention | Redact identifiers, set log retention, and log query IDs plus aggregate diagnostics |
| Exposing admin rebuild/delete endpoints publicly | Demo data loss or poisoned index | Put admin APIs behind authentication, network allowlist, or separate internal route group |
| Sending full patient records to external embedding/rerank providers | Unnecessary third-party data transfer | Send only retrieval text needed for matching; remove name, phone, ID, address, and visit identifiers |
| Letting formula/source text be updated without audit trail | Hard to investigate wrong recommendations | Store import version, source checksum, actor, timestamp, and failed-row report |
| Treating medical-adjacent output as ordinary search copy | User relies on output as diagnosis/prescription | Enforce doctor-review wording and return evidence/contraindications by default |

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Showing "90% match" as the dominant visual | Doctors overtrust or argue with uncalibrated numbers | Show rank, matched fields, evidence, and a secondary retrieval score if needed |
| Hiding original text and contraindications | Result feels ungrounded and unsafe | Put source article/evidence and禁忌 fields in the first result payload |
| Mixing multiple formulas in one result card | Doctor cannot tell which formula corresponds to which syndrome branch | Display branch labels and one formula candidate per branch |
| Returning empty results for narrow queries | Demo appears broken | Return topK plus "low evidence / broaden query" status and matched-field diagnostics |
| No indication of stale index | Customer tests updated data and thinks search is wrong | Show index data version and last rebuild time in admin/status view |

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **Data import:** Often missing deterministic `entry_id` generation. Verify same Excel import twice produces identical IDs.
- [ ] **Formula mapping:** Often missing unresolved-code handling. Verify unmapped formulas do not get fake codes.
- [ ] **Multi-formula rows:** Often missing branch normalization. Verify rows with numbered/semicolon formula lists become separate candidates or `needs_review`.
- [ ] **Retrieval quality:** Often missing exact-term regression tests. Verify exact formula, symptom, tongue, pulse, and article-number queries.
- [ ] **Score display:** Often missing wording review. Verify no docs/UI label raw scores as medical confidence.
- [ ] **Evidence payload:** Often missing contraindications and source references. Verify every result carries source/evidence fields when present.
- [ ] **Admin operations:** Often missing status. Verify index status includes data version, entry count, model, failures, and last build time.
- [ ] **Demo deployment:** Often missing provider-key and stale-index failure modes. Verify smoke tests run after deploy and after rebuild.
- [ ] **Privacy:** Often missing log minimization. Verify logs do not contain patient names, phone numbers, IDs, or full raw narratives unless explicitly approved.

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Unstable IDs already exposed | HIGH | Freeze current API, create migration table from old IDs to new `entry_id`, re-index, and publish versioned API docs |
| Multi-formula rows indexed as one result | MEDIUM | Export affected rows, split/mark branches, rebuild index, and rerun smoke queries against affected symptoms |
| Scores marketed as confidence | MEDIUM | Update API docs/UI labels, remove percent formatting, add release note explaining rank semantics |
| Pure vector search misses exact terms | MEDIUM | Add keyword index and hybrid fusion, create exact-term regression suite, retune field weights |
| Demo serving stale vectors | LOW to MEDIUM | Expose index status, rebuild from source, verify row/entry counts, and add deploy smoke check |
| Patient data logged externally | HIGH | Rotate/delete logs where possible, document incident, add redaction, and verify provider data-handling settings before reopening demo |

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Unstable data IDs | Phase 1: Data contract and ingestion normalization | Same import produces identical `entry_id`; blank `编码` does not block internal identity |
| Multi-formula rows | Phase 1: Data contract and ingestion normalization | Import report counts split, unsplit, and `needs_review` formula branches |
| Noisy retrieval fields | Phase 1 and Phase 2: Retrieval baseline | Indexed text is inspectable; field manifest exists; smoke queries pass |
| Pure vector search | Phase 2: Hybrid retrieval baseline | Exact formula/article/symptom queries return expected topK entries |
| Score misinterpretation | Phase 3: API/scoring contract | API docs define scores as ranking diagnostics; UI has no percent-confidence labels |
| Safety boundary drift | Phase 3 and Phase 4: Safety documentation | Responses include evidence/禁忌/中西先后; docs state doctor-review intended use |
| Fragile admin/index operations | Phase 4: Admin APIs and index operations | Status endpoint reports version/count/model/failures; rebuild and delete smoke tests pass |
| Unreliable external demo | Phase 5: Demo deployment hardening | Fresh deploy runs smoke queries; provider-key failures are visible; index version matches source |
| 200-book expansion rewrite | Phase 6: Multi-source expansion | New source adapter can map a second book without changing retrieval API |

## Sources

- Project context: `.planning/PROJECT.md` and `data/任如亮项目对话.txt` (HIGH confidence for scope, stakeholder intent, score caveat, and demo constraints).
- Local data inspection of `data/伤寒论原文 病症信息对应表（内容齐全 1 稿）.xlsx` on 2026-06-14: 1,322 nonempty rows, 1,290 blank `编码` cells, roughly 485 multi-formula-like `推荐方剂` cells (HIGH confidence for current sample shape).
- Microsoft Azure AI Search documentation on hybrid search and relevance scoring: https://learn.microsoft.com/azure/search/hybrid-search-overview and https://learn.microsoft.com/azure/search/index-similarity-and-scoring (HIGH confidence for hybrid search and score semantics as search-engine behavior).
- Qdrant documentation on hybrid search / sparse plus dense retrieval: https://qdrant.tech/documentation/concepts/hybrid-queries/ (MEDIUM confidence for ecosystem pattern; exact implementation stack not chosen).
- NIST AI Risk Management Framework 1.0: https://www.nist.gov/itl/ai-risk-management-framework (HIGH confidence for AI risk-management framing).
- WHO guidance on ethics and governance of artificial intelligence for health: https://www.who.int/publications/i/item/9789240029200 and large multi-modal models for health: https://www.who.int/publications/i/item/9789240084759 (HIGH confidence for health-AI transparency, human oversight, and safety framing).
- China Personal Information Protection Law translation and official policy references: https://digichina.stanford.edu/work/translation-personal-information-protection-law-of-the-peoples-republic-of-china-effective-nov-1-2021/ and https://www.gov.cn/ (MEDIUM confidence for privacy framing; legal review is still required before production).

---
*Pitfalls research for: medical-adjacent TCM formula retrieval*
*Researched: 2026-06-14*
