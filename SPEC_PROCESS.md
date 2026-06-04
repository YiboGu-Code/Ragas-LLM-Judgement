# SPEC_PROCESS：与 Superpowers 协作生成 SPEC 与 PLAN 的过程记录

本文档用于记录：从最初需求到 [SPEC.md](file:///e:/Homework/SEEC3/RagasTest/SPEC.md) 与 [PLAN.md](file:///e:/Homework/SEEC3/RagasTest/PLAN.md) 的产出过程中，Superpowers 工作流（brainstorming → writing-plans）的关键对话节点、迭代与决策证据。

## 1. 背景与初始需求

**用户目标：**

- 基于 Ragas 搭建一个 LLM 测评平台（仅后端，不需要前端）
- 评测覆盖四类：Prompt、RAG、AI Workflow、AI Agent
- 强约束评测：输入规范、评测方式、结果输出，且必须保证通用性
- 使用 Superpowers 流程一步一步来

**早期约束与关键偏好（由用户明确给出/确认）：**

- 模型使用要抽象出一个接口，用户自行对接具体模型与网关
- 评测用例主要通过数据集文件提供（JSONL）
- 默认持久化存储用 SQLite
- 评测执行方式采用进程内异步（非外部队列）

## 2. Brainstorming 关键节点（追问与澄清）

在进入书面 SPEC 之前，重点通过“关键约束”来锁定通用平台边界，避免后续实现跑偏：

### 2.1 关键追问 1：模型/Embedding 的接入方式

目的：Ragas 通常需要 LLM-as-judge 与/或 embedding 能力，不同接入方式会决定平台的可移植性与抽象边界。

对话节选（压缩复述）：

> 我：评测执行时，平台调用被测 LLM/Embedding 的方式优先支持哪一种？（OpenAI 兼容 / Ollama / 单一云厂商 / 先做抽象层）  
> 你：先做抽象层。模型的使用抽象出一个接口，然后我自己来手动对接实现需要使用哪个模型。

决策：在 SPEC 中明确 ModelProvider 接口（chat/embed），平台核心不依赖任何厂商 SDK；provider_ref 仅保存与透传，且不得回显敏感字段。

### 2.2 关键追问 2：评测输入数据的供给方式

目的：评测的可复用性与可追溯性很大程度由 Dataset 机制决定；内联样本与外部数据拉取会显著影响范围与复杂度。

对话节选（压缩复述）：

> 我：评测用例希望主要通过哪种方式提供？（数据集文件 / 请求内联 / 二者都要 / 从外部拉取）  
> 你：数据集文件。

决策：以 JSONL 数据集上传作为主路径，并在 SPEC 中强制 schema 校验、记录行号错误；Run 引用 dataset_id 复用数据集。

### 2.3 关键追问 3：默认数据库与落盘策略

目的：是否“零配置可运行”直接决定工具可用性；同时需要兼顾后续可迁移到 Postgres 的可能。

对话节选（压缩复述）：

> 我：默认持久化存储用哪种数据库？（SQLite / Postgres / 仅文件 / 不落盘）  
> 你：SQLite 默认。

决策：SPEC 与 PLAN 都以 SQLite 为默认；同时在数据模型层保持清晰边界，未来可替换为 Postgres 而不影响业务逻辑。

### 2.4 关键追问 4：Run 执行方式（同步 vs 异步）

目的：评测任务通常耗时，平台必须支持查询进度与失败原因；但用户不希望引入 Redis 等外部依赖。

对话节选（压缩复述）：

> 我：评测任务执行方式默认是哪种？（异步队列 / 进程内异步 / 同步 / 仅生成任务配置）  
> 你：进程内异步。

决策：采用进程内异步执行引擎（并发控制、超时、取消、状态查询），并将分布式队列明确为非目标。

## 3. 关键迭代（至少 3 轮）与处理决策

### 迭代 1：从“要做测评平台”收敛到“通用抽象边界”

输入：你提出“基于 Ragas 搭建测评平台，覆盖四类评测，强约束输入输出，保证通用性”。  
处理：优先澄清“模型接入”与“被测系统接入”的抽象方式，避免平台被某个模型 SDK 或业务代码锁死。  
产出决策：三类可插拔接口成为架构主线：

- ModelProvider：你自行对接具体模型与 embedding
- SUTAdapter：把 Prompt/RAG/Workflow/Agent 的执行统一输出为 Trace
- Metric：把评分统一成 `MetricResult`，并显式 requirements 与 skipped 规则

### 迭代 2：从“评测四类形态”收敛到“统一的 Dataset/Trace 规约”

输入：四类评测天然需要不同中间产物（RAG contexts、workflow steps、agent tool calls）。  
处理：在 SPEC 中强制每类 record 的 input schema 与 trace 必需字段，避免实现阶段由 adapter“自由发挥”导致指标不可计算。  
产出决策：在 SPEC 中明确：

- RAG：必须由 trace 产出 `retrieval.contexts`，否则依赖 contexts 的指标必须 skipped
- Workflow：trace 必须有 steps（输入/输出/耗时/状态）
- Agent：trace 必须有 messages，tool_calls 可选但结构固定

### 迭代 3：从“平台能力列表”收敛到“可执行的 Run 生命周期”

输入：用户要求可通用评测与结果输出，且无需前端。  
处理：把能力落实为 API 闭环：Dataset 上传 → Run 创建/启动 → 查询 items → 导出，形成最小可用平台。  
产出决策：在 SPEC 中定义稳定错误返回结构（error.code/message/details）与导出格式（JSONL/CSV/JSON），在 PLAN 中按 TDD 拆解到每个 endpoint 的测试用例与实现步骤。

## 4. 采纳与推翻：哪些建议来自 AI，哪些被修正

### 4.1 采纳的建议（AI 提出 → 你采纳）

- **FastAPI 单体 + 插件化执行/评测（推荐方案）**：作为“零配置可运行 + 可扩展”的平衡点被采纳。
- **以 Dataset(JSONL) 为中心的评测复用机制**：满足通用性与可追溯性。
- **严格 skipped 规则**：缺字段不猜测补全，明确标记 skipped 并解释原因，避免误导性分数。
- **provider_ref 不回显敏感信息**：安全性需求被写入 SPEC，并在 PLAN 中规划为可测试的脱敏模块。

### 4.2 未采纳/延后（AI 提出 → 你未采纳或延后）

- **外部队列（Redis/Celery/RQ）**：为减少依赖与符合“进程内异步”偏好，明确为非目标。
- **从外部 URL/S3/Git 自动拉取数据集**：为控制范围与复杂度，作为非目标或未来扩展点。

## 5. 对 brainstorming 技能的反思

### 5.1 做得好的地方

- 先锁定关键不可逆决策（模型接入方式、数据输入方式、存储与执行方式），能显著降低后续实现返工风险。
- 将“通用性”落到可操作的约束：接口抽象 + schema + trace + skipped 规则，避免泛泛而谈。

### 5.2 不足与改进空间

- 对 Ragas 指标的“最小可用集合”与其对 chat/embed 的依赖细节，还可以在 brainstorming 阶段更早明确（例如首期必须支持哪些 ragas 指标、哪些属于可选）。
- 对 artifacts 的保存策略与合规策略，可以进一步追问（例如默认脱敏规则、哪些字段绝不落盘）。

## 6. 冷启动验证试跑（不同智能体）

按照课程要求，本项目在正式进入实现前，需要使用“与主开发智能体不同”的 agent，仅凭 `SPEC.md` + `PLAN.md` 冷启动试跑 1–2 个任务，并把证据记录在此处。

**当前状态：未执行（仍待完成）。**

原因：虽然已进入实现阶段并完成了部分任务，但尚未按要求使用“不同于主开发智能体”的第二个 agent 进行冷启动试跑，因此本节先保留为空并明确标注待补充。

**计划的冷启动试跑方式（执行时将补充证据）：**

- 提供给第二个 agent 的输入：仅 [SPEC.md](file:///e:/Homework/SEEC3/RagasTest/SPEC.md) + [PLAN.md](file:///e:/Homework/SEEC3/RagasTest/PLAN.md)
- 选择试跑任务（建议 1–2 个）：
  - 任务 2：插件接口与 registry（能暴露接口/命名一致性问题）
  - 任务 3：数据集 schema 校验（能暴露输入约束是否足够清晰）
- 要求第二个 agent 的行为：遇到不确定处停下来提问，不允许自行猜测继续

**执行完成后，本节将补充以下内容：**

- 第二个 agent 提出的关键问题与其暴露的 SPEC/PLAN 缺陷
- 它对需求的误读点与原因归因（spec 写错/不够清晰 vs agent 误读）
- 它产出的代码与测试与预期的差距分析
- 基于该反馈对 SPEC/PLAN 做出的修订，并给出关键 diff 片段

## 7. 实现阶段过程补充（简要，便于追溯）

为保证过程证据可追溯，在开始执行 PLAN 后补充关键实施节点（不替代 `AGENT_LOG.md`）：

- Git 初始化：仓库最初不是 git repository，因此先执行 `git init` 并提交了 SPEC/PLAN/SPEC_PROCESS 与 Python 骨架（commit：e871524）。
- Worktree：按课程建议创建 `.worktrees/feat-backend-mvp`，在分支 `feat/backend-mvp` 上开发，避免污染默认分支。
- Task 2（插件接口与 registry）：
  - 先写失败测试 `tests/test_plugin_registry.py`，观察到 `ModuleNotFoundError: app.plugins`（红灯）。
  - 添加 `app/plugins/interfaces.py`、`app/plugins/registry.py` 并让测试通过（绿灯）。
  - 当前实现提交：857a961。
- Task 3（数据集 schema 校验）：
  - 先写失败测试 `tests/test_dataset_validation.py`，观察到 `ModuleNotFoundError: app.datasets`（红灯）。
  - 添加 `app/datasets/records.py` 与 `app/datasets/validator.py` 并让测试通过（绿灯）。
  - 当前实现提交：71d88d5。
- Task 4（SQLite 持久化模型）：
  - 先写失败测试 `tests/test_db_models.py`，观察到 `ModuleNotFoundError: app.db`（红灯）。
  - 添加 `app/db/*` 并让测试通过（绿灯），同时修复 Python 3.12 的 `datetime.utcnow` 弃用告警。
  - 当前实现提交：39df4a2。
- Task 5（FastAPI 入口与 healthz）：
  - 先写失败测试 `tests/test_healthz.py`，观察到 `ModuleNotFoundError: app.main`（红灯）。
  - 添加 `app/main.py` 并让测试通过（绿灯）。
  - 当前实现提交：9b7a8f0。
- Task 6（Dataset 上传/查询 API）：
  - 先写失败测试 `tests/test_datasets_api.py`，观察到 `ImportError: cannot import name 'create_app'`（红灯）。
  - 引入 `create_app()` 工厂（支持按环境变量创建独立 app/DB），并实现 `/datasets` 上传与 schema 错误返回 422（绿灯）。
  - 当前实现提交：b9050a2。
- Task 7（HTTP SUTAdapter）：
  - 先写失败测试 `tests/test_sut_http_adapter.py`，观察到 `ModuleNotFoundError: app.sut`（红灯）。
  - 添加 `app/sut/http_adapter.py` 并让测试通过（绿灯）。
  - 当前实现提交：4e5cfdb。
- Task 8（进程内异步 RunEngine）：
  - 先写失败测试 `tests/test_execution_engine.py`，观察到 `ModuleNotFoundError: app.execution`（红灯）。
  - 添加 `app/execution/engine.py` 并让测试通过（绿灯），包含并发控制与超时失败标记。
  - 当前实现提交：5ae7a9b。
- Task 9（基础指标与严格 skipped 规则）：
  - 先写失败测试 `tests/test_metric_requirements.py`，观察到 `ModuleNotFoundError: app.metrics`（红灯）。
  - 添加 `app/metrics/basic.py`，实现 `rag_contexts_present`：缺失 `trace.retrieval.contexts` 时严格 `skipped`（绿灯）。
  - 当前实现提交：a8411cf。
- Task 10（Ragas 指标封装：requirements + skipped）：
  - 先写失败测试 `tests/test_ragas_metrics_skipped.py`，观察到 `ModuleNotFoundError: app.metrics.ragas_metrics`（红灯）。
  - 添加 `app/metrics/ragas_metrics.py`，实现 `RagasFaithfulnessMetric` / `RagasAnswerRelevancyMetric` 的 requirements 检查，不满足条件时严格 `skipped`（绿灯）。
  - 当前实现提交：94b30c7。
- Task 11（Run 生命周期 API：创建/启动/查询/items/取消）：
  - 先写失败测试 `tests/test_runs_api.py`，观察到 `AttributeError: 'State' object has no attribute 'registry'`（红灯）。
  - 在 `app/main.py` 初始化 `PluginRegistry` 并注册内置 adapter/metric；添加 `app/api/runs.py` 与 `app/schemas/runs.py`，实现 Run 的创建、后台启动、查询与 items 获取、取消（绿灯）。
  - 当前实现提交：c88f014。
- Task 12（导出 API：jsonl/csv/json）：
  - 扩展测试 `tests/test_runs_api.py`，观察到 `GET /runs/{run_id}/export` 返回 404（红灯）。
  - 在 `app/api/runs.py` 添加导出端点，支持 jsonl/csv/json 三种格式，并保持字段稳定（绿灯）。
  - 当前实现提交：a36621f。
- Task 13（脱敏与 artifacts 开关）：
  - 先写失败测试 `tests/test_artifacts_redaction.py`，覆盖 `save_artifacts=true/false` 与脱敏规则；初始实现未落盘、无 trace_ref（红灯）。
  - 添加 `app/artifacts/redaction.py` 与 `app/artifacts/store.py`，并在 Run 执行落库时按开关写入 artifacts、记录 `trace_ref`，对敏感字符串做默认脱敏（绿灯）。
  - 当前实现提交：3b291dd。
- Task 14（Dockerfile + GitHub Actions CI）：
  - 添加 `Dockerfile`（启动 `uvicorn app.main:app`）与 `.github/workflows/ci.yml`（pytest + docker build），以及 `.dockerignore` 控制构建上下文。
  - 当前实现提交：23084e6。

## 8. 结论与下一步

- 你已审查并确认当前 [SPEC.md](file:///e:/Homework/SEEC3/RagasTest/SPEC.md) 与 [PLAN.md](file:///e:/Homework/SEEC3/RagasTest/PLAN.md) 可进入实现阶段。
- 下一步将采用“子代理驱动（subagent-driven-development）”执行 PLAN 中的任务，并在实现过程中持续更新 PLAN 勾选与 commit hash，同时记录 `AGENT_LOG.md`。

## 9. 最终验证与 push 证据（任务 15）

本节记录“完成前的可重复验证证据”和“push GitHub 的尝试结果”，对应 [PLAN.md](file:///e:/Homework/SEEC3/RagasTest/PLAN.md) 的任务 15。

### 9.1 静态检查（ruff）

环境说明：当前环境中 `ruff` 命令不可直接调用，需要通过 `python -m ruff` 调用。

执行命令：

```bash
python -m ruff check .
```

观察到输出（节选）：

```txt
All checks passed!
```

### 9.2 单元测试（pytest）

执行命令：

```bash
python -m pytest -q
```

观察到输出（节选）：

```txt
20 passed in 0.80s
```

补充说明：为避免 anyio 默认参数化到 `trio` 后在当前环境触发 “There is no current event loop” 报错，新增了 `tests/conftest.py` 固定 `anyio_backend = "asyncio"`，使 async 测试在所有环境下稳定运行（commit：3d99be0）。

### 9.3 push GitHub

远端：

- origin: `https://github.com/YiboGu-Code/-Ragas-LLM-.git`

执行命令：

```bash
git push -u origin main
```

结果：失败（网络错误）。

错误信息（节选）：

```txt
fatal: unable to access 'https://github.com/YiboGu-Code/-Ragas-LLM-.git/': Recv failure: Connection was reset
```
