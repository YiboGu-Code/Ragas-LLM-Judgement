# 数据集（JSONL）规约：Prompt / RAG / Workflow / Agent

本文档用于指导 SUT 系统生成“合规数据集”，使其可以直接上传到本项目后端 `POST /datasets`，并用于 dataset-only 模式评测（不依赖 SUT 执行接口）。

权威校验来源（后端上传校验逻辑）：
- [records.py](file:///e:/Homework/SEEC3/RagasTest/app/datasets/records.py)
- [validator.py](file:///e:/Homework/SEEC3/RagasTest/app/datasets/validator.py)

---

## 1. 总览（必须满足）

- 文件格式：JSONL（每行一个 JSON object）
- 编码：UTF-8
- 每行必须包含字段 `type`，且必须与上传时的 `eval_type` 一致
  - 例如：上传 `eval_type=rag`，则每行 `type` 必须为 `"rag"`
- 空行允许存在（会被忽略）
- 每条 record 建议提供稳定的 `record_id`（字符串），用于结果对齐与回溯
  - 如果不提供，后端在运行时会按行号生成（例如 `line-1`）

---

## 2. 通用字段（所有类型通用）

每行 record 结构（通用）：

```json
{
  "record_id": "可选，推荐：稳定唯一字符串",
  "type": "prompt|rag|workflow|agent（必填）",
  "input": { "必填，不同类型结构不同" },
  "expected": { "可选，ground truth / reference 等" },
  "output": "可选，任意 JSON 或字符串",
  "trace": { "可选，任意 JSON 对象，用于 metrics 读取" },
  "tags": { "可选，任意 JSON 对象（元信息）" }
}
```

### 2.1 dataset-only 运行的最低要求（强烈建议遵守）

本项目支持 dataset-only 模式：不调用 SUT，只从 dataset 里拿 `output/trace` 来做评测。

为保证 run 可运行，**每条 record 至少提供 `output` 或 `trace` 其中一个**。否则该条会在运行时失败（错误类似：`dataset adapter requires record.trace and/or record.output`）。

建议优先提供 `trace`，并把最终答案放在：
- `trace.output.answer`

---

## 3. 四类场景详细规约

下面给出每种 `type` 的：
- **最小可上传**：仅满足上传校验（能上传成功）
- **推荐可评测**：满足 dataset-only + 常见 metrics 的字段需求

### 3.1 Prompt 数据集（type="prompt"）

#### 最小可上传

```jsonl
{"record_id":"p1","type":"prompt","input":{"user_input":"...","system_prompt":"..."}}
```

必填字段：
- `input.user_input`：字符串

可选字段：
- `input.system_prompt`：字符串
- `input.variables`：对象
- `input.constraints`：对象

#### 推荐可评测（dataset-only）

```jsonl
{"record_id":"p1","type":"prompt","input":{"user_input":"用一句话解释什么是单元测试","system_prompt":"你是严谨的软件工程助教。"},"expected":{"reference":"..."},"output":{"answer":"..."},"trace":{"output":{"answer":"..."}},"tags":{"topic":"testing"}}
```

推荐字段说明：
- `trace.output.answer`：最终回答文本（多数字段需求都从这里读取）
- `expected.reference`：可选的参考答案（用于 correctness 类指标）

### 3.2 RAG 数据集（type="rag"）

#### 最小可上传

```jsonl
{"record_id":"r1","type":"rag","input":{"question":"...","retrieval_config":{"top_k":3}}}
```

必填字段：
- `input.question`：字符串

可选字段：
- `input.retrieval_config`：对象（如 `{ "top_k": 3 }`）

#### 推荐可评测（dataset-only + RAG 指标）

```jsonl
{"record_id":"r1","type":"rag","input":{"question":"什么是依赖注入（DI）？给出一个简短定义。","retrieval_config":{"top_k":3}},"expected":{"reference":"..."},"output":{"answer":"..."},"trace":{"output":{"answer":"..."},"retrieval":{"contexts":[{"id":"c1","text":"...","source":"dataset"}]}},"tags":{"topic":"di"}}
```

RAG 推荐字段说明：
- `trace.output.answer`：最终回答
- `trace.retrieval.contexts`：检索上下文列表
  - 建议使用对象列表，每项至少包含 `text`
  - 推荐字段：`id`、`text`、`source`
- `expected.reference`：可选 ground truth（用于 context_recall / answer_correctness 等）

### 3.3 Workflow 数据集（type="workflow"）

#### 最小可上传

```jsonl
{"record_id":"w1","type":"workflow","input":{"goal":"...","inputs":{"k":"v"}}}
```

必填字段：
- `input.goal`：字符串

可选字段：
- `input.inputs`：对象
- `input.workflow_ref`：对象（例如工作流模板/版本引用）

#### 推荐可评测（dataset-only）

```jsonl
{"record_id":"w1","type":"workflow","input":{"goal":"从一段需求中提取验收标准","inputs":{"requirement":"..."}},"expected":{"reference":"..."},"output":{"answer":"..."},"trace":{"output":{"answer":"..."}},"tags":{"workflow":"req-to-ac"}}
```

### 3.4 Agent 数据集（type="agent"）

#### 最小可上传

```jsonl
{"record_id":"a1","type":"agent","input":{"task":"..."}}
```

必填字段：
- `input.task`：字符串

可选字段：
- `input.tools_allowed`：字符串数组
- `input.environment`：对象
- `input.termination_criteria`：对象

#### 推荐可评测（dataset-only + Agent 指标）

```jsonl
{"record_id":"a1","type":"agent","input":{"task":"你是一个代码审查助手。请给出对某个 PR 的审查清单。","tools_allowed":["http"],"termination_criteria":{"max_steps":3}},"output":{"answer":"..."},"trace":{"output":{"answer":"..."},"agent":{"messages":[{"role":"user","content":"..."},{"role":"assistant","content":"..."}]}},"tags":{"agent":"review"}}
```

Agent 推荐字段说明：
- `trace.agent.messages`：多轮对话消息数组
  - 每项建议包含：`role`（user/assistant/system）与 `content`
- `trace.output.answer`：可选（如果你希望同时跑 answer_relevancy / correctness 等）

---

## 4. Metrics 字段要求（SUT 生成 trace 时最重要）

下面是常用指标对 dataset 字段的“最低要求”。缺字段通常会在结果中表现为 `skipped`（原因会体现在 `details.reason`）。

### 4.1 不依赖大模型的基础指标

- `rag_contexts_present`
  - 需要：`trace.retrieval.contexts`
  - score：存在且非空通常视为通过；为空/缺失则不通过

### 4.2 依赖大模型（Provider）的 Ragas 指标（0~1 分，越高越好）

提示：这些指标需要后端配置 provider（例如 Ark + 环境变量注入密钥），否则会 `skipped`（reason 类似：`missing provider`）。

- `ragas_faithfulness`
  - 需要：`trace.output.answer` + `trace.retrieval.contexts`
  - 语义：回答是否能被检索到的上下文支撑（减少幻觉）

- `ragas_answer_relevancy`
  - 需要：`trace.output.answer`（通常还需要 embedding 模型）
  - 语义：回答与问题/目标的相关性

- `ragas_context_precision`
  - 需要：`trace.retrieval.contexts` + `expected.reference`
  - 语义：检索到的上下文是否“精准”（噪声越少越好）

- `ragas_context_recall`
  - 需要：`trace.retrieval.contexts` + `expected.reference`
  - 语义：检索到的上下文是否“覆盖”了参考答案所需信息（覆盖越多越好）

- `ragas_answer_correctness`
  - 需要：`trace.output.answer` + `expected.reference`（通常还需要 embedding 模型）
  - 语义：回答与参考答案的一致性/正确性

- `ragas_agent_goal_accuracy`
  - 需要：`trace.agent.messages`
  - 语义：Agent 对话过程与最终结果是否达成任务目标

---

## 5. 常见失败与排查

- 上传 422：`schema error line=...`
  - 说明：该行 JSON 结构不满足当前 `eval_type` 的 Pydantic schema
  - 建议：对照 [records.py](file:///e:/Homework/SEEC3/RagasTest/app/datasets/records.py) 修正该行字段结构

- 创建 run 422：`eval_type mismatch with dataset`
  - 说明：run 的 eval_type 与 dataset 上传时 eval_type 不一致

- 运行时某条 item failed：`dataset adapter requires record.trace and/or record.output`
  - 说明：dataset-only 模式下该条 record 缺少 `trace` 且缺少 `output`

