# 四类场景 Metrics 详版说明

本文是详版说明，对应“选项 3”：不仅说明四个场景分别采用哪些 metrics，还会详细说明每个 metric 的依赖字段、是否依赖 provider / embeddings、具体计算方法、`skipped` 的典型原因，以及当前实现中的特殊处理逻辑。

内容以当前仓库代码为准，主要依据：

- `app/metrics/basic.py`
- `app/metrics/ragas_metrics.py`
- `frontend/src/pages/RunCreatePage.tsx`

## 1. 总览

### 1.1 四类场景与对应 metrics

| 场景 | 默认/推荐采用的 metrics |
| --- | --- |
| `prompt` | `ragas_answer_relevancy`、`ragas_answer_correctness` |
| `rag` | `rag_contexts_present`、`ragas_faithfulness`、`ragas_answer_relevancy`、`ragas_context_precision`、`ragas_context_recall` |
| `workflow` | `ragas_answer_relevancy`、`ragas_answer_correctness` |
| `agent` | `ragas_agent_goal_accuracy` |

### 1.2 两类计算方式

当前项目里的 metrics 并不完全采用同一种计算路径，而是分成两类：

#### A. 规则 / 启发式计算

这类指标不依赖外部 LLM，分数由后端代码直接计算：

- `rag_contexts_present`
- `ragas_faithfulness`
- `ragas_context_recall`

#### B. Ragas + LLM / embeddings 计算

这类指标由后端把 record/trace 组装成 ragas 样本，再调用 ragas 的 `aevaluate()` 计算：

- `ragas_answer_relevancy`
- `ragas_context_precision`
- `ragas_answer_correctness`
- `ragas_agent_goal_accuracy`

## 2. 通用预处理逻辑

在介绍具体指标前，先说明所有 ragas 相关指标共享的一些底层逻辑。

### 2.1 文本截断

项目通过环境变量限制输入到指标中的文本长度与上下文数量，以降低 token 消耗和超时风险：

- `RAGAS_MAX_TEXT_CHARS`，默认 `800`
- `RAGAS_MAX_CONTEXTS`，默认 `3`

这意味着：

- 很长的 `answer`、`reference`、`user_input` 会先截断再参与计算
- RAG 场景只会保留前若干条 contexts 参与计算

### 2.2 启发式 overlap 的文本归一化

用于 `ragas_faithfulness` 和 `ragas_context_recall` 的启发式算法会做如下处理：

1. 去掉首尾空白
2. 转小写
3. 将连续空白折叠
4. 去掉大部分标点
5. 生成固定长度的 shingle 集合

shingle 长度由环境变量控制：

- `RAGAS_HEURISTIC_SHINGLE_N`，默认 `2`

### 2.3 provider 注入逻辑

对于走 ragas 的指标，后端会：

1. 从 provider 获取 `llm`
2. 必要时获取 `embeddings`
3. 如果 metric 实例上还没有 `llm` 或 `embeddings`，就自动注入
4. 调用 `aevaluate(...)`

这一步的作用是兼容某些 ragas 版本对 metric 实例属性的要求，避免出现例如：

- `answer_relevancy requires embeddings to be set`

### 2.4 `skipped` 与 `ok`

当前平台对 metric 的输出状态主要有：

- `ok`：成功算出 score
- `skipped`：缺字段、缺 provider、缺 embeddings、ragas 返回空分数等

因此“没有算出分”不一定是错误，也可能只是输入不满足该 metric 的 requirements。

## 3. Prompt 场景

Prompt 场景的输入核心是：

- `record.input.user_input`
- `trace.output.answer`
- 如果要做 correctness，还需要 `record.expected.reference`

### 3.1 `ragas_answer_relevancy`

#### 作用

评估回答是否与用户问题/指令相关，是否“切题”。

#### 依赖字段

- `record.input.user_input`
- `trace.output.answer`

#### 是否需要外部能力

- 需要 provider 的 chat LLM
- 需要 embeddings

#### 具体计算方法

后端执行流程如下：

1. 提取 `user_input`
2. 提取 `answer`
3. 对两者做长度截断
4. 构造 ragas 单轮样本：

```json
{
  "user_input": "...",
  "response": "..."
}
```

5. 调用：

- ragas `AnswerRelevancy()`
- `aevaluate(dataset=..., metrics=[...], llm=..., embeddings=...)`

6. 读取 ragas 返回的 score

#### 分数解释

- 通常为 `0~1`
- 越高表示回答越切题

#### 常见 `skipped` 原因

- `missing record input`
- `missing trace.output.answer`
- `missing provider`
- `provider missing get_ragas_embeddings()`
- `ragas returned empty score`

### 3.2 `ragas_answer_correctness`

#### 作用

评估回答是否正确、是否与参考答案一致。

#### 依赖字段

- `record.input.user_input`
- `record.expected.reference`
- `trace.output.answer`

#### 是否需要外部能力

- 一般需要 provider 的 chat LLM
- 一般需要 embeddings

#### 具体计算方法

后端有一个非常关键的特殊分支：

1. 提取 `user_input`
2. 提取 `reference`
3. 提取 `answer`
4. 如果：

```text
reference.strip() == answer.strip()
```

则直接返回：

- `status = ok`
- `score = 1.0`
- `details.shortcut = "reference_equals_answer"`

5. 只有在不完全相等时，才进入 ragas 正常打分流程：

```json
{
  "user_input": "...",
  "response": "...",
  "reference": "..."
}
```

并调用：

- ragas `AnswerCorrectness()`

#### 分数解释

- 完全相等时一定为 `1.0`
- 否则由 ragas + LLM/embeddings 计算，通常为 `0~1`

#### 常见 `skipped` 原因

- `missing record input`
- `missing record.expected.reference`
- `missing trace.output.answer`
- `missing provider`
- `ragas returned empty score`

## 4. RAG 场景

RAG 场景比 Prompt 多出一类关键数据：

- `trace.retrieval.contexts`

因此它除了回答类指标，还会涉及上下文存在性、上下文精度、上下文覆盖度等指标。

### 4.1 `rag_contexts_present`

#### 作用

检查检索上下文是否存在。

#### 依赖字段

- `trace.retrieval.contexts`

#### 是否需要外部能力

- 不需要 provider
- 不需要 LLM
- 不需要 embeddings

#### 具体计算方法

1. 读取 `trace.retrieval.contexts`
2. 若字段不存在，则：
   - `status = skipped`
   - `reason = missing trace.retrieval.contexts`
3. 若字段存在，则：
   - `len(contexts) > 0` 时 score = `1.0`
   - `len(contexts) == 0` 时 score = `0.0`

#### 分数解释

- `1.0` 表示存在至少一个 context
- `0.0` 表示字段存在但为空数组

### 4.2 `ragas_faithfulness`

#### 作用

评估回答是否忠实于检索到的上下文，即回答里的信息能否在 contexts 中找到支持。

#### 依赖字段

- `trace.output.answer`
- `trace.retrieval.contexts`

#### 是否需要外部能力

- 当前实现不需要 provider
- 当前实现不调用 LLM

#### 具体计算方法

当前项目中它已经**不再直接调用 ragas Faithfulness()**，而是改成启发式算法：

1. 提取 `answer`
2. 提取 `contexts`
3. 对文本做截断
4. 将所有 contexts 文本拼接
5. 对 answer 和 contexts 分别生成 shingle 集合
6. 计算：

```text
score = |answer_shingles ∩ context_shingles| / |answer_shingles|
```

也就是：回答中的信息片段，有多少能在上下文中找到。

#### 分数解释

- 越接近 `1`，说明回答越“可由上下文支持”
- 越接近 `0`，说明回答与 contexts 的重叠越少

#### 说明

该实现的 `details` 会明确标记：

- `method = heuristic`
- `heuristic = shingle_overlap`

#### 常见 `skipped` 原因

- `missing trace.retrieval.contexts`
- `missing trace.output.answer`

### 4.3 `ragas_answer_relevancy`

#### 作用

评估 RAG 回答是否切题，是否回答了用户问题。

#### 依赖字段

- `record.input.question`
- `trace.output.answer`

#### 是否需要外部能力

- 需要 provider chat
- 需要 embeddings

#### 具体计算方法

与 Prompt 场景下的 `ragas_answer_relevancy` 相同，只是输入字段改为：

- `record.input.question`

构造样本：

```json
{
  "user_input": "question",
  "response": "answer"
}
```

然后调用 ragas `AnswerRelevancy()`

### 4.4 `ragas_context_precision`

#### 作用

评估“检索到的内容是否精准”，即 contexts 中有多少是与参考答案真正相关的。

#### 依赖字段

- `record.input.question`
- `record.expected.reference`
- `trace.retrieval.contexts`

#### 是否需要外部能力

- 需要 provider chat
- 当前实现不显式传 embeddings

#### 具体计算方法

1. 提取 `question`
2. 提取 `reference`
3. 提取 `contexts`
4. 限制 contexts 数量与文本长度
5. 构造 ragas 样本：

```json
{
  "user_input": "...",
  "reference": "...",
  "retrieved_contexts": ["...", "..."]
}
```

6. 调用 ragas `ContextPrecision()`

#### 分数解释

- 越高表示上下文越“精准”
- 即检索出来的内容中，和参考答案相关的部分占比越高

#### 常见 `skipped` 原因

- `missing record input`
- `missing record.expected.reference`
- `missing trace.retrieval.contexts`
- `missing provider`
- `ragas returned empty score`

### 4.5 `ragas_context_recall`

#### 作用

评估检索到的 contexts 是否覆盖了参考答案所需的信息。

#### 依赖字段

- `record.expected.reference`
- `trace.retrieval.contexts`

#### 是否需要外部能力

- 当前实现不需要 provider
- 当前实现不调用 LLM

#### 具体计算方法

当前项目中它也已经改成启发式算法：

1. 提取 `reference`
2. 提取 `contexts`
3. 归一化并生成 shingle 集合
4. 计算：

```text
score = |reference_shingles ∩ context_shingles| / |reference_shingles|
```

也就是：参考答案中的信息片段，有多少已经被 contexts 覆盖。

#### 分数解释

- 越接近 `1`，说明检索上下文越完整
- 越接近 `0`，说明上下文对参考答案的覆盖很差

#### 说明

`details` 中会标记：

- `method = heuristic`
- `heuristic = shingle_overlap`

#### 常见 `skipped` 原因

- `missing record.expected.reference`
- `missing trace.retrieval.contexts`

## 5. Workflow 场景

Workflow 场景的核心输入字段是：

- `record.input.goal`
- `trace.output.answer`

如果要做 correctness，还需要：

- `record.expected.reference`

### 5.1 `ragas_answer_relevancy`

#### 作用

评估 workflow 输出是否与 `goal` 相关。

#### 依赖字段

- `record.input.goal`
- `trace.output.answer`

#### 计算方法

与 Prompt 场景相同，只是 `user_input` 的来源变成：

- `record.input.goal`

之后调用 ragas `AnswerRelevancy()`

### 5.2 `ragas_answer_correctness`

#### 作用

评估 workflow 的输出是否符合参考答案。

#### 依赖字段

- `record.input.goal`
- `record.expected.reference`
- `trace.output.answer`

#### 计算方法

与 Prompt 场景相同：

1. 若 `reference == answer`，直接返回 `1.0`
2. 否则调用 ragas `AnswerCorrectness()`

## 6. Agent 场景

Agent 场景和前面最大的不同是：输入不是简单的单轮文本，而是多轮消息轨迹。

### 6.1 `ragas_agent_goal_accuracy`

#### 作用

评估 agent 的整体多轮行为是否达成目标。

#### 依赖字段

优先依赖：

- `trace.agent.messages`

若没有消息数组，后端会尝试退化为：

- 从 `record.input.task` 提取用户任务
- 从 `trace.output.answer` 提取最终回答

#### 是否需要外部能力

- 需要 provider chat
- 不需要 embeddings

#### 具体计算方法

1. 读取 `trace.agent.messages`
2. 逐条消息转换为 ragas 消息对象：
   - `role=user` -> `HumanMessage`
   - `role=assistant` -> `AIMessage`
   - `role=tool` -> `ToolMessage`
3. 如果消息数组不可用，但存在 `task + answer`，则构造两条消息：
   - 一条 `HumanMessage(task)`
   - 一条 `AIMessage(answer)`
4. 将消息序列包装为：

```python
MultiTurnSample(user_input=messages)
```

5. 调用 ragas `AgentGoalAccuracyWithoutReference()`

#### 分数解释

- 通常为 `0~1`
- 越高表示 agent 越可能达成目标

#### 常见 `skipped` 原因

- `missing provider`
- `missing trace.agent.messages`
- `ragas returned empty score`

## 7. 四类场景的字段依赖对照

| 场景 | metric | 关键字段 |
| --- | --- | --- |
| `prompt` | `ragas_answer_relevancy` | `input.user_input`、`trace.output.answer` |
| `prompt` | `ragas_answer_correctness` | `input.user_input`、`expected.reference`、`trace.output.answer` |
| `rag` | `rag_contexts_present` | `trace.retrieval.contexts` |
| `rag` | `ragas_faithfulness` | `trace.output.answer`、`trace.retrieval.contexts` |
| `rag` | `ragas_answer_relevancy` | `input.question`、`trace.output.answer` |
| `rag` | `ragas_context_precision` | `input.question`、`expected.reference`、`trace.retrieval.contexts` |
| `rag` | `ragas_context_recall` | `expected.reference`、`trace.retrieval.contexts` |
| `workflow` | `ragas_answer_relevancy` | `input.goal`、`trace.output.answer` |
| `workflow` | `ragas_answer_correctness` | `input.goal`、`expected.reference`、`trace.output.answer` |
| `agent` | `ragas_agent_goal_accuracy` | `trace.agent.messages` 或 `input.task + trace.output.answer` |

## 8. 当前实现中的关键取舍

### 8.1 为什么有些指标改成 heuristic

项目在后期为了减少：

- token 消耗
- RAG 长上下文超时
- item `failed`

将最耗时、最容易超时的两个指标改成启发式：

- `ragas_faithfulness`
- `ragas_context_recall`

所以它们虽然仍保留 `ragas_*` 命名，但当前实际上不是通过 ragas 的 LLM 评分链路直接得到的。

### 8.2 `answer_correctness` 的快捷分支

如果参考答案和输出答案完全一致，直接返回 `1.0`，不再调用 ragas。这么做的意义是：

- 避免明明完全一致却因 LLM 解析失败而 `skipped/failed`
- 降低 token 消耗
- 提高稳定性

### 8.3 为什么会出现 `skipped`

`skipped` 在当前系统中通常不是 bug，而是输入条件不满足。例如：

- 没有 `expected.reference`
- 没有 `trace.output.answer`
- 没有 `trace.retrieval.contexts`
- 没有 provider
- provider 不支持 embeddings
- ragas 返回空分数

因此在使用 metrics 时，必须先保证对应字段齐全。

## 9. 总结

当前平台中四类场景的 metric 设计思路可以概括为：

- `prompt / workflow`：主要关注“回答是否切题、是否正确”
- `rag`：除了回答本身，还要评估“上下文是否存在、是否精准、是否覆盖充分、回答是否忠实于上下文”
- `agent`：主要关注“多轮行为是否达成目标”

从实现角度看，当前系统并不是“所有指标都统一走 ragas 原生链路”，而是在稳定性、成本和可解释性之间做了取舍：一部分指标用规则/启发式，一部分指标用 ragas + provider 真正计算。这一点在阅读和解释评测结果时必须明确区分。
