# 四类场景 Metrics 简版说明
本文是简版说明，对应“选项 1”：说明四个场景分别使用哪些 metrics，并给出尽量接近 Ragas 内部思路的计算链路与数学公式。内容以当前代码实现为准，主要参考 `app/metrics/basic.py` 与 `app/metrics/ragas_metrics.py`；当某个指标在本项目里已被启发式实现替代时，也会明确写出“当前项目公式”。

## 1. 总览
| 场景       | 当前采用的 metrics                                           |
| ---------- | ------------------------------------------------------------ |
| `prompt`   | `ragas_answer_relevancy`、`ragas_answer_correctness`         |
| `rag`      | `rag_contexts_present`、`ragas_faithfulness`、`ragas_answer_relevancy`、`ragas_context_precision`、`ragas_context_recall` |
| `workflow` | `ragas_answer_relevancy`、`ragas_answer_correctness`         |
| `agent`    | `ragas_agent_goal_accuracy`                                  |

## 2. Prompt 场景
### 2.1 `ragas_answer_relevancy`
- 作用：评估回答是否切题，是否与用户输入高度相关。

- Ragas 的核心思路不是“直接让 LLM 打一个总分”，而是先做“反向问题生成”：
  1. 从 `record.input` 提取 `user_input`
  2. 从 `trace.output` 提取 `answer`
  3. 让 LLM 根据 `answer` 反向生成 `N` 个可能对应的问题，记为 $q'_1, q'_2, ..., q'_N$
  4. 对原问题 $q$ 和每个反向问题 $q'_i$ 计算 embedding

- 近似计算公式：
$$
\text{AnswerRelevancy}(q, a) = \frac{1}{N} \sum_{i=1}^{N} \cos\left(E(q'_i), E(q)\right)
$$
其中：
- $q$：原始用户问题
- $a$：回答
- $q'_i$：由 LLM 基于回答反推的第 $i$ 个问题
- $E(\cdot)$：embedding 向量
- $N$：反向生成的问题数，Ragas 经典实现里默认常见为 $3$

- 余弦相似度公式：
$$
\cos(x, y) = \frac{x \cdot y}{\|x\| \|y\|}
$$

- 直观理解：
  - 如果一个回答真的切题，那么仅根据回答内容，LLM 大概率能“反推出”与原问题非常接近的问题；
  - 如果回答跑题、答非所问、信息冗余很多，反推出来的问题与原问题的 embedding 相似度就会下降。

- 本项目实现：
  - 调用 `AnswerRelevancy()`
  - 输入样本为 `{ user_input, response }`
  - 通过 `aevaluate()` 运行，最终返回 $0 \sim 1$ 左右的连续分值

### 2.2 `ragas_answer_correctness`
- 作用：评估回答是否与参考答案一致或接近。

- Ragas 将其拆成两个部分：
  - **事实一致性（factual similarity）**
  - **语义相似度（semantic similarity）**

- 第一步：把 $answer$ 与 $reference$ 分解为 statement 集合，然后由 LLM 判定：
  - $TP$：回答中存在且参考答案也存在的事实
  - $FP$：回答中出现但参考答案中不存在的事实
  - $FN$：参考答案中存在但回答中缺失的事实

- 第二步：基于 statement 级别的 TP/FP/FN 计算事实一致性的 F1：
$$
F_{\text{fact}} = \frac{|TP|}{|TP| + 0.5 \times (|FP| + |FN|)}
$$

- 第三步：计算回答与参考答案的语义相似度：
$$
S_{\text{sem}} = \cos\left(E(a), E(r)\right)
$$
其中：
- $a$：answer
- $r$：reference
- $E(\cdot)$：embedding 向量

- 第四步：加权合成最终分数。Ragas 经典实现中常见默认权重为 factuality $0.75$、semantic similarity $0.25$：
$$
\text{AnswerCorrectness} = 0.75 \cdot F_{\text{fact}} + 0.25 \cdot S_{\text{sem}}
$$

- 本项目实现差异：
  - 如果 $\text{reference.strip()} = \text{answer.strip()}$，直接走快捷路径返回 $1.0$
  - 否则调用 `AnswerCorrectness()`，即仍按 Ragas 的“事实 F1 + 语义相似度”思路计算

## 3. RAG 场景
### 3.1 `rag_contexts_present`
- 作用：检查是否提供了检索上下文。

- 这个指标不是 Ragas 原生 LLM 指标，而是本项目自定义规则指标。

- 当前项目分段函数公式：
$$
\text{rag\_contexts\_present} =
\begin{cases}
\text{skipped}, & \text{若 } trace.retrieval.contexts \text{ 字段不存在} \\
1.0, & \text{若 } |contexts| > 0 \\
0.0, & \text{若 } |contexts| = 0
\end{cases}
$$

- 它回答的问题是：“有没有提供检索上下文”，而不是“上下文本身是否正确”。

### 3.2 `ragas_faithfulness`
- 作用：评估回答是否忠实于检索到的上下文。

- **Ragas 原始思路公式：**
  1. 先把 $answer$ 拆成若干 statement：$s_1, s_2, ..., s_m$
  2. 对每个 statement，用 LLM 判断它是否能被 $retrieved\_contexts$ 支撑
$$
\text{Faithfulness}_{\text{ragas}} = \frac{\sum_{j=1}^{m} \mathbf{1}\left[s_j \text{ 可由上下文推出}\right]}{m}
$$
$\mathbf{1}[\cdot]$ 为指示函数，条件成立取 $1$，不成立取 $0$。

- **本项目当前实现并没有直接走上述 LLM 判定链路**，而是改成了启发式 shingle overlap，公式为：
  1. 先将 $answer$ 归一化后切成 $n$-shingles，记为 $S_n(answer)$
  2. 将所有 contexts 拼接、归一化后切成 $n$-shingles，记为 $S_n(contexts)$
$$
\text{Faithfulness}_{\text{project}} = \frac{\left|S_n(answer) \cap S_n(contexts)\right|}{\left|S_n(answer)\right|}
$$

- 代码中的具体实现约束：
  - $n = \text{RAGAS\_HEURISTIC\_SHINGLE\_N}$，默认 $2$
  - answer 与每条 context 都会先截断，默认最多 $800$ 字符
  - 最多只取前 $3$ 条 contexts

- 直观上，这个分数可以理解为：
  - “回答中的局部文本片段，有多大比例能在上下文文本里找到覆盖”

- 注意：
  - 这只是对 Ragas 原始 statement support ratio 的近似替代，不等价于真正的 statement 级事实核验

### 3.3 `ragas_answer_relevancy`
- 作用：评估回答是否切题。

- 公式与 Prompt / Workflow 场景的 `ragas_answer_relevancy` 完全相同，只是输入字段变成：
  - $q = record.input.question$
  - $a = trace.output.answer$

$$
\text{AnswerRelevancy}(q, a) = \frac{1}{N} \sum_{i=1}^{N} \cos\left(E(q'_i), E(q)\right)
$$

- 它衡量的是“回答是否切题”，不是“回答是否被上下文支撑”。

### 3.4 `ragas_context_precision`
- 作用：评估检索到的上下文是否“精准”，即上下文中有多少内容真正对参考答案有帮助。

- Ragas 的思路是：先判断每个 rank 上的 context 是否 relevant，再计算排名敏感的平均 precision。

- 设检索结果为 $c_1, c_2, ..., c_K$，相关性标记：
$$
v_k =
\begin{cases}
1, & c_k \text{ 对 reference 有帮助} \\
0, & c_k \text{ 无帮助}
\end{cases}
$$

- 则第 $k$ 位的 precision 为：
$$
P@k = \frac{\sum_{i=1}^{k} v_i}{k}
$$

- 最终 Context Precision：
$$
\text{ContextPrecision@K} = \frac{\sum_{k=1}^{K} \left(P@k \cdot v_k\right)}{\sum_{k=1}^{K} v_k}
$$

- 这个公式的含义是：
  - 只在“当前位置是相关块”时记一笔贡献；
  - 越早出现的相关块，会带来更高的分数；
  - 所以它是一个“排序敏感”的检索质量指标。

- 本项目实现：
  - 提供 $\{ user\_input, reference, retrieved\_contexts \}$
  - 调用 `ContextPrecision()`
  - $v_k$ 的判定由 Ragas 内部借助 LLM 完成，而不是本项目手工打标签

### 3.5 `ragas_context_recall`
- 作用：评估上下文是否覆盖了参考答案所需的信息。

- **Ragas 原始思路公式：**
  1. 先把 $reference$ 拆成 statement：$r_1, r_2, ..., r_t$
  2. 对每个 statement，判断是否能被 $retrieved\_contexts$ 支撑
$$
\text{ContextRecall}_{\text{ragas}} = \frac{\sum_{j=1}^{t} \mathbf{1}\left[r_j \text{ 可由上下文推出}\right]}{t}
$$

- 它和 Faithfulness 的区别是：
  - Faithfulness 看“回答中的 claim 是否有依据”
  - Context Recall 看“参考答案中的关键信息是否被检索上下文覆盖”

- **本项目当前实现是启发式近似：**
  - 记 $S_n(reference)$ 为参考答案的 $n$-shingle 集合
  - 记 $S_n(contexts)$ 为所有 contexts 拼接后的 $n$-shingle 集合
$$
\text{ContextRecall}_{\text{project}} = \frac{\left|S_n(reference) \cap S_n(contexts)\right|}{\left|S_n(reference)\right|}
$$

- 代码中的参数同样是：
  - $n = 2$（默认）
  - 文本先做归一化与截断
  - 最多取前 $3$ 条 contexts

- 直观含义：
  - “参考答案中的局部文本模式，有多大比例可以在检索上下文中找到”

## 4. Workflow 场景
### 4.1 `ragas_answer_relevancy`
- 作用：评估 workflow 输出是否与目标 $goal$ 相关。

- 这里将 $goal$ 视作用户输入 $q$，最终输出视作 $answer = a$。

- 计算链路与前面的 Answer Relevancy 完全一致：
$$
\text{AnswerRelevancy}(q, a) = \frac{1}{N} \sum_{i=1}^{N} \cos\left(E(q'_i), E(q)\right)
$$
其中 $q'_i$ 是由 LLM 根据 workflow 输出反向生成的问题或目标描述。

- 因此它衡量的是“workflow 产出是否贴合既定目标”，而不是“步骤是否漂亮”。

### 4.2 `ragas_answer_correctness`
- 作用：评估 workflow 输出是否符合 $expected.reference$

$$
F_{\text{fact}} = \frac{|TP|}{|TP| + 0.5 \times (|FP| + |FN|)}
$$
$$
S_{\text{sem}} = \cos\left(E(a), E(r)\right)
$$
$$
\text{AnswerCorrectness} = 0.75 \cdot F_{\text{fact}} + 0.25 \cdot S_{\text{sem}}
$$

- 本项目同样保留了字符串完全一致时直接返回 $1.0$ 的快捷路径。

## 5. Agent 场景
### 5.1 `ragas_agent_goal_accuracy`
- 作用：评估 agent 的多轮行为是否达成目标。

- 这个指标在 Ragas 文档中的定义是**二值判定**：
  - $1$：工作流最终达成了用户目标
  - $0$：没有达成

- 对于 `WithoutReference` 版本，Ragas 的思路是：
  1. 从整段多轮对话 / tool use 轨迹中推断用户目标 $g$
  2. 再让 LLM 判断最终状态 $T$ 是否满足目标 $g$

抽象公式：
$$
\text{AgentGoalAccuracy}(T) = J(T, g) \in \{0, 1\}
$$
其中：
- $T$：完整的多轮消息轨迹（含必要时的 tool 调用结果）
- $g$：从用户交互中显式或隐式提取的目标
- $J(\cdot)$：LLM judge 的目标达成判定器

- 本项目实现：
  - 优先读取 $trace.agent.messages$
  - 若缺少完整多轮消息，则退化为 $[\text{HumanMessage}(user\_input), \text{AIMessage}(answer)]$
  - 组装 `MultiTurnSample`
  - 调用 `AgentGoalAccuracyWithoutReference()`

- 由于这是二值判定，本项目里通常可以把它理解成：
  - “从多轮过程看，agent 到底有没有把这件事办成”

## 6. 统一补充说明
- 本项目当前并不是所有 `ragas_*` 指标都直接调用原生 ragas 的 LLM 链路。

- 为了降低超时和 token 消耗，以下指标已经改成启发式计算：
  - `ragas_faithfulness`
  - `ragas_context_recall`

- 因此在解释结果时，需要区分：
  - 规则/启发式分数
  - ragas + LLM/embeddings 分数

- 当前项目中启发式分数统一通用模板公式：
$$
\text{Overlap}(A, B) = \frac{\left|S_n(A) \cap S_n(B)\right|}{\left|S_n(A)\right|}
$$
其中 $S_n(\cdot)$ 表示归一化文本后的 $n$-shingle 集合。

- 对应映射：
  - `ragas_faithfulness`：$\text{Overlap}(answer, contexts)$，看回答文本被上下文覆盖比例
  - `ragas_context_recall`：$\text{Overlap}(reference, contexts)$，看参考答案文本被上下文覆盖比例

- 答辩话术建议：
  - `answer_relevancy` / `answer_correctness` / `context_precision` / `agent_goal_accuracy`：完全沿用 Ragas 原生 LLM + Embedding 判定链路
  - `faithfulness` / `context_recall`：为降低调用成本、提升运行稳定性，替换为可量化、可解释的 shingle 重叠启发式公式

---
## 格式兼容说明
1. 全部公式使用标准独立 $$ 块，支持绝大多数 Markdown 编辑器（Typora、VSCode+Markdown All in One、GitBook、Notion、语雀、Obsidian）；
2. 分段函数 `cases`、指示函数、集合交、向量范数、求和、余弦相似度均使用通用 LaTeX 语法，无自定义宏；
3. 变量、下标、文本标注统一使用 `\text{xxx}` 保证中英文混合排版正常；
4. 去掉了原文本中无法渲染的单行 `$$` 内换行文本，全部转为标准数学表达式。
