# 中医方剂检索系统

## What This Is

中医方剂检索系统是一个面向医生的轻量级方剂检索服务。医生或业务后端提交患者门诊采集信息，包括症状、舌诊、脉象、望闻问切描述等，系统基于《伤寒论》等结构化中医典籍资料返回匹配度靠前的方剂和依据条目。

一期目标是用现有《伤寒论》Excel 样例数据做出可演示的检索服务和接口文档，让业务后端能够导入/更新知识数据，并通过检索接口获得可展示的推荐结果。它不是一期的中医聊天机器人，也不负责生成诊疗建议。

## Core Value

医生输入患者症状后，系统必须能稳定返回有典籍依据、排序合理、可回连业务方剂库的推荐方剂列表。

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] 从《伤寒论》Excel 样例中解析约 1248 条有效病症-方剂记录，并保留完整展示字段。
- [ ] 将核心检索字段构造成适合语义检索和关键词检索的知识条目。
- [ ] 提供数据导入、重建索引、查看索引状态、更新/删除数据点等管理接口。
- [ ] 提供患者信息检索接口，接收症状、舌诊、脉象、补充描述等输入并返回 topK 方剂条目。
- [ ] 检索结果返回匹配分、方剂名称、方剂编码/回连标识、治法、证型、病名、原文依据、禁忌等字段。
- [ ] 输出接口文档，便于业务 Java 后端和前端联调。
- [ ] 部署一个示例服务或示例页面，支持客户在两到三周内查看效果。

### Out of Scope

- 生成式中医对话系统 — 一期沟通中已明确先拿掉对话，只做检索；后续增加预算再扩展。
- 私有大模型本地部署 — 原型中曾考虑，但一期采用公有模型/检索能力，避免设备和部署复杂度。
- 自动从原始古籍抽取知识 — 现阶段数据由客户人工整理成结构化表格提供。
- 处方明细业务库维护 — 检索服务返回方剂名称/code，处方药材明细由需求方业务系统维护和展示。
- 医疗诊断或处方决策闭环 — 系统提供检索参考和典籍依据，最终判断由医生完成。

## Context

项目来自一次中医方剂检索系统一期沟通。需求方已有产品原型和前端开发人员，但一期后端能力主要需要一个可被 Java 后端调用的检索服务。医生端会录入患者症状、舌诊、脉象等门诊信息，后端调用检索服务，检索服务返回若干匹配条目，再由业务后端根据方剂 code 查本地处方库并返回前端展示。

当前基础数据位于 `data/伤寒论原文 病症信息对应表（内容齐全 1 稿）.xlsx`。该文件是人工整理的《伤寒论》结构化病症信息对应表，约 1329 行、22 列，从第 4 行开始约 1248 条有效记录。字段包括编码、人模分类、主干部位、分支部位、主病主症、复合症、细分主症、同症异名、人模图示、舌诊、脉象、原文条文号、中医证型、中医病名、病因、病理、西医病名、中西先后、治法、推荐方剂、配伍与检查禁忌、疗效评定。

样例数据整体质量较高，适合一期检索验证。主要数据风险是 `编码` 列并非每条记录都有稳定值，`推荐方剂` 列也不总是单个方剂，有些条目包含多个证型对应多个方剂。后续如果业务系统依赖方剂 code 回连处方库，需要明确条目 ID、方剂 code、方剂名称归一化和多方剂拆分规则。

沟通记录位于 `data/任如亮项目对话.txt`，其中明确一期先基于伤寒论样例开发，后续可能扩展到最多约 200 本中医典籍。扩展前需要确认各典籍字段结构是否统一，否则需要设计多数据源字段映射层。

## Constraints

- **Timeline**: 两到三周内交付样例服务或页面 — 客户希望尽快看到效果。
- **Scope**: 一期只做检索，不做对话生成 — 避免把搜索引擎式需求误做成聊天系统。
- **Data Source**: 业务方维护 MySQL/二维表，检索服务构建独立索引 — 检索不应实时依赖业务库扫描。
- **Data Shape**: 先适配《伤寒论》Excel 的 22 列结构 — 后续 200 本书字段统一性尚未确认。
- **Integration**: 检索服务需要面向 Java 后端提供稳定 HTTP API 和接口文档 — 前端展示由需求方团队对接。
- **Scoring**: 匹配分可返回但主要用于排序展示 — 语义检索分数绝对值不应被解释为医学置信度。
- **Safety**: 返回内容应保留典籍依据、禁忌和西医优先建议字段 — 医疗场景需要让医生看到依据和风险提示。

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 一期定位为检索服务而非对话系统 | 沟通中多次确认先返回匹配方剂列表，生成式对话后续加预算再做 | — Pending |
| 使用独立向量/检索索引，不直接在 MySQL 实时检索 | 语义检索、重排和索引维护不适合直接依赖二维业务库查询 | — Pending |
| 以《伤寒论》Excel 为一期样例数据 | 当前数据完整、字段丰富，可快速验证效果 | — Pending |
| 数据管理接口和业务检索接口分开设计 | 管理接口服务索引维护，业务接口服务医生查询，职责更清晰 | — Pending |
| 方剂 code/条目 ID 需要独立规范 | Excel `编码` 不完整，推荐方剂存在多方剂文本，不能直接作为稳定回连键 | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-14 after initialization*
