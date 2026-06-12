import { apiFetch, apiFetchBlob } from "./client";
import type {
  RunCreateRequest,
  RunCreateResponse,
  RunGetResponse,
  RunItemsResponse,
  RunListResponse,
} from "./types";

export async function createRun(
  payload: RunCreateRequest,
): Promise<RunCreateResponse> {
  return apiFetch<RunCreateResponse>("/runs", {
    method: "POST",
    body: payload,
  });
}

export async function startRun(runId: string): Promise<RunGetResponse> {
  return apiFetch<RunGetResponse>(`/runs/${encodeURIComponent(runId)}/start`, {
    method: "POST",
  });
}

export async function cancelRun(runId: string): Promise<RunGetResponse> {
  return apiFetch<RunGetResponse>(`/runs/${encodeURIComponent(runId)}/cancel`, {
    method: "POST",
  });
}

export async function getRun(runId: string): Promise<RunGetResponse> {
  return apiFetch<RunGetResponse>(`/runs/${encodeURIComponent(runId)}`);
}

export async function getRunItems(runId: string): Promise<RunItemsResponse> {
  return apiFetch<RunItemsResponse>(`/runs/${encodeURIComponent(runId)}/items`);
}

export function exportRunUrl(
  runId: string,
  format: "csv" | "json" | "jsonl",
): string {
  return `/api/runs/${encodeURIComponent(runId)}/export?format=${encodeURIComponent(format)}`;
}

export async function exportRunBlob(
  runId: string,
  format: "csv" | "json" | "jsonl",
): Promise<Blob> {
  return apiFetchBlob(
    `/runs/${encodeURIComponent(runId)}/export?format=${encodeURIComponent(format)}`,
  );
}

export async function deleteRun(runId: string): Promise<void> {
  await apiFetch<string>(`/runs/${encodeURIComponent(runId)}`, {
    method: "DELETE",
  });
}

export async function listRuns(): Promise<RunListResponse> {
  return apiFetch<RunListResponse>("/runs");
}
