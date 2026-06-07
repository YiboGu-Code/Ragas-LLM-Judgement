import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ApiError } from "../api/client";
import { deleteDataset, getDataset } from "../api/datasets";
import type { DatasetGetResponse } from "../api/types";
import { addRecentDataset, removeRecentDataset } from "../storage/recent";

export default function DatasetDetailPage() {
  const navigate = useNavigate();
  const { datasetId } = useParams();
  const [loading, setLoading] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [data, setData] = useState<DatasetGetResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function onDelete() {
    if (!datasetId) return;
    if (!window.confirm(`确认删除 dataset：${datasetId}？此操作不可恢复。`))
      return;
    setError(null);
    setDeleting(true);
    try {
      await deleteDataset(datasetId);
      removeRecentDataset(datasetId);
      navigate("/datasets/upload");
    } catch (e) {
      const message = e instanceof ApiError ? e.message : "delete failed";
      setError(message);
    } finally {
      setDeleting(false);
    }
  }

  const load = useCallback(async () => {
    if (!datasetId) {
      setData(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await getDataset(datasetId);
      setData(res);
      addRecentDataset(res.dataset_id);
    } catch (e) {
      const message = e instanceof ApiError ? e.message : "request failed";
      setError(message);
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [datasetId]);

  useEffect(() => {
    const t = window.setTimeout(() => {
      void load();
    }, 0);
    return () => window.clearTimeout(t);
  }, [load]);

  return (
    <div className="page">
      <div className="page-head">
        <h1>Dataset 详情</h1>
        <div className="muted">{datasetId}</div>
      </div>

      <div className="card">
        <div className="row">
          <button
            className="btn primary"
            type="button"
            onClick={load}
            disabled={loading}
          >
            {loading ? "Loading..." : "Refresh"}
          </button>
          <button
            className="btn"
            type="button"
            onClick={() => void onDelete()}
            disabled={deleting || !datasetId}
          >
            {deleting ? "Deleting..." : "Delete"}
          </button>
          {data ? (
            <button
              className="btn"
              type="button"
              onClick={() =>
                navigate(
                  `/runs/create?dataset_id=${encodeURIComponent(data.dataset_id)}&eval_type=${encodeURIComponent(data.eval_type)}`,
                )
              }
            >
              创建 Run
            </button>
          ) : null}
        </div>

        {error ? <pre className="error">{error}</pre> : null}
        {data ? (
          <div className="kv">
            <div className="kv-row">
              <div className="kv-k">dataset_id</div>
              <div className="kv-v">{data.dataset_id}</div>
            </div>
            <div className="kv-row">
              <div className="kv-k">name</div>
              <div className="kv-v">{data.name ?? "-"}</div>
            </div>
            <div className="kv-row">
              <div className="kv-k">eval_type</div>
              <div className="kv-v">{data.eval_type}</div>
            </div>
            <div className="kv-row">
              <div className="kv-k">schema_version</div>
              <div className="kv-v">{data.schema_version}</div>
            </div>
            <div className="kv-row">
              <div className="kv-k">records_count</div>
              <div className="kv-v">{data.records_count}</div>
            </div>
            <div className="kv-row">
              <div className="kv-k">raw_path</div>
              <div className="kv-v">{data.raw_path ?? "-"}</div>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
