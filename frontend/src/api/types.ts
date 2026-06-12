export type EvalType = "prompt" | "rag" | "workflow" | "agent";

export type DatasetCreateResponse = {
  dataset_id: string;
  records_count: number;
  eval_type: EvalType;
  schema_version: string;
};

export type DatasetGetResponse = {
  dataset_id: string;
  name: string | null;
  eval_type: EvalType;
  schema_version: string;
  records_count: number;
  raw_path: string | null;
};

export type DatasetListItem = {
  dataset_id: string;
  name: string | null;
  eval_type: EvalType;
  schema_version: string;
  records_count: number;
  created_at: string;
};

export type DatasetListResponse = {
  items: DatasetListItem[];
};

export type MetricName =
  | "rag_contexts_present"
  | "ragas_faithfulness"
  | "ragas_answer_relevancy"
  | "ragas_context_precision"
  | "ragas_context_recall"
  | "ragas_answer_correctness"
  | "ragas_agent_goal_accuracy";

export type ProviderRef =
  | { provider_name: "none"; config: Record<string, unknown> }
  | {
      provider_name: "ark";
      config: { base_url: string; model: string; embedding_model?: string };
    };

export type RunCreateRequest = {
  dataset_id: string;
  eval_type: EvalType;
  sut?: null;
  metrics: Array<{
    metric_name: MetricName;
    metric_config: Record<string, unknown>;
  }>;
  provider_ref: ProviderRef;
  execution: {
    max_concurrency: number;
    timeout_seconds: number;
    save_artifacts: boolean;
    artifact_redaction: string;
  };
};

export type RunCreateResponse = { run_id: string; status: string };

export type RunGetResponse = {
  run_id: string;
  status:
    | "created"
    | "queued"
    | "running"
    | "succeeded"
    | "failed"
    | "canceled";
  progress: { total: number; completed: number; failed: number };
};

export type RunListItem = {
  run_id: string;
  dataset_id: string;
  eval_type: EvalType;
  status: string;
  progress: { total: number; completed: number; failed: number };
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
};

export type RunListResponse = {
  items: RunListItem[];
};

export type MetricResult = {
  name: string;
  status: "ok" | "skipped" | "failed";
  score: number | null;
  details: Record<string, unknown> | null;
  version: string | null;
};

export type RunItem = {
  record_id: string;
  status: "succeeded" | "failed";
  error: { type: string; message: string } | null;
  output: unknown;
  trace_ref: string | null;
  metrics: MetricResult[];
  duration_ms: number | null;
};

export type RunItemsResponse = {
  items: RunItem[];
};
