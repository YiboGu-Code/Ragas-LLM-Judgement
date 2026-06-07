# 前端交接文档：LLM Eval Backend（FastAPI + SQLite）

本文件用于帮助另一个智能体/工程师基于当前后端项目快速构建前端界面。内容包含：核心概念、数据流、落盘位置、配置方式、所有对外 HTTP 接口、请求/响应结构、常见错误与前端页面建议。

> 后端入口：[main.py](file:///e:/Homework/SEEC3/RagasTest/app/main.py)

---

## 1. 核心概念（前端需要理解）

### 1.1 Dataset（数据集）

- 数据集以 JSONL 上传（每行一个 JSON 对象），后端严格校验 schema（按 `eval_type`）。
- 上传后会生成 `dataset_id`，并默认将原始 JSONL 落盘保存（可配置关闭）。
- Dataset 元信息会写入 SQLite 的 `datasets` 表（见 [models.py](file:///e:/Homework/SEEC3/RagasTest/app/db/models.py)）。

### 1.2 Run（一次评测执行）

- Run 只绑定一个 `dataset_id` + 一个 `eval_type`（创建 run 时会校验它们一致）。
- Run 执行是异步的：`POST /runs/{run_id}/start` 后后台线程执行。
- Run 的逐条结果（每个 record 一条）写入 SQLite 的 `run_items` 表。

### 1.3 Item（逐条评测结果）

每条 record 会生成一个 item，包含：
- `status`: `succeeded|failed`
- `output`: 该条样本的输出（dataset-only 模式来自 dataset 的 `output/trace`；SUT 模式来自 /execute）
- `metrics`: 多个指标的计算结果（每个指标 `ok|skipped|failed`）
- `trace_ref`: 可选，指向落盘 trace 文件路径（artifacts）

### 1.4 Artifacts（trace 落盘）

- 如果 run 配置或默认配置启用 `save_artifacts`，后端会把每条记录的 trace 存成文件：
  - `artifacts/<RUN_ID>/<record_id>.json`
- item 中的 `trace_ref` 会返回该文件相对路径。

---

## 2. 两种运行模式（前端创建 Run 时要体现）

后端支持两种模式（见 [runs.py:create_run](file:///e:/Homework/SEEC3/RagasTest/app/api/runs.py#L209-L260)）：

### 2.1 Dataset-only（推荐，不依赖 SUT）

- 创建 run 时 **不传 `sut`**，后端会默认使用：
  - `{"adapter_name": "dataset", "adapter_config": {}}`
- 要求：每条 record 必须包含 `output` 或 `trace`（至少其一），否则该条 item 会 `failed`：
  - 错误：`dataset adapter requires record.trace and/or record.output`
  - 逻辑见 [dataset_adapter.py](file:///e:/Homework/SEEC3/RagasTest/app/sut/dataset_adapter.py)

### 2.2 SUT 模式（可选）

- 创建 run 时传 `sut.adapter_name="http"`，后端会调用你的被测系统 `POST /execute` 获取 trace/output。
- 本项目已实现 http 适配器，但是否可用取决于你是否真的部署了 SUT 服务。

---

## 3. 数据落盘位置（前端“结果保存到哪”相关提示）

默认配置见 [config.py](file:///e:/Homework/SEEC3/RagasTest/app/core/config.py)：

- SQLite：`data/app.db`（环境变量：`APP_SQLITE_PATH`）
- 上传数据集保存目录：`data/datasets`（环境变量：`APP_DATASET_DIR`）
  - 文件名：`data/datasets/<DATASET_ID>.jsonl`（写入逻辑见 [datasets.py](file:///e:/Homework/SEEC3/RagasTest/app/api/datasets.py#L38-L44)）
- artifacts：`artifacts`（环境变量：`APP_ARTIFACT_DIR`）
  - 文件结构：`artifacts/<RUN_ID>/<record_id>.json`（写入逻辑见 [store.py](file:///e:/Homework/SEEC3/RagasTest/app/artifacts/store.py#L12-L26)）

导出接口 `/runs/{id}/export` 是即时返回内容，不会自动在服务器落盘。

---

## 4. 配置与鉴权（前端注意事项）

### 4.1 服务地址

- 开发默认：`http://127.0.0.1:8000`

### 4.2 环境变量

后端使用 `APP_` 前缀读取配置（见 [config.py](file:///e:/Homework/SEEC3/RagasTest/app/core/config.py#L6-L15)）。

### 4.3 Ark Provider 的密钥

- `ARK_API_KEY` 必须通过环境变量提供（后端启动时会自动读取根目录 `.env` 注入）。
- 前端 **不要** 把密钥放到 `provider_ref.config`，后端会拒绝（见 [runs.py:_provider_config_contains_secrets](file:///e:/Homework/SEEC3/RagasTest/app/api/runs.py#L26-L38)）。

---

## 5. 数据模型（前端需要的字段）

### 5.1 Dataset API Response

定义见 [schemas/datasets.py](file:///e:/Homework/SEEC3/RagasTest/app/schemas/datasets.py)：

#### DatasetCreateResponse

```json
{
  "dataset_id": "uuid",
  "records_count": 6,
  "eval_type": "prompt",
  "schema_version": "v1"
}
```

#### DatasetGetResponse

```json
{
  "dataset_id": "uuid",
  "name": null,
  "eval_type": "prompt",
  "schema_version": "v1",
  "records_count": 6,
  "raw_path": "data\\datasets\\<dataset_id>.jsonl"
}
```

### 5.2 Run API Request/Response

定义见 [schemas/runs.py](file:///e:/Homework/SEEC3/RagasTest/app/schemas/runs.py)：

#### RunCreateRequest（核心）

```json
{
  "dataset_id": "uuid",
  "eval_type": "prompt|rag|workflow|agent",
  "sut": null,
  "metrics": [
    { "metric_name": "ragas_answer_relevancy", "metric_config": {} }
  ],
  "provider_ref": {
    "provider_name": "ark|manual|none",
    "config": {
      "base_url": "https://ark.cn-beijing.volces.com/api/v3",
      "model": "doubao-seed-2-0-mini-260428",
      "embedding_model": "doubao-embedding-vision-251215"
    }
  },
  "execution": {
    "max_concurrency": 2,
    "timeout_seconds": 90,
    "save_artifacts": true,
    "artifact_redaction": "default_v1"
  }
}
```

说明：
- dataset-only：把 `sut` 直接省略或传 `null`。
- `provider_ref.provider_name="none"` 时，Ragas 类指标会因缺 provider 而 `skipped`。

#### RunCreateResponse

```json
{ "run_id": "uuid", "status": "created" }
```

#### RunGetResponse

```json
{
  "run_id": "uuid",
  "status": "created|running|succeeded|failed|canceled",
  "progress": { "total": 6, "completed": 6, "failed": 0 }
}
```

#### RunItemsResponse（用于列表展示）

```json
{
  "items": [
    {
      "record_id": "p1",
      "status": "succeeded|failed",
      "error": { "type": "ValueError", "message": "..." },
      "output": { "answer": "..." },
      "trace_ref": "artifacts\\<RUN_ID>\\p1.json",
      "metrics": [
        { "name": "ragas_answer_relevancy", "status": "ok|skipped|failed", "score": 0.8, "details": {}, "version": "1" }
      ],
      "duration_ms": 1234
    }
  ]
}
```

---

## 6. JSONL 数据集 schema（上传校验规则）

上传校验逻辑见 [validator.py](file:///e:/Homework/SEEC3/RagasTest/app/datasets/validator.py#L21-L43) 与 [records.py](file:///e:/Homework/SEEC3/RagasTest/app/datasets/records.py)。

共同约束：
- 每行必须是 JSON object
- `type` 必须与上传时的 `eval_type` 一致（比如上传 `eval_type=prompt`，每行 `type` 必须是 `"prompt"`）
- 可选字段（dataset-only 推荐用到）：
  - `output`: 任意 JSON 或字符串
  - `trace`: 任意 JSON（用于 metrics 读取 `trace.output.answer`、`trace.retrieval.contexts`、`trace.agent.messages`）

### 6.1 Prompt record

最小必填：

```jsonl
{"record_id":"p1","type":"prompt","input":{"user_input":"...","system_prompt":"..."}}
```

dataset-only 推荐：

```jsonl
{"record_id":"p1","type":"prompt","input":{"user_input":"...","system_prompt":"..."},"output":{"answer":"..."},"trace":{"output":{"answer":"..."}}}
```

### 6.2 RAG record

最小必填：

```jsonl
{"record_id":"r1","type":"rag","input":{"question":"...","retrieval_config":{"top_k":3}}}
```

dataset-only + Ragas contexts 指标推荐：

```jsonl
{"record_id":"r1","type":"rag","input":{"question":"..."},"expected":{"reference":"..."},"trace":{"output":{"answer":"..."},"retrieval":{"contexts":[{"id":"c1","text":"...","source":"dataset"}]}}}
```

### 6.3 Workflow record

```jsonl
{"record_id":"w1","type":"workflow","input":{"goal":"...","inputs":{"k":"v"}},"output":{"answer":"..."},"trace":{"output":{"answer":"..."}}}
```

### 6.4 Agent record

```jsonl
{"record_id":"a1","type":"agent","input":{"task":"..."},"output":{"answer":"..."},"trace":{"agent":{"messages":[{"role":"user","content":"..."},{"role":"assistant","content":"..."}]}}}
```

---

## 7. 指标（metrics）与可选项（供前端下拉框）

后端在启动时注册的 metrics 见 [main.py](file:///e:/Homework/SEEC3/RagasTest/app/main.py#L30-L52)：

### 7.1 内置基础指标

- `rag_contexts_present`：检查 `trace.retrieval.contexts` 是否存在（见 [basic.py](file:///e:/Homework/SEEC3/RagasTest/app/metrics/basic.py)）

### 7.2 Ragas 指标（需要 provider）

实现见 [ragas_metrics.py](file:///e:/Homework/SEEC3/RagasTest/app/metrics/ragas_metrics.py)：

- `ragas_faithfulness`
- `ragas_answer_relevancy`
- `ragas_context_precision`
- `ragas_context_recall`
- `ragas_answer_correctness`
- `ragas_agent_goal_accuracy`

前端可将每个指标的“常见 skipped 原因”提示给用户（来自 MetricResult.details.reason）：
- 缺 provider：`missing provider`
- 缺 trace 输出：`missing trace.output.answer`
- 缺 contexts：`missing trace.retrieval.contexts`
- 缺 ground truth：`missing record.expected.reference`
- agent 缺 messages：`missing trace.agent.messages`

---

## 8. Provider（模型提供方）与配置

目前注册 provider：
- `ark`（见 [providers.py](file:///e:/Homework/SEEC3/RagasTest/app/providers.py#L80-L120)）

前端可用的 provider_ref 示例：

```json
{
  "provider_name": "ark",
  "config": {
    "base_url": "https://ark.cn-beijing.volces.com/api/v3",
    "model": "doubao-seed-2-0-mini-260428",
    "embedding_model": "doubao-embedding-vision-251215"
  }
}
```

注意：
- 真实密钥通过环境变量 `ARK_API_KEY` 注入，不在 config 里传。
- `embedding_model` 只在需要 embedding 的指标时必须（例如 `ragas_answer_relevancy`、`ragas_answer_correctness`）。

---

## 9. 全量 HTTP API 清单（前端调用）

所有路由来源：
- [datasets.py](file:///e:/Homework/SEEC3/RagasTest/app/api/datasets.py)
- [runs.py](file:///e:/Homework/SEEC3/RagasTest/app/api/runs.py)
- [main.py](file:///e:/Homework/SEEC3/RagasTest/app/main.py)

### 9.1 Health

#### GET /healthz

响应：

```json
{ "status": "ok" }
```

### 9.2 Datasets

#### POST /datasets

Content-Type：`multipart/form-data`

字段：
- `eval_type`：`prompt|rag|workflow|agent`
- `file`：JSONL 文件（UTF-8）
- `name`（可选）

成功响应：`DatasetCreateResponse`

常见错误：
- 422：非 UTF-8 或 schema 校验失败（错误信息包含行号）

#### GET /datasets/{dataset_id}

成功响应：`DatasetGetResponse`

常见错误：
- 404：dataset not found

### 9.3 Runs

#### POST /runs

Body：JSON（`RunCreateRequest`）

语义：
- dataset-only：`sut` 省略/为 null（后端自动用 dataset adapter）

常见错误（重要）：
- 404：`dataset not found`
- 422：`eval_type mismatch with dataset`
- 422：`dataset is not runnable (raw_path missing)`
- 422：`unknown metric`
- 422：`unknown sut adapter`
- 422：`provider_ref.config must not include secrets; use environment variables`

#### POST /runs/{run_id}/start

启动后台执行。重复调用不会重复执行（如果 status 已不是 created/queued，会直接返回当前状态）。

#### GET /runs/{run_id}

查询 run 状态与 progress。

#### GET /runs/{run_id}/items

查询逐条结果。用于前端“结果表格”。

#### GET /runs/{run_id}/export?format=csv|json|jsonl

导出 run + items：
- `format=json`：返回 `{run, items}`
- `format=jsonl`：每行一个 item（纯文本返回）
- `format=csv`：扁平化 CSV，列名为 `metric.<name>.status/score`

#### POST /runs/{run_id}/cancel

取消运行中的 run。

---

## 10. 前端页面建议（信息架构）

### 10.1 Dataset 上传页

- 输入：eval_type 下拉框（prompt/rag/workflow/agent）、文件选择、可选 name
- 提交：POST /datasets
- 成功后跳转 Dataset 详情页（展示 dataset_id、records_count、raw_path）
- 失败显示：422 的 `detail`（通常包含行号）

### 10.2 Dataset 详情页

- 展示：dataset_id、eval_type、records_count、raw_path
- 操作：创建 Run（跳转 Run 创建页，预填 dataset_id + eval_type）

### 10.3 Run 创建页（核心）

- 必填：dataset_id、eval_type（最好从 Dataset 详情页带入，避免 mismatch）
- 选择模式：
  - dataset-only（默认）：sut 不填写
  - SUT：http adapter（可选 UI；若用户没部署 SUT，建议隐藏或明显提示）
- metrics 多选：展示已注册 metric_name 列表
- provider：
  - provider_name：ark / none
  - config：base_url、model、embedding_model（根据所选 metrics 动态提示是否必填）
- execution：max_concurrency、timeout_seconds、save_artifacts、artifact_redaction
- 提交：POST /runs

### 10.4 Run 详情页

- 顶部：run_id、status、progress（轮询 GET /runs/{id}）
- 操作：start / cancel
- items 表格：GET /runs/{id}/items
  - 列建议：record_id、status、duration_ms、error、每个 metric 的 status/score、trace_ref
  - 点击 trace_ref：提示用户到服务器 `artifacts/...` 路径读取（当前后端未提供“下载 artifact 文件”的专用 API）
- 导出按钮：GET /runs/{id}/export?format=csv|json|jsonl

---

## 11. 调试与排错（前端提示文案建议）

- `eval_type mismatch with dataset`：你选的 eval_type 和 dataset 上传时的 eval_type 不一致；回到 Dataset 详情页重新创建 run。
- `dataset adapter requires record.trace and/or record.output`：dataset-only 模式下 record 缺少 output/trace；需要重新上传包含 output/trace 的 JSONL。
- 指标 `skipped`：缺必要字段或缺 provider；前端展示 `details.reason`。
- run `failed` 且 items 中存在 `record_id="__run__"`：这是“run 级别”错误项，用于展示早期失败原因（数据集读取失败、provider 初始化失败等）。

