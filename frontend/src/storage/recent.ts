const KEY_DATASETS = "llm_eval_recent_datasets";
const KEY_RUNS = "llm_eval_recent_runs";

function safeParseArray(value: string | null): string[] {
  if (!value) return [];
  try {
    const parsed = JSON.parse(value) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((x) => typeof x === "string") as string[];
  } catch {
    return [];
  }
}

function writeArray(key: string, values: string[]) {
  localStorage.setItem(key, JSON.stringify(values));
}

function uniqRecentInsert(values: string[], id: string, max: number): string[] {
  const normalized = id.trim();
  if (!normalized) return values;
  const next = [normalized, ...values.filter((x) => x !== normalized)];
  return next.slice(0, max);
}

export function getRecentDatasets(): string[] {
  return safeParseArray(localStorage.getItem(KEY_DATASETS));
}

export function addRecentDataset(datasetId: string) {
  const current = getRecentDatasets();
  const next = uniqRecentInsert(current, datasetId, 12);
  writeArray(KEY_DATASETS, next);
}

export function removeRecentDataset(datasetId: string) {
  const normalized = datasetId.trim();
  if (!normalized) return;
  const current = getRecentDatasets();
  const next = current.filter((x) => x !== normalized);
  writeArray(KEY_DATASETS, next);
}

export function getRecentRuns(): string[] {
  return safeParseArray(localStorage.getItem(KEY_RUNS));
}

export function addRecentRun(runId: string) {
  const current = getRecentRuns();
  const next = uniqRecentInsert(current, runId, 12);
  writeArray(KEY_RUNS, next);
}

export function removeRecentRun(runId: string) {
  const normalized = runId.trim();
  if (!normalized) return;
  const current = getRecentRuns();
  const next = current.filter((x) => x !== normalized);
  writeArray(KEY_RUNS, next);
}
