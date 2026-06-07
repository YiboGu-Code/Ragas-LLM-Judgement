export default function HelpPage() {
  return (
    <div className="page">
      <div className="page-head">
        <h1>使用说明书</h1>
        <div className="muted">Prompt / RAG / Workflow / Agent：如何选 metrics、每个指标含义与 score 来源</div>
      </div>

      <div className="card">
        <h2>快速开始（核心概念）</h2>
        <ul className="list">
          <li>
            选择 eval_type：必须与数据集 JSONL 每行 record 的 type 一致（prompt/rag/workflow/agent）。
          </li>
          <li>
            dataset-only 模式：sut 为空，后端从每条 record 的 output 或 trace 中读取输出并计算指标。
          </li>
          <li>
            Ragas 指标需要 Provider（例如 ark）。密钥不要在前端填写，后端通过环境变量（如 ARK_API_KEY）注入。
          </li>
          <li>
            items 表格中 metrics 的 status：
            <span className="mono">ok</span> 表示成功算出 score；
            <span className="mono">skipped</span> 表示缺字段/缺 provider；
            <span className="mono">failed</span> 表示执行出错或 ragas 返回空值。
          </li>
        </ul>
      </div>

      <div className="card">
        <h2>Prompt 场景</h2>
        <p className="muted">适用于单轮对话/指令跟随的结果评测。</p>
        <div className="kv">
          <div className="kv-row">
            <div className="kv-k">推荐 metrics</div>
            <div className="kv-v">
              <span className="mono">ragas_answer_relevancy</span>，
              <span className="mono">ragas_answer_correctness</span>
            </div>
          </div>
          <div className="kv-row">
            <div className="kv-k">必备字段</div>
            <div className="kv-v">
              <span className="mono">trace.output.answer</span>（或 output/trace.output 中可提取到 answer/text）
              <br />
              correctness 还需要 <span className="mono">record.expected.reference</span>
            </div>
          </div>
        </div>
        <ul className="list">
          <li>
            <span className="mono">ragas_answer_relevancy</span>：回答与问题/输入的相关性。score 来自后端调用 ragas 计算结果（通常 0~1，越高越相关）。
          </li>
          <li>
            <span className="mono">ragas_answer_correctness</span>：回答与参考答案的一致性/正确性（需要 expected.reference）。score 来自 ragas（通常 0~1，越高越接近参考）。
          </li>
        </ul>
      </div>

      <div className="card">
        <h2>RAG 场景</h2>
        <p className="muted">适用于“检索 contexts + 生成 answer”的评测。</p>
        <div className="kv">
          <div className="kv-row">
            <div className="kv-k">推荐 metrics</div>
            <div className="kv-v">
              <span className="mono">rag_contexts_present</span>，
              <span className="mono">ragas_faithfulness</span>，
              <span className="mono">ragas_answer_relevancy</span>，
              <span className="mono">ragas_context_precision</span>，
              <span className="mono">ragas_context_recall</span>
            </div>
          </div>
          <div className="kv-row">
            <div className="kv-k">必备字段</div>
            <div className="kv-v">
              <span className="mono">trace.retrieval.contexts</span>（contexts 列表）
              <br />
              faithfulness / relevancy 还需要 <span className="mono">trace.output.answer</span>
              <br />
              precision/recall 还需要 <span className="mono">record.expected.reference</span>
            </div>
          </div>
        </div>
        <ul className="list">
          <li>
            <span className="mono">rag_contexts_present</span>：检查是否存在 contexts。后端实现为：contexts 数量 &gt; 0 则 score=1，否则 score=0。
          </li>
          <li>
            <span className="mono">ragas_faithfulness</span>：回答是否“忠实于”给定 contexts（避免幻觉）。score 来自 ragas（通常 0~1）。
          </li>
          <li>
            <span className="mono">ragas_answer_relevancy</span>：回答对问题的相关性。score 来自 ragas（通常 0~1）。
          </li>
          <li>
            <span className="mono">ragas_context_precision</span>：检索到的 contexts 中有多少与参考答案相关（越“精准”越高）。
          </li>
          <li>
            <span className="mono">ragas_context_recall</span>：检索到的 contexts 覆盖了多少参考答案所需信息（越“全面”越高）。
          </li>
        </ul>
      </div>

      <div className="card">
        <h2>Workflow 场景</h2>
        <p className="muted">适用于“给定 goal + inputs，产出 answer”的工作流评测。</p>
        <div className="kv">
          <div className="kv-row">
            <div className="kv-k">推荐 metrics</div>
            <div className="kv-v">
              <span className="mono">ragas_answer_relevancy</span>，
              <span className="mono">ragas_answer_correctness</span>
            </div>
          </div>
          <div className="kv-row">
            <div className="kv-k">必备字段</div>
            <div className="kv-v">
              <span className="mono">trace.output.answer</span>
              <br />
              correctness 还需要 <span className="mono">record.expected.reference</span>
            </div>
          </div>
        </div>
        <ul className="list">
          <li>
            score 由后端使用 ragas 对单条样本计算得到（通常 0~1）。前端展示的是后端返回的 score。
          </li>
        </ul>
      </div>

      <div className="card">
        <h2>Agent 场景</h2>
        <p className="muted">适用于多轮对话/工具调用的 agent 轨迹评测。</p>
        <div className="kv">
          <div className="kv-row">
            <div className="kv-k">推荐 metrics</div>
            <div className="kv-v">
              <span className="mono">ragas_agent_goal_accuracy</span>
            </div>
          </div>
          <div className="kv-row">
            <div className="kv-k">必备字段</div>
            <div className="kv-v">
              <span className="mono">trace.agent.messages</span>（数组，包含 role/content）
            </div>
          </div>
        </div>
        <ul className="list">
          <li>
            <span className="mono">ragas_agent_goal_accuracy</span>：评估 agent 的多轮行为是否达成目标（不需要 reference）。score 来自后端调用 ragas 计算（通常 0~1）。
          </li>
        </ul>
      </div>

      <div className="card">
        <h2>score 是如何计算的？（以服务端为准）</h2>
        <ul className="list">
          <li>
            基础指标 <span className="mono">rag_contexts_present</span>：服务端直接根据 contexts 是否存在/数量计算（0 或 1）。
          </li>
          <li>
            所有 <span className="mono">ragas_*</span>：服务端将 record/trace 组装成 ragas 的 sample，再调用 ragas 的 aevaluate 得到分数。前端不在本地重复计算，只展示返回值。
          </li>
          <li>
            当缺字段或缺 provider 时，服务端会返回 <span className="mono">skipped</span> 并在 details.reason 给出原因（前端会在结果里展示该 reason）。
          </li>
        </ul>
      </div>
    </div>
  )
}

