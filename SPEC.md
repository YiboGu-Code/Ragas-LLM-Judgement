# SPEC：基于 Ragas 的 LLM 测评平台（后端）

## 1. 问题陈述

大语言模型（LLM）应用在 Prompt、RAG、AI Workflow、AI Agent 四种形态下的质量评估，常见痛点是：

- 评测输入与输出缺少统一规范，导致不同团队、不同项目间无法复用数据集与结果
- 评测指标依赖具体模型/框架实现，迁移成本高，难以形成通用平台
- RAG/Agent/Workflow 评测需要“执行轨迹”与中间产物（contexts、steps、tool calls），而不仅是最终输出
- 评测任务通常耗时且需要并发，缺少可追溯的运行记录、制品与导出能力

本项目构建一个仅后端的通用测评平台，核心目标是：用统一的 Dataset + Run + Trace + Metric 规约，支持对 Prompt / RAG / AI Workflow / AI Agent 的可复用、可追溯评测；同时把模型与被测系统（SUT）抽象成接口，便于用户自行接入任意模型与业务系统。

## 2. 目标用户

- 需要对 Prompt/RAG/Agent/Workflow 做持续评测与回归的个人开发者、研究者
- 需要在不同模型/不同实现之间做横向对比的团队
- 课程项目场景：希望严格约束评测输入/输出与指标计算流程的学习者

## 3. 用户故事（至少 5 个，INVEST）

1. 作为平台使用者，我可以上传一个 JSONL 数据集并得到 schema 校验结果，以便后续多次复用同一数据集进行不同评测。
2. 作为平台使用者，我可以创建一次评测 Run，指定评测类型（prompt/rag/workflow/agent）、指标集与并发度，以便用同一套机制运行不同类型评测。
3. 作为平台使用者，我可以在 Run 执行期间查询进度与失败原因，以便定位数据问题或被测系统问题。
4. 作为平台使用者，我可以导出 Run 的逐条结果与聚合统计（JSONL/CSV），以便在外部做可视化或报告。
5. 作为平台使用者，我可以替换模型 Provider 实现（例如不同供应商或本地模型），而无需改动平台核心逻辑，以便保持通用性与可移植性。
6. 作为平台使用者，我可以对 RAG/Agent/Workflow 评测保存（或禁止保存）执行轨迹制品，以满足调试与合规需求。

## 4. 范围与非目标

### 4.1 范围（本期实现）

- 仅后端：HTTP API + 进程内异步执行 + SQLite 默认持久化
- 支持数据集上传（JSONL），支持四类评测的统一 schema 校验
- 支持创建 Run、启动 Run、查询 Run/Item 结果、导出结果
- 内置可扩展的抽象接口：
  - ModelProvider（由用户自行实现具体模型调用）
  - SUTAdapter（支持 prompt/rag/workflow/agent 四类执行）
  - Metric（指标计算，可内置部分基于 Ragas 或通用规则的实现）

### 4.2 非目标（本期不做）

- 前端 UI
- 分布式队列（Redis/Celery/RQ）与多节点调度
- 在线多租户权限体系（可保留扩展点，但不承诺本期实现）
- 对任意外部数据源的自动拉取（S3/HTTP/Git 等）

## 5. 术语与定义

- Dataset：评测样本集合（JSONL 文件）与其元数据
- Record：数据集中的一条样本
- Run：一次评测任务，引用一个 Dataset，并指定评测类型、SUT、指标、并发、配置快照
- SUT（System Under Test）：被测系统，可为 Prompt 模板、RAG 管道、Workflow 引擎、Agent 实现
- Trace（Execution Trace）：执行轨迹，包括中间步骤、检索上下文、工具调用、耗时等
- Metric：评分函数，对每条 record 给出分数与细节，并支持 Run 级聚合

## 6. 功能规约（模块化）

### 6.1 数据集管理（Dataset）

#### 输入

- 上传文件：JSONL（每行一个 JSON 对象）
- Content-Type：multipart/form-data
- 额外参数：
  - name：可选，用户自定义数据集名
  - eval_type：可选，若指定则用于更严格的 schema 校验（prompt/rag/workflow/agent）

#### 行为

- 平台必须逐行解析并校验：
  - JSON 语法合法
  - 必须字段存在
  - 字段类型正确（字符串/对象/数组/数字/布尔）
  - record_id 在同一数据集中必须唯一（若用户未提供，则平台生成稳定 id）
- 校验失败时返回：
  - 首个错误所在的行号与原因
  - 建议修复方式（例如缺字段、类型错误）
- 校验通过时：
  - 保存原始文件（可配置关闭）
  - 落库保存 dataset 元数据与统计（records_count、schema_version 等）

#### 输出

- dataset_id（UUID 或等价唯一标识）
- records_count
- eval_type（推断或用户指定）
- schema_version

#### 边界条件与错误处理

- 文件过大：返回 413，并给出最大支持大小与建议分片策略
- JSONL 行数为 0：返回 400
- schema 不符合：返回 422，包含 line_number 与 message

### 6.2 Run 创建与启动

#### 输入

- dataset_id：必填
- eval_type：必填（prompt/rag/workflow/agent）
- sut：必填，SUT 适配配置
  - adapter_name：字符串
  - adapter_config：JSON 对象
- metrics：必填，指标列表
  - 每项包含 metric_name 与 metric_config
- provider_ref：必填，模型 provider 的引用配置（平台只保存与透传，不解释其内部字段）
- execution：可选，执行参数
  - max_concurrency：默认 4
  - timeout_seconds：默认 120（单条 record）
  - save_artifacts：默认 true
  - artifact_redaction：默认按规则脱敏

#### 行为

- 创建 Run 时平台必须保存一份不可变的配置快照（config snapshot），用于复现
- 启动 Run 时：
  - 进入队列（进程内后台）
  - 逐条 record 执行 SUTAdapter，得到 Trace
  - 对 Trace 执行每个 Metric，得到 per-item 评分
  - 将 per-item 与聚合结果持久化

#### 输出

- run_id
- status（created/queued/running/succeeded/failed/canceled）
- 进度字段（total/completed/failed）

#### 边界条件与错误处理

- dataset_id 不存在：404
- eval_type 与 dataset schema 不匹配：422
- adapter_name 或 metric_name 未注册：422
- 后台执行异常：run 标记为 failed，并记录可追溯的错误摘要

### 6.3 结果查询与导出

#### 输入

- 查询 Run：run_id
- 查询 items：run_id + 分页参数（limit/offset）
- 导出：run_id + format（jsonl/csv/json）

#### 行为

- Run 查询返回：
  - 配置快照摘要
  - 聚合结果（每个 metric 的 mean、p50、p95、min、max、count）
  - 版本信息（平台版本、schema_version、metric 版本）
- Items 查询返回：
  - 每条 record 的 status、error（如有）、output、trace_ref、metrics
- 导出时：
  - jsonl：逐条 ItemResult（稳定字段）
  - csv：扁平化表格（每个 metric 一个列，错误列、耗时列等）
  - json：包含 RunSummary + items（可分页导出或完整导出）

#### 边界条件与错误处理

- run_id 不存在：404
- format 不支持：400

## 7. 四类评测的输入/行为/输出规约（严格）

本平台统一以 JSONL Record 为输入，统一以 Trace + Metrics 为输出。所有 schema 均包含顶层字段：

- record_id：字符串，可选（不提供则平台生成）
- type：字符串，必填，取值为 prompt/rag/workflow/agent
- input：对象，必填，类型相关的输入字段
- expected：对象，可选，用于 reference-based 指标
- tags：对象，可选，任意键值标签（用于分组聚合）

### 7.1 Prompt 评测（type=prompt）

#### 输入 schema（input）

- user_input：字符串，必填
- system_prompt：字符串，可选
- variables：对象，可选（用于模板变量）
- constraints：对象，可选（例如输出格式、语言、长度）

#### 输出约束

- output.text：字符串，必填
- trace.messages：数组，可选（系统/用户/助手消息）
- metrics：至少包含用户选择的 metric

### 7.2 RAG 评测（type=rag）

#### 输入 schema（input）

- question：字符串，必填
- retrieval_config：对象，可选（例如 top_k、filters；平台只透传）

#### Trace 约束（必须由 SUTAdapter 产出）

- trace.retrieval.contexts：字符串数组，必填（允许为空数组，但会影响部分指标）
- trace.retrieval.sources：对象数组，可选（例如 doc_id、url、score）
- output.answer：字符串，必填

#### expected（可选）

- ground_truth：字符串或字符串数组，可选

#### 评测规则

- 若缺失 contexts，则所有依赖 contexts 的指标必须标记为 skipped，并在 details 中给出原因
- 支持 reference-free 与 reference-based 指标混用，但必须在结果中显式标注 metric 的 requirements

### 7.3 AI Workflow 评测（type=workflow）

#### 输入 schema（input）

- goal：字符串，必填
- inputs：对象，可选（工作流输入参数）
- workflow_ref：对象，可选（例如 workflow_id、version；平台只透传）

#### Trace 约束

- trace.steps：数组，必填
  - step_id：字符串
  - name：字符串
  - input：对象或字符串
  - output：对象或字符串
  - started_at/ended_at：时间戳或耗时字段（二者至少一个）
  - status：succeeded/failed/skipped

#### 输出约束

- output.final：对象或字符串，必填（工作流最终输出）

### 7.4 AI Agent 评测（type=agent）

#### 输入 schema（input）

- task：字符串，必填
- tools_allowed：字符串数组，可选
- environment：对象，可选（约束与背景信息）
- termination_criteria：对象，可选（例如必须产出某种结构）

#### Trace 约束

- trace.messages：数组，必填（对话消息序列）
- trace.tool_calls：数组，可选
  - tool_name：字符串
  - arguments：对象
  - result：对象或字符串
  - status：succeeded/failed
- trace.safety：对象，可选（合规性标签）

#### 输出约束

- output.final：对象或字符串，必填（agent 最终产出）

## 8. 指标（Metrics）与 Ragas 集成约束

### 8.1 指标接口约束

- 每个 Metric 对单条 record 输出：
  - score：数值（默认 0.0–1.0），若不适用则 status=skipped
  - details：结构化对象（用于解释与调试）
  - version：字符串（用于复现）
- 每个 Metric 必须声明 requirements：
  - 需要 output 字段
  - 需要 trace.contexts
  - 需要 expected.ground_truth
  - 是否需要 ModelProvider（LLM-as-judge 或 embedding）

### 8.2 Ragas 使用原则（通用性优先）

- 平台不绑定特定供应商模型；Ragas（若使用）只能通过平台的 ModelProvider 接口获取所需 LLM/Embedding 能力
- 对缺失字段的 record：
  - 不允许“猜测补全”
  - 必须标记指标为 skipped，并在 details 中说明缺失字段
- Ragas 指标默认支持：
  - faithfulness（需要 contexts + answer + judge LLM）
  - answer_relevancy（需要 question + answer + judge LLM）
  - context_recall/context_precision（通常需要 ground_truth 或引用信息，缺失则跳过）

## 9. 系统架构

### 9.1 组件

- API 服务（HTTP）
  - Dataset API
  - Run API
  - Export API
- Execution Engine（进程内异步）
  - Scheduler：管理队列、并发度、取消
  - Worker：执行 SUTAdapter、调用 Metric
- Plugin Registry
  - 注册/发现 ModelProvider、SUTAdapter、Metric
- Storage
  - SQLite：Run/Dataset/ItemResult 元数据与聚合
  - Artifact Store：本地目录（可配置关闭）

### 9.2 数据流（简述）

1. 上传 JSONL → 校验 → 保存 Dataset
2. 创建 Run（保存配置快照）→ 启动 Run（排队）
3. 对每条 record：SUTAdapter 执行 → 产生 Trace → Metrics 打分 → 存 ItemResult
4. 聚合统计 → RunSummary
5. 查询/导出 → 返回稳定结构

## 10. 数据模型（逻辑）

- datasets
  - id, name, eval_type, schema_version, records_count, created_at
  - raw_path（可为空，若关闭保存原始文件）
- runs
  - id, dataset_id, eval_type, status, config_snapshot_json, created_at, started_at, finished_at
  - progress_total, progress_completed, progress_failed
- run_items
  - id, run_id, record_id, status, error_json, output_json, trace_ref, metrics_json, duration_ms
- artifacts
  - id, run_id, record_id, path, redaction_policy, created_at

## 11. API 设计（初版）

- POST /datasets
- GET /datasets/{dataset_id}
- POST /runs
- POST /runs/{run_id}/start
- GET /runs/{run_id}
- GET /runs/{run_id}/items?limit=&offset=
- GET /runs/{run_id}/export?format=jsonl|csv|json
- POST /runs/{run_id}/cancel
- GET /healthz

错误返回统一结构：

- error.code：稳定错误码
- error.message：人类可读信息
- error.details：结构化细节（如字段路径、行号、缺失字段列表）

## 12. 技术选型与理由

- 语言：Python（生态成熟，Ragas 生态友好，适合快速集成评测指标）
- Web 框架：FastAPI（类型友好、性能与开发效率平衡、OpenAPI 自动生成便于通用对接）
- 数据库：SQLite 默认（零配置启动，便于课程与单机场景；后续可平滑切换 Postgres）
- 异步执行：进程内后台任务（满足你指定的执行方式，避免 Redis 等外部依赖）
- 指标：以 Ragas 为核心的可插拔 Metric 体系，辅以通用指标（成功率、结构校验、耗时等）
- 模型接入：抽象 ModelProvider 接口，由用户自行实现（满足通用性与可控性）

## 13. 非功能性需求

### 13.1 性能

- 支持至少 4 并发执行（可配置）
- 单条 record 超时可控（timeout_seconds）
- 导出大结果集时支持流式输出或分页

### 13.2 安全

- 不记录或回显 provider_ref 中可能包含的敏感字段（例如 API key）
- artifacts 默认脱敏策略可配置（例如对 messages 中的疑似密钥模式做遮盖）
- 提供关闭 artifacts 保存的开关

### 13.3 可用性

- 关键 API 返回稳定结构与可追踪错误码
- Run 可取消，取消后不再启动新的 item

### 13.4 可观测性

- 记录 run 级与 item 级事件日志（不包含敏感信息）
- 在 RunSummary 中提供版本与配置快照哈希，便于复现

## 14. 验收标准（客观）

1. 能上传 prompt/rag/workflow/agent 任一类型的数据集 JSONL，并得到严格 schema 校验结果。
2. 能基于 dataset_id 创建 Run，并在后台执行；可查询进度与每条 item 的结果或错误。
3. Run 结果包含：
   - per-item 的标准化 output、metrics、trace_ref
   - run 级聚合统计（mean/p50/p95 等）
4. 能导出 JSONL 与 CSV，并且字段稳定、可被脚本解析。
5. 平台核心不依赖任何具体模型 SDK；替换 ModelProvider 不需要修改平台核心逻辑。

## 15. 风险与未决问题

- Ragas 与自定义 ModelProvider 的适配复杂度：需要确保 Ragas 所需的 LLM/Embedding 能力可通过接口表达
- Trace 的标准化：不同 SUT 实现产生的轨迹细节差异大，需要在最小必需字段与可扩展字段之间取得平衡
- 进程内异步的可靠性：服务重启会中断 run，需要定义重启后的状态恢复策略（初版可标记为 failed，并支持重跑）
- 数据集 schema 版本演进：需要明确向后兼容策略与迁移方案
