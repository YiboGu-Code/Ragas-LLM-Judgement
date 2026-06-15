import { useCallback, useEffect, useMemo, useState } from "react";
import {
  bulkDeleteDatasets,
  deleteDataset,
  listDatasets,
  uploadDataset,
} from "../api/datasets";
import type {
  BulkDeleteResponse,
  DatasetCreateResponse,
  DatasetListResponse,
  EvalType,
} from "../api/types";
import { ApiError } from "../api/client";
import { addRecentDataset } from "../storage/recent";
import { useNavigate } from "react-router-dom";
import { DEMO_DATASETS } from "../utils/demoDatasets";

const EVAL_TYPES: EvalType[] = ["prompt", "rag", "workflow", "agent"];

export default function DatasetsUploadPage() {
  const navigate = useNavigate();
  const [evalType, setEvalType] = useState<EvalType>("prompt");
  const [name, setName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<DatasetCreateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [shared, setShared] = useState<DatasetListResponse | null>(null);
  const [loadingShared, setLoadingShared] = useState(false);
  const [sharedError, setSharedError] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [deletingShared, setDeletingShared] = useState(false);
  const [bulkDeleteResult, setBulkDeleteResult] =
    useState<BulkDeleteResponse | null>(null);

  const loadShared = useCallback(async () => {
    setLoadingShared(true);
    setSharedError(null);
    try {
      const res = await listDatasets();
      setShared(res);
    } catch (e) {
      const message = e instanceof ApiError ? e.message : "request failed";
      setSharedError(message);
      setShared(null);
    } finally {
      setLoadingShared(false);
    }
  }, []);

  useEffect(() => {
    void loadShared();
  }, [loadShared]);

  const selectedSet = useMemo(() => new Set(selectedIds), [selectedIds]);
  const allSelected = useMemo(() => {
    if (!shared || shared.items.length === 0) return false;
    return shared.items.every((x) => selectedSet.has(x.dataset_id));
  }, [selectedSet, shared]);

  function toggleSelected(id: string) {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );
  }

  function toggleAll() {
    if (!shared) return;
    if (allSelected) {
      setSelectedIds([]);
      return;
    }
    setSelectedIds(shared.items.map((x) => x.dataset_id));
  }

  async function onDeleteOne(datasetId: string) {
    if (!window.confirm(`确认删除 dataset：${datasetId}？此操作不可恢复。`))
      return;
    setSharedError(null);
    setBulkDeleteResult(null);
    setDeletingShared(true);
    try {
      await deleteDataset(datasetId);
      setSelectedIds((prev) => prev.filter((x) => x !== datasetId));
      await loadShared();
    } catch (e) {
      const message = e instanceof ApiError ? e.message : "delete failed";
      setSharedError(message);
    } finally {
      setDeletingShared(false);
    }
  }

  async function onBulkDelete() {
    const ids = selectedIds;
    if (ids.length === 0) return;
    if (
      !window.confirm(`确认批量删除 ${ids.length} 个 dataset？此操作不可恢复。`)
    )
      return;
    setSharedError(null);
    setBulkDeleteResult(null);
    setDeletingShared(true);
    try {
      const res = await bulkDeleteDatasets(ids);
      setBulkDeleteResult(res);
      const deleted = new Set(
        res.results.filter((x) => x.status === "deleted").map((x) => x.id),
      );
      setSelectedIds((prev) => prev.filter((x) => !deleted.has(x)));
      await loadShared();
    } catch (e) {
      const message = e instanceof ApiError ? e.message : "bulk delete failed";
      setSharedError(message);
    } finally {
      setDeletingShared(false);
    }
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) {
      setError("请选择一个 JSONL 文件");
      return;
    }
    setSubmitting(true);
    setError(null);
    setResult(null);
    try {
      const res = await uploadDataset({ evalType, file, name });
      setResult(res);
      addRecentDataset(res.dataset_id);
      navigate(`/datasets/${encodeURIComponent(res.dataset_id)}`);
    } catch (e2) {
      const message = e2 instanceof ApiError ? e2.message : "upload failed";
      setError(message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="page">
      <div className="page-head">
        <h1>Datasets</h1>
        <div className="muted">
          上传 JSONL 数据集（dataset-only 模式推荐每条包含 output 或 trace）
        </div>
      </div>

      <div className="card">
        <h2>上传</h2>
        <form onSubmit={onSubmit} className="form">
          <label className="field">
            <div className="label">eval_type</div>
            <select
              className="input"
              value={evalType}
              onChange={(e) => setEvalType(e.target.value as EvalType)}
            >
              {EVAL_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </label>

          <label className="field">
            <div className="label">name（可选）</div>
            <input
              className="input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="my dataset"
            />
          </label>

          <label className="field">
            <div className="label">file（.jsonl）</div>
            <input
              className="input"
              type="file"
              accept=".jsonl,application/jsonl,text/plain"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </label>

          <div className="row">
            <button className="btn primary" type="submit" disabled={submitting}>
              {submitting ? "Uploading..." : "Upload"}
            </button>
            <div className="muted">
              接口：POST /datasets（multipart/form-data）
            </div>
          </div>
        </form>

        {error ? <pre className="error">{error}</pre> : null}
        {result ? (
          <pre className="code">{JSON.stringify(result, null, 2)}</pre>
        ) : null}
      </div>

      <div className="card">
        <h2>Demo 数据集下载</h2>
        <div className="muted">下载后可直接上传试跑（.jsonl）</div>
        <div className="row" style={{ marginTop: 12 }}>
          {DEMO_DATASETS.map((x) => (
            <a key={x.key} className="btn" href={x.href} download={x.filename}>
              下载 {x.label}
            </a>
          ))}
        </div>
      </div>

      <div className="card">
        <div className="row">
          <h2 style={{ margin: 0 }}>共享 Datasets</h2>
          <button
            className="btn"
            type="button"
            onClick={() => void loadShared()}
            disabled={loadingShared}
          >
            {loadingShared ? "Loading..." : "Refresh"}
          </button>
          <button
            className="btn"
            type="button"
            onClick={() => void onBulkDelete()}
            disabled={deletingShared || selectedIds.length === 0}
          >
            {deletingShared
              ? "Deleting..."
              : `批量删除（${selectedIds.length}）`}
          </button>
        </div>
        <div className="muted">所有访问者可见（来自后端数据库）</div>
        {sharedError ? <pre className="error">{sharedError}</pre> : null}
        {bulkDeleteResult ? (
          <pre className="code">
            {JSON.stringify(bulkDeleteResult, null, 2)}
          </pre>
        ) : null}
        {shared ? (
          <div className="table-wrap" style={{ marginTop: 12 }}>
            <table className="table">
              <thead>
                <tr>
                  <th>
                    <input
                      type="checkbox"
                      checked={allSelected}
                      onChange={toggleAll}
                    />
                  </th>
                  <th>name</th>
                  <th>eval_type</th>
                  <th>records</th>
                  <th>dataset_id</th>
                  <th>actions</th>
                </tr>
              </thead>
              <tbody>
                {shared.items.map((it) => (
                  <tr key={it.dataset_id}>
                    <td>
                      <input
                        type="checkbox"
                        checked={selectedSet.has(it.dataset_id)}
                        onChange={() => toggleSelected(it.dataset_id)}
                      />
                    </td>
                    <td>{it.name ?? "-"}</td>
                    <td>{it.eval_type}</td>
                    <td>{it.records_count}</td>
                    <td>{it.dataset_id}</td>
                    <td style={{ textAlign: "right" }}>
                      <button
                        className="btn"
                        type="button"
                        onClick={() =>
                          navigate(
                            `/datasets/${encodeURIComponent(it.dataset_id)}`,
                          )
                        }
                        disabled={deletingShared}
                      >
                        打开
                      </button>
                      <button
                        className="btn"
                        type="button"
                        onClick={() => void onDeleteOne(it.dataset_id)}
                        disabled={deletingShared}
                      >
                        删除
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </div>

      <div className="card">
        <h2>提示</h2>
        <ul className="list">
          <li>每行必须是 JSON 对象；type 必须与 eval_type 一致</li>
          <li>
            dataset-only 模式：每条 record 至少包含 output 或 trace（否则该条会
            failed）
          </li>
          <li>后端校验失败会返回 422，detail 通常包含行号信息</li>
        </ul>
      </div>
    </div>
  );
}
