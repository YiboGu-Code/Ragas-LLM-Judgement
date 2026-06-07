import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ApiError } from "../api/client";
import {
  cancelRun,
  deleteRun,
  getRun,
  getRunItems,
  exportRunBlob,
  startRun,
} from "../api/runs";
import type { RunGetResponse, RunItemsResponse } from "../api/types";
import { addRecentRun, removeRecentRun } from "../storage/recent";
import { buildExportFilename } from "../utils/exportFilename";
import { downloadBlob } from "../utils/downloadBlob";

function formatMs(ms: number | null): string {
  if (ms === null) return "-";
  if (ms < 1000) return `${ms}ms`;
  const s = ms / 1000;
  return `${s.toFixed(2)}s`;
}

function renderError(value: unknown): string {
  if (typeof value === "string") return value;
  if (value && typeof value === "object") {
    const anyValue = value as Record<string, unknown>;
    const message =
      typeof anyValue.message === "string" ? anyValue.message : "";
    const type = typeof anyValue.type === "string" ? anyValue.type : "";
    return [type, message].filter(Boolean).join(": ");
  }
  return "";
}

function metricReason(details: unknown): string {
  if (!details || typeof details !== "object") return "";
  const anyDetails = details as Record<string, unknown>;
  return typeof anyDetails.reason === "string" ? anyDetails.reason : "";
}

export default function RunDetailPage() {
  const navigate = useNavigate();
  const { runId } = useParams();
  const [run, setRun] = useState<RunGetResponse | null>(null);
  const [items, setItems] = useState<RunItemsResponse | null>(null);
  const [loadingRun, setLoadingRun] = useState(false);
  const [loadingItems, setLoadingItems] = useState(false);
  const [exporting, setExporting] = useState<null | "csv" | "json" | "jsonl">(
    null,
  );
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canStart = run?.status === "created" || run?.status === "queued";
  const canCancel = run?.status === "running" || run?.status === "queued";
  const canDelete = run
    ? run.status !== "running" && run.status !== "queued"
    : true;
  const shouldPoll = run?.status === "running" || run?.status === "queued";

  const exportReady = useMemo(() => Boolean(runId), [runId]);

  async function onExport(format: "csv" | "json" | "jsonl") {
    if (!runId) return;
    setError(null);
    setExporting(format);
    try {
      const blob = await exportRunBlob(runId, format);
      const filename = buildExportFilename(runId, format);
      downloadBlob(filename, blob);
    } catch (e) {
      const message = e instanceof ApiError ? e.message : "export failed";
      setError(message);
    } finally {
      setExporting(null);
    }
  }

  async function onDelete() {
    if (!runId) return;
    if (!window.confirm(`确认删除 run：${runId}？此操作不可恢复。`)) return;
    setError(null);
    setDeleting(true);
    try {
      await deleteRun(runId);
      removeRecentRun(runId);
      navigate("/runs/create");
    } catch (e) {
      const message = e instanceof ApiError ? e.message : "delete failed";
      setError(message);
    } finally {
      setDeleting(false);
    }
  }

  const loadRun = useCallback(async () => {
    if (!runId) {
      setRun(null);
      return;
    }
    setLoadingRun(true);
    setError(null);
    try {
      const res = await getRun(runId);
      setRun(res);
      addRecentRun(res.run_id);
    } catch (e) {
      const message = e instanceof ApiError ? e.message : "request failed";
      setError(message);
      setRun(null);
    } finally {
      setLoadingRun(false);
    }
  }, [runId]);

  const loadItems = useCallback(async () => {
    if (!runId) {
      setItems(null);
      return;
    }
    setLoadingItems(true);
    setError(null);
    try {
      const res = await getRunItems(runId);
      setItems(res);
    } catch (e) {
      const message = e instanceof ApiError ? e.message : "request failed";
      setError(message);
      setItems(null);
    } finally {
      setLoadingItems(false);
    }
  }, [runId]);

  async function onStart() {
    if (!runId) return;
    setError(null);
    try {
      const res = await startRun(runId);
      setRun(res);
    } catch (e) {
      const message = e instanceof ApiError ? e.message : "start failed";
      setError(message);
    }
  }

  async function onCancel() {
    if (!runId) return;
    setError(null);
    try {
      const res = await cancelRun(runId);
      setRun(res);
    } catch (e) {
      const message = e instanceof ApiError ? e.message : "cancel failed";
      setError(message);
    }
  }

  useEffect(() => {
    const t = window.setTimeout(() => {
      void loadRun();
      setItems(null);
    }, 0);
    return () => window.clearTimeout(t);
  }, [loadRun, runId]);

  useEffect(() => {
    if (!shouldPoll) return;
    const t = window.setInterval(() => {
      void loadRun();
    }, 1500);
    return () => window.clearInterval(t);
  }, [shouldPoll, loadRun, runId]);

  useEffect(() => {
    if (
      run?.status === "succeeded" ||
      run?.status === "failed" ||
      run?.status === "canceled"
    ) {
      const t = window.setTimeout(() => {
        void loadItems();
      }, 0);
      return () => window.clearTimeout(t);
    }
  }, [run?.status, loadItems]);

  return (
    <div className="page">
      <div className="page-head">
        <h1>Run 详情</h1>
        <div className="muted">{runId}</div>
      </div>

      <div className="card">
        <div className="row">
          <button
            className="btn primary"
            type="button"
            onClick={loadRun}
            disabled={loadingRun}
          >
            {loadingRun ? "Loading..." : "Refresh"}
          </button>
          <button
            className="btn"
            type="button"
            onClick={onStart}
            disabled={!canStart}
          >
            Start
          </button>
          <button
            className="btn"
            type="button"
            onClick={onCancel}
            disabled={!canCancel}
          >
            Cancel
          </button>
          <button
            className="btn"
            type="button"
            onClick={() => void onDelete()}
            disabled={deleting || exporting !== null || !runId || !canDelete}
          >
            {deleting ? "Deleting..." : "Delete"}
          </button>
          <button
            className="btn"
            type="button"
            onClick={loadItems}
            disabled={loadingItems || !runId}
          >
            {loadingItems ? "Loading items..." : "Load items"}
          </button>
          {exportReady ? (
            <div className="row" style={{ marginLeft: "auto" }}>
              <button
                className="btn"
                type="button"
                onClick={() => void onExport("csv")}
                disabled={exporting !== null}
              >
                {exporting === "csv" ? "Exporting..." : "Export CSV"}
              </button>
              <button
                className="btn"
                type="button"
                onClick={() => void onExport("json")}
                disabled={exporting !== null}
              >
                {exporting === "json" ? "Exporting..." : "Export JSON"}
              </button>
              <button
                className="btn"
                type="button"
                onClick={() => void onExport("jsonl")}
                disabled={exporting !== null}
              >
                {exporting === "jsonl" ? "Exporting..." : "Export JSONL"}
              </button>
            </div>
          ) : null}
        </div>

        {error ? <pre className="error">{error}</pre> : null}

        {run ? (
          <div className="kv">
            <div className="kv-row">
              <div className="kv-k">status</div>
              <div className="kv-v">
                <span
                  className={
                    run.status === "succeeded"
                      ? "pill ok"
                      : run.status === "failed"
                        ? "pill bad"
                        : "pill"
                  }
                >
                  {run.status}
                </span>
                {shouldPoll ? (
                  <span className="muted" style={{ marginLeft: 8 }}>
                    polling...
                  </span>
                ) : null}
              </div>
            </div>
            <div className="kv-row">
              <div className="kv-k">progress</div>
              <div className="kv-v">
                {run.progress.completed}/{run.progress.total} (failed{" "}
                {run.progress.failed})
              </div>
            </div>
          </div>
        ) : null}
      </div>

      <div className="card">
        <h2>Items</h2>
        {items ? (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>record_id</th>
                  <th>status</th>
                  <th>duration</th>
                  <th>metrics</th>
                  <th>error</th>
                  <th>trace_ref</th>
                </tr>
              </thead>
              <tbody>
                {items.items.map((it) => (
                  <tr key={it.record_id}>
                    <td className="mono">{it.record_id}</td>
                    <td>
                      <span
                        className={
                          it.status === "succeeded" ? "pill ok" : "pill bad"
                        }
                      >
                        {it.status}
                      </span>
                    </td>
                    <td>{formatMs(it.duration_ms)}</td>
                    <td>
                      {it.metrics.length === 0 ? (
                        <span className="muted">-</span>
                      ) : (
                        <div className="metrics">
                          {it.metrics.map((m) => (
                            <div key={m.name} className="metric">
                              <span className="mono">{m.name}</span>
                              <span
                                className={
                                  m.status === "ok"
                                    ? "pill ok"
                                    : m.status === "skipped"
                                      ? "pill"
                                      : "pill bad"
                                }
                              >
                                {m.status}
                              </span>
                              <span className="muted">
                                {m.score === null ? "" : String(m.score)}
                              </span>
                              {metricReason(m.details) ? (
                                <span className="muted">
                                  {metricReason(m.details)}
                                </span>
                              ) : null}
                            </div>
                          ))}
                        </div>
                      )}
                    </td>
                    <td>
                      {it.error ? (
                        <span className="mono">{renderError(it.error)}</span>
                      ) : (
                        <span className="muted">-</span>
                      )}
                    </td>
                    <td className="mono">{it.trace_ref ?? "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="muted">
            未加载。点击 Load items 或等待 run 结束自动加载。
          </div>
        )}
      </div>
    </div>
  );
}
