# 使用手册：基于 Ragas 的 LLM 测评平台（后端）

本项目提供一个仅后端的通用测评平台（FastAPI + SQLite + 本地 artifacts），用于对以下四类对象进行评测：

- Prompt
- RAG
- AI Workflow
- AI Agent

平台通过“数据集（JSONL）→ Run（执行）→ Items（逐条结果）→ 导出（JSONL/CSV/JSON）”形成闭环；模型与被测系统（SUT）均通过抽象接口/HTTP 适配器接入，平台核心不绑定任何特定模型 SDK。

补充说明：

- 平台支持两种运行模式：
  - 数据集评测（推荐）：不需要接入外部 SUT。你在 JSONL 中直接提供每条样本的 `output` / `trace`，平台只负责跑指标（Ragas 等）并产出结果。
  - SUT 评测（可选）：你提供一个对外服务的被测系统（SUT），平台通过 HTTP 调用 `POST /execute` 获取 `output` / `trace` 后再跑指标。

---

## 1. 快速启动

### 1.1 本地启动（推荐用于开发与调试）

安装依赖：

```bash
python -m venv .venv
```

进入虚拟环境（Windows PowerShell）：

```bash
.\.venv\Scripts\Activate.ps1
```

进入虚拟环境（macOS/Linux）：

```bash
source .venv/bin/activate
```

安装依赖：

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
```

启动服务：

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

健康检查：

```bash
curl http://127.0.0.1:8000/healthz
```

预期响应：

```json
{ "status": "ok" }
```

### 1.2 Docker 启动（推荐用于演示/部署）

构建镜像：

```bash
docker build -t llm-eval-backend:local .
```

运行：

```bash
docker run --rm -p 8000:8000 llm-eval-backend:local
```

---

## 2. 配置（环境变量）

配置由 `APP_` 前缀的环境变量控制（见 [config.py](file:///e:/Homework/SEEC3/RagasTest/app/core/config.py)）。

常用项：

- `APP_SQLITE_PATH`：SQLite 文件路径，默认 `data/app.db`
- `APP_DATASET_DIR`：上传数据集保存目录，默认 `data/datasets`
- `APP_ARTIFACT_DIR`：trace artifacts 保存目录，默认 `artifacts`
- `APP_SAVE_RAW_DATASETS`：是否保存上传的原始 JSONL，默认 `true`
- `APP_SAVE_ARTIFACTS`：是否保存每条记录的 trace artifact，默认 `true`
- `APP_DEFAULT_MAX_CONCURRENCY`：默认并发度，默认 `4`
- `APP_DEFAULT_TIMEOUT_SECONDS`：默认单条超时秒数，默认 `120`

示例（Windows PowerShell）：

```powershell
$env:APP_SQLITE_PATH="data/app.db"
$env:APP_SAVE_ARTIFACTS="true"
```

方舟（Ark）Provider 相关环境变量：

- `ARK_API_KEY`：方舟 API Key。必须通过环境变量提供，不要写进 `provider_ref.config`。

本项目会在启动时自动读取根目录的 `.env`，并将其中的键值注入到当前进程的环境变量中（如果系统环境变量已经存在，则默认不覆盖）。

`.env` 示例：

```env
ARK_API_KEY=YOUR_ARK_API_KEY
```

---

## 3. Dataset：上传数据集（JSONL）

上传接口：

- `POST /datasets`（multipart/form-data）
  - `eval_type`: `prompt|rag|workflow|agent`
  - `file`: JSONL 文件（UTF-8）
  - `name`（可选）

校验规则：

- JSONL 每行必须是 JSON 对象
- 必须符合对应 `eval_type` 的严格 schema
- 空文件/空数据集会被拒绝
- 校验失败会返回 422，并包含行号信息（例如 `schema error line=3: ...`）
- 除了严格 schema 要求的字段外，每条 record 还可以额外包含：
  - `output`：该条样本的输出（用于“数据集评测”模式）
  - `trace`：该条样本的轨迹（用于依赖 contexts / agent messages 的指标）

### 3.1 Prompt 数据集示例

`prompt.jsonl`：

```jsonl
{"record_id":"p1","type":"prompt","input":{"user_input":"用一句话解释什么是单元测试","system_prompt":"你是一个严谨的软件工程助教"}}
{"record_id":"p2","type":"prompt","input":{"user_input":"把下面这句英文翻译成中文：Hello world."}}
```

如果使用“数据集评测”模式，需要在数据集中提供 `output` 或 `trace.output`（否则该条样本没有可评测的输出，会被标记为 failed）。例如：

```jsonl
{
  "record_id": "p3",
  "type": "prompt",
  "input": {
    "user_input": "用一句话解释什么是单元测试"
  },
  "output": {
    "answer": "单元测试是对最小可测试单元进行验证的自动化测试。"
  }
}
```

上传：

```bash
curl -X POST http://127.0.0.1:8000/datasets \
  -F "eval_type=prompt" \
  -F "file=@prompt.jsonl"
```

上传（Windows PowerShell）：

```powershell
curl.exe -X POST http://127.0.0.1:8000/datasets `
  -F "eval_type=prompt" `
  -F "file=@prompt.jsonl"
```

### 3.2 RAG 数据集示例

`rag.jsonl`：

```jsonl
{
  "record_id": "r1",
  "type": "rag",
  "input": {
    "question": "什么是依赖注入？",
    "retrieval_config": {
      "top_k": 3
    }
  }
}
```

上传：

```bash
curl -X POST http://127.0.0.1:8000/datasets \
  -F "eval_type=rag" \
  -F "file=@rag.jsonl"
```

上传（Windows PowerShell）：

```powershell
curl.exe -X POST http://127.0.0.1:8000/datasets `
  -F "eval_type=rag" `
  -F "file=@rag.jsonl"
```

### 3.3 Workflow 数据集示例

`workflow.jsonl`：

```jsonl
{
  "record_id": "w1",
  "type": "workflow",
  "input": {
    "goal": "从一段需求中提取验收标准",
    "inputs": {
      "requirement": "做一个后端测评平台"
    }
  }
}
```

### 3.4 Agent 数据集示例

`agent.jsonl`：

```jsonl
{
  "record_id": "a1",
  "type": "agent",
  "input": {
    "task": "给定一个 Python 函数，找出潜在的边界条件并写出 3 条单元测试用例",
    "tools_allowed": [
      "python",
      "http"
    ]
  }
}
```

---

## 4. Run：创建/启动/查询/导出

Run 生命周期相关接口（见 [runs.py](file:///e:/Homework/SEEC3/RagasTest/app/api/runs.py)）：

- `POST /runs`：创建 run（只做引用校验与落库，不执行）
- `POST /runs/{run_id}/start`：启动 run（后台线程异步执行）
- `GET /runs/{run_id}`：查询 run 状态与进度
- `GET /runs/{run_id}/items`：获取逐条结果
- `GET /runs/{run_id}/export?format=jsonl|csv|json`：导出

### 4.1 创建 run（示例）

说明：

- `sut` 字段现在是可选的：
  - 不填写 `sut`：默认使用 `dataset` 适配器（不发 HTTP），直接用数据集中的 `output` / `trace` 做评测
  - 填写 `sut.adapter_name = "http"`：通过 HTTP 调用外部被测系统（SUT）
- `metrics.metric_name` 可用内置指标包括：
  - `rag_contexts_present`
  - `ragas_faithfulness`
  - `ragas_answer_relevancy`
  - `ragas_context_precision`
  - `ragas_context_recall`
  - `ragas_answer_correctness`
  - `ragas_agent_goal_accuracy`
- `provider_ref` 用于指定评测时使用的 LLM/Embedding provider。本项目内置 `ark` provider（火山方舟 OpenAI 兼容）。

创建 run（数据集评测：不写 `sut`）：

```bash
cat > run_create.json <<'JSON'
{
  "dataset_id": "<DATASET_ID>",
  "eval_type": "rag",
  "metrics": [{ "metric_name": "rag_contexts_present", "metric_config": {} }],
  "provider_ref": {
    "provider_name": "ark",
    "config": {
      "base_url": "https://ark.cn-beijing.volces.com/api/v3",
      "model": "deepseek-v3-2-251201",
      "embedding_model": "doubao-embedding-vision-251215"
    }
  },
  "execution": { "max_concurrency": 2, "timeout_seconds": 10, "save_artifacts": true, "artifact_redaction": "default_v1" }
}
JSON

curl -X POST http://127.0.0.1:8000/runs \
  -H "Content-Type: application/json" \
  --data-binary "@run_create.json"
```

创建 run（Windows PowerShell，数据集评测：不写 `sut`）：

```powershell
@'
{
  "dataset_id": "<DATASET_ID>",
  "eval_type": "rag",
  "metrics": [{ "metric_name": "rag_contexts_present", "metric_config": {} }],
  "provider_ref": {
    "provider_name": "ark",
    "config": {
      "base_url": "https://ark.cn-beijing.volces.com/api/v3",
      "model": "deepseek-v3-2-251201",
      "embedding_model": "doubao-embedding-vision-251215"
    }
  },
  "execution": { "max_concurrency": 2, "timeout_seconds": 10, "save_artifacts": true, "artifact_redaction": "default_v1" }
}
'@ | Set-Content -Encoding utf8 run_create.json

curl.exe -X POST http://127.0.0.1:8000/runs `
  -H "Content-Type: application/json" `
  --data-binary "@run_create.json"
```

返回示例：

```json
{ "run_id": "...", "status": "created" }
```

### 4.2 启动 run

```bash
curl -X POST http://127.0.0.1:8000/runs/<RUN_ID>/start
```

### 4.3 查询 run 状态

```bash
curl http://127.0.0.1:8000/runs/<RUN_ID>
```

返回示例：

```json
{
  "run_id": "...",
  "status": "running",
  "progress": { "total": 0, "completed": 0, "failed": 0 }
}
```

### 4.4 查看 items

```bash
curl http://127.0.0.1:8000/runs/<RUN_ID>/items
```

每条 item 字段说明：

- `status`: `succeeded|failed`
- `output`: SUT 返回的输出（由 SUT 决定结构）
- `trace_ref`: 当开启 artifacts 保存时，为本地文件路径（否则为 null）
- `metrics`: 指标列表，每个元素形如 `{name,status,score,details,version}`

### 4.5 导出结果

JSON：

```bash
curl "http://127.0.0.1:8000/runs/<RUN_ID>/export?format=json"
```

JSONL：

```bash
curl "http://127.0.0.1:8000/runs/<RUN_ID>/export?format=jsonl"
```

CSV：

```bash
curl "http://127.0.0.1:8000/runs/<RUN_ID>/export?format=csv"
```

---

## 5. 接入被测系统（SUT）：HTTP /execute 契约

如果你希望评测“一个真实运行的系统”（例如在线 RAG 服务、Agent 服务），可以使用 SUT 模式。当 run 创建时指定：

- `sut.adapter_name = "http"`
- `sut.adapter_config.base_url = "http://<sut-host>:<sut-port>"`

平台会对 `POST {base_url}/execute` 发起请求（见 [http_adapter.py](file:///e:/Homework/SEEC3/RagasTest/app/sut/http_adapter.py)）：

请求体：

```json
{"record":{...}}
```

响应体（建议结构）：

```json
{
  "output": { "answer": "..." },
  "trace": {
    "output": { "answer": "..." },
    "retrieval": {
      "contexts": [{ "id": "c1", "text": "...", "source": "..." }]
    },
    "workflow": {
      "steps": [
        {
          "name": "step1",
          "status": "ok",
          "duration_ms": 12,
          "input": {},
          "output": {}
        }
      ]
    },
    "agent": {
      "messages": [
        { "role": "user", "content": "..." },
        { "role": "assistant", "content": "..." }
      ],
      "tool_calls": []
    }
  }
}
```

说明：

- 平台不会替 SUT “补齐” trace 字段；缺字段会导致依赖该字段的指标被严格标记为 `skipped`
- 内置 `rag_contexts_present` 只关心 `trace.retrieval.contexts`

### 5.1 最小 SUT 示例（FastAPI）

你可以用下面的示例快速起一个被测系统服务（端口 9000），返回一个包含 contexts 的 trace，便于验证 `rag_contexts_present`：

```python
from fastapi import FastAPI

app = FastAPI()


@app.post("/execute")
async def execute(payload: dict):
    record = payload.get("record") or {}
    question = (record.get("input") or {}).get("question") or ""

    trace = {
        "output": {"answer": f"echo: {question}"},
        "retrieval": {"contexts": [{"id": "c1", "text": "示例上下文", "source": "demo"}]},
    }

    return {"output": trace["output"], "trace": trace}
```

启动该示例服务：

```bash
uvicorn sut_demo:app --host 127.0.0.1 --port 9000
```

---

## 6. 常见问题

### 6.1 为什么 ragas\_\* 指标一直是 skipped？

常见原因：

- 未配置 `ARK_API_KEY`（或 provider 初始化失败），导致 provider 不可用
- 数据集中没有提供指标所需字段：
  - 例如 `ragas_faithfulness` 需要 `trace.retrieval.contexts` 和 `trace.output.answer`
  - 例如 `ragas_answer_relevancy` 需要 `trace.output.answer`
  - 例如 `ragas_context_precision/recall` 需要 `record.expected.reference` 与 `trace.retrieval.contexts`

平台不会替你“补齐”缺失字段，缺字段会被严格标记为 `skipped`。

### 6.2 artifacts 保存在哪里？如何关闭？

- 默认保存目录：`APP_ARTIFACT_DIR`（默认 `artifacts`）
- run 创建时可以在 `execution.save_artifacts` 覆盖开关
- 默认脱敏策略：`execution.artifact_redaction="default_v1"`（会对常见密钥模式做替换）
