import { useCallback, useEffect, useState } from "react";
import { apiFetch, ApiError } from "../api/client";

export default function HealthPage() {
  const [status, setStatus] = useState<"idle" | "loading" | "ok" | "error">(
    "idle",
  );
  const [error, setError] = useState<string | null>(null);

  const check = useCallback(async () => {
    setStatus("loading");
    setError(null);
    try {
      const res = await apiFetch<{ status: string }>("/healthz");
      setStatus(res.status === "ok" ? "ok" : "error");
      if (res.status !== "ok") setError(`unexpected status: ${res.status}`);
    } catch (e) {
      const message = e instanceof ApiError ? e.message : "request failed";
      setStatus("error");
      setError(message);
    }
  }, []);

  useEffect(() => {
    const t = window.setTimeout(() => {
      void check();
    }, 0);
    return () => window.clearTimeout(t);
  }, [check]);

  return (
    <div className="page">
      <h1>Health</h1>
      <p className="muted">通过前端代理访问：/api/healthz</p>

      <div className="card">
        <div className="row">
          <button
            className="btn primary"
            type="button"
            onClick={check}
            disabled={status === "loading"}
          >
            {status === "loading" ? "Checking..." : "Check"}
          </button>
          <div className="pill">
            {status === "ok"
              ? "OK"
              : status === "error"
                ? "ERROR"
                : status === "loading"
                  ? "LOADING"
                  : "IDLE"}
          </div>
        </div>
        {error ? <pre className="error">{error}</pre> : null}
      </div>
    </div>
  );
}
