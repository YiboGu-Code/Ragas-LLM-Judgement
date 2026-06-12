import { apiFetch } from "./client";
import type {
  DatasetCreateResponse,
  DatasetGetResponse,
  DatasetListResponse,
  EvalType,
} from "./types";

export async function uploadDataset(args: {
  evalType: EvalType;
  file: File;
  name?: string;
}): Promise<DatasetCreateResponse> {
  const form = new FormData();
  form.append("eval_type", args.evalType);
  form.append("file", args.file);
  if (args.name && args.name.trim().length > 0) {
    form.append("name", args.name.trim());
  }

  return apiFetch<DatasetCreateResponse>("/datasets", {
    method: "POST",
    body: form,
    isFormData: true,
  });
}

export async function getDataset(
  datasetId: string,
): Promise<DatasetGetResponse> {
  return apiFetch<DatasetGetResponse>(
    `/datasets/${encodeURIComponent(datasetId)}`,
  );
}

export async function deleteDataset(datasetId: string): Promise<void> {
  await apiFetch<unknown>(`/datasets/${encodeURIComponent(datasetId)}`, {
    method: "DELETE",
  });
}

export async function listDatasets(): Promise<DatasetListResponse> {
  return apiFetch<DatasetListResponse>("/datasets");
}
