import { useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import type {
  EvalType,
  MetricName,
  ProviderRef,
  RunCreateRequest,
} from "../api/types";
import { createRun } from "../api/runs";
import { ApiError } from "../api/client";
import { addRecentRun } from "../storage/recent";

const EVAL_TYPES: EvalType[] = ["prompt", "rag", "workflow", "agent"];

type MetricOption = {
  name: MetricName;
  label: string;
  group: "basic" | "ragas";
  evalTypes: EvalType[];
  requiresProvider: boolean;
  requiresEmbedding: boolean;
  hint: string;
};

const METRICS: MetricOption[] = [
  {
    name: "rag_contexts_present",
    label: "rag_contexts_present",
    group: "basic",
    evalTypes: ["rag"],
    requiresProvider: false,
    requiresEmbedding: false,
    hint: "需要 trace.retrieval.contexts",
  },
  {
    name: "ragas_faithfulness",
    label: "ragas_faithfulness",
    group: "ragas",
    evalTypes: ["rag"],
    requiresProvider: true,
    requiresEmbedding: false,
    hint: "需要 trace.output.answer + trace.retrieval.contexts + provider",
  },
  {
    name: "ragas_answer_relevancy",
    label: "ragas_answer_relevancy",
    group: "ragas",
    evalTypes: ["prompt", "rag", "workflow"],
    requiresProvider: true,
    requiresEmbedding: true,
    hint: "需要 trace.output.answer + provider（embedding_model 推荐配置）",
  },
  {
    name: "ragas_context_precision",
    label: "ragas_context_precision",
    group: "ragas",
    evalTypes: ["rag"],
    requiresProvider: true,
    requiresEmbedding: true,
    hint: "需要 trace.retrieval.contexts + expected.reference + provider（embedding_model 推荐配置）",
  },
  {
    name: "ragas_context_recall",
    label: "ragas_context_recall",
    group: "ragas",
    evalTypes: ["rag"],
    requiresProvider: true,
    requiresEmbedding: true,
    hint: "需要 trace.retrieval.contexts + expected.reference + provider（embedding_model 推荐配置）",
  },
  {
    name: "ragas_answer_correctness",
    label: "ragas_answer_correctness",
    group: "ragas",
    evalTypes: ["prompt", "rag", "workflow"],
    requiresProvider: true,
    requiresEmbedding: true,
    hint: "需要 trace.output.answer + expected.reference + provider（embedding_model 推荐配置）",
  },
  {
    name: "ragas_agent_goal_accuracy",
    label: "ragas_agent_goal_accuracy",
    group: "ragas",
    evalTypes: ["agent"],
    requiresProvider: true,
    requiresEmbedding: false,
    hint: "需要 trace.agent.messages + provider",
  },
];

function toInt(value: string, fallback: number): number {
  const n = Number(value);
  return Number.isFinite(n) && n > 0 ? Math.floor(n) : fallback;
}

function defaultMetricsForEvalType(evalType: EvalType): MetricName[] {
  switch (evalType) {
    case "prompt":
      return ["ragas_answer_relevancy", "ragas_answer_correctness"];
    case "workflow":
      return ["ragas_answer_relevancy", "ragas_answer_correctness"];
    case "rag":
      return [
        "rag_contexts_present",
        "ragas_faithfulness",
        "ragas_answer_relevancy",
        "ragas_context_precision",
        "ragas_context_recall",
      ];
    case "agent":
      return ["ragas_agent_goal_accuracy"];
  }
}

function anyRagasSelected(selected: MetricName[]): boolean {
  return selected.some((m) => m.startsWith("ragas_"));
}

function requiresEmbeddingModel(selected: MetricName[]): boolean {
  const set = new Set(selected);
  return (
    set.has("ragas_answer_relevancy") ||
    set.has("ragas_answer_correctness") ||
    set.has("ragas_context_precision") ||
    set.has("ragas_context_recall")
  );
}

export default function RunCreatePage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();

  const prefillDatasetId = params.get("dataset_id") ?? "";
  const prefillEvalType = (params.get("eval_type") as EvalType | null) ?? null;

  const [datasetId, setDatasetId] = useState(prefillDatasetId);
  const [evalType, setEvalType] = useState<EvalType>(
    prefillEvalType && EVAL_TYPES.includes(prefillEvalType)
      ? prefillEvalType
      : "prompt",
  );
  const [selectedMetrics, setSelectedMetrics] = useState<MetricName[]>(
    defaultMetricsForEvalType(
      prefillEvalType && EVAL_TYPES.includes(prefillEvalType)
        ? prefillEvalType
        : "prompt",
    ),
  );

  const [providerName, setProviderName] = useState<"none" | "ark">("ark");
  const [arkBaseUrl, setArkBaseUrl] = useState(
    "https://ark.cn-beijing.volces.com/api/v3",
  );
  const [arkModel, setArkModel] = useState("deepseek-v3-2-251201");
  const [arkEmbeddingModel, setArkEmbeddingModel] = useState(
    "doubao-embedding-vision-251215",
  );

  const [maxConcurrency, setMaxConcurrency] = useState("2");
  const [timeoutSeconds, setTimeoutSeconds] = useState("90");
  const [saveArtifacts, setSaveArtifacts] = useState(true);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const metricOptions = useMemo(
    () => METRICS.filter((m) => m.evalTypes.includes(evalType)),
    [evalType],
  );

  const ragasSelected = anyRagasSelected(selectedMetrics);
  const embeddingRequired = requiresEmbeddingModel(selectedMetrics);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const id = datasetId.trim();
    if (!id) {
      setError("dataset_id 不能为空");
      return;
    }
    if (selectedMetrics.length === 0) {
      setError("请至少选择一个 metric");
      return;
    }

    setSubmitting(true);
    setError(null);

    let provider_ref: ProviderRef = { provider_name: "none", config: {} };
    if (providerName === "ark") {
      const baseUrl = arkBaseUrl.trim();
      const model = arkModel.trim();
      const embeddingModel = arkEmbeddingModel.trim();
      if (!baseUrl) {
        setSubmitting(false);
        setError("ark.base_url 不能为空");
        return;
      }
      if (!model) {
        setSubmitting(false);
        setError("ark.model 不能为空");
        return;
      }
      if (embeddingRequired && !embeddingModel) {
        setSubmitting(false);
        setError("已选择需要 embedding 的指标，请填写 ark.embedding_model");
        return;
      }
      provider_ref = {
        provider_name: "ark",
        config: embeddingModel
          ? { base_url: baseUrl, model, embedding_model: embeddingModel }
          : { base_url: baseUrl, model },
      };
    }

    const payload: RunCreateRequest = {
      dataset_id: id,
      eval_type: evalType,
      sut: null,
      metrics: selectedMetrics.map((m) => ({
        metric_name: m,
        metric_config: {},
      })),
      provider_ref,
      execution: {
        max_concurrency: toInt(maxConcurrency, 2),
        timeout_seconds: toInt(timeoutSeconds, 90),
        save_artifacts: saveArtifacts,
        artifact_redaction: "default_v1",
      },
    };

    try {
      const res = await createRun(payload);
      addRecentRun(res.run_id);
      navigate(`/runs/${encodeURIComponent(res.run_id)}`);
    } catch (e2) {
      const message = e2 instanceof ApiError ? e2.message : "create run failed";
      setError(message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="page">
      <div className="page-head">
        <h1>Runs</h1>
        <div className="muted">
          dataset-only：sut = null（输出从 dataset 的 output/trace 读取）
        </div>
      </div>

      <div className="card">
        <h2>创建 Run</h2>
        <form onSubmit={onSubmit} className="form">
          <label className="field">
            <div className="label">dataset_id</div>
            <input
              className="input"
              value={datasetId}
              onChange={(e) => setDatasetId(e.target.value)}
              placeholder="uuid..."
            />
          </label>

          <label className="field">
            <div className="label">eval_type</div>
            <select
              className="input"
              value={evalType}
              onChange={(e) => {
                const nextEvalType = e.target.value as EvalType;
                setEvalType(nextEvalType);
                const nextDefaults = defaultMetricsForEvalType(nextEvalType);
                setSelectedMetrics(nextDefaults);
                if (anyRagasSelected(nextDefaults) && providerName === "none") {
                  setProviderName("ark");
                }
              }}
            >
              {EVAL_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </label>

          <div className="field">
            <div className="label">metrics</div>
            <div className="checkboxes">
              <div className="subhead">基础</div>
              {metricOptions
                .filter((m) => m.group === "basic")
                .map((m) => {
                  const checked = selectedMetrics.includes(m.name);
                  return (
                    <label key={m.name} className="checkbox">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={(e) => {
                          const nextChecked = e.target.checked;
                          const next = nextChecked
                            ? ([
                                ...new Set([...selectedMetrics, m.name]),
                              ] as MetricName[])
                            : selectedMetrics.filter((x) => x !== m.name);
                          setSelectedMetrics(next);
                        }}
                      />
                      <span className="mono">{m.label}</span>
                      <span className="muted">{m.hint}</span>
                    </label>
                  );
                })}

              <div className="subhead" style={{ marginTop: 8 }}>
                Ragas（需要 provider）
              </div>
              {metricOptions
                .filter((m) => m.group === "ragas")
                .map((m) => {
                  const checked = selectedMetrics.includes(m.name);
                  return (
                    <label key={m.name} className="checkbox">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={(e) => {
                          const nextChecked = e.target.checked;
                          const next = nextChecked
                            ? ([
                                ...new Set([...selectedMetrics, m.name]),
                              ] as MetricName[])
                            : selectedMetrics.filter((x) => x !== m.name);
                          setSelectedMetrics(next);
                          if (
                            anyRagasSelected(next) &&
                            providerName === "none"
                          ) {
                            setProviderName("ark");
                          }
                        }}
                      />
                      <span className="mono">{m.label}</span>
                      <span className="muted">{m.hint}</span>
                    </label>
                  );
                })}
            </div>
          </div>

          <div className="card subtle">
            <div className="row">
              <div style={{ fontWeight: 650 }}>Provider</div>
              <div className="muted">
                密钥不要在这里填，后端通过环境变量注入（例如 ARK_API_KEY）
              </div>
            </div>

            <div className="grid-2" style={{ marginTop: 10 }}>
              <label className="field">
                <div className="label">provider_name</div>
                <select
                  className="input"
                  value={providerName}
                  onChange={(e) =>
                    setProviderName(e.target.value as "none" | "ark")
                  }
                >
                  <option value="ark">ark</option>
                  <option value="none">none</option>
                </select>
              </label>
              <div className="field">
                <div className="label">需要 provider？</div>
                <div className="pill">
                  {ragasSelected ? "是（已选 Ragas 指标）" : "否（仅基础指标）"}
                </div>
              </div>
            </div>

            {providerName === "ark" ? (
              <div className="grid-2" style={{ marginTop: 10 }}>
                <label className="field">
                  <div className="label">base_url</div>
                  <input
                    className="input"
                    value={arkBaseUrl}
                    onChange={(e) => setArkBaseUrl(e.target.value)}
                  />
                </label>
                <label className="field">
                  <div className="label">model</div>
                  <input
                    className="input"
                    value={arkModel}
                    onChange={(e) => setArkModel(e.target.value)}
                  />
                </label>
                <label className="field" style={{ gridColumn: "1 / -1" }}>
                  <div className="label">
                    embedding_model{embeddingRequired ? "（必填）" : "（可选）"}
                  </div>
                  <input
                    className="input"
                    value={arkEmbeddingModel}
                    onChange={(e) => setArkEmbeddingModel(e.target.value)}
                  />
                </label>
              </div>
            ) : (
              <div className="muted" style={{ marginTop: 10 }}>
                选择 none 时，所有 Ragas 指标会被 skipped（missing provider）
              </div>
            )}
          </div>

          <div className="grid-2">
            <label className="field">
              <div className="label">max_concurrency</div>
              <input
                className="input"
                value={maxConcurrency}
                onChange={(e) => setMaxConcurrency(e.target.value)}
              />
            </label>
            <label className="field">
              <div className="label">timeout_seconds</div>
              <input
                className="input"
                value={timeoutSeconds}
                onChange={(e) => setTimeoutSeconds(e.target.value)}
              />
            </label>
          </div>

          <label className="checkbox">
            <input
              type="checkbox"
              checked={saveArtifacts}
              onChange={(e) => setSaveArtifacts(e.target.checked)}
            />
            <span>save_artifacts（trace 落盘到 artifacts/）</span>
          </label>

          <div className="row">
            <button className="btn primary" type="submit" disabled={submitting}>
              {submitting ? "Creating..." : "Create"}
            </button>
            <div className="muted">接口：POST /runs</div>
          </div>
        </form>

        {error ? <pre className="error">{error}</pre> : null}
      </div>
    </div>
  );
}
