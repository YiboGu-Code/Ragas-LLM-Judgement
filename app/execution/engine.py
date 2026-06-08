from __future__ import annotations

import asyncio
import os
import time
from typing import Any

from app.plugins.interfaces import MetricResult


class RunEngine:
    def __init__(self, *, max_concurrency: int, timeout_seconds: float) -> None:
        self._max_concurrency = max_concurrency
        self._timeout_seconds = timeout_seconds
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    async def _run_one(self, *, record: dict[str, Any], adapter: Any, metrics: list[Any], provider: Any) -> dict[str, Any]:
        start = time.time()
        metric_timeout_seconds = float(os.getenv("METRIC_TIMEOUT_SECONDS") or "60")
        if metric_timeout_seconds <= 0:
            metric_timeout_seconds = self._timeout_seconds
        metric_timeout_seconds = min(self._timeout_seconds, metric_timeout_seconds)
        try:
            trace_obj = await asyncio.wait_for(
                adapter.execute(record=record, provider=provider),
                timeout=self._timeout_seconds,
            )
            trace = trace_obj.get("trace") if isinstance(trace_obj, dict) else None
            output = trace_obj.get("output") if isinstance(trace_obj, dict) else None
            metric_results: list[dict[str, Any]] = []
            any_metric_failed = False
            for metric in metrics:
                metric_name = getattr(metric, "name", None) or metric.__class__.__name__
                metric_version = getattr(metric, "version", None) or "1"
                try:
                    mr = await asyncio.wait_for(
                        metric.evaluate(record=record, trace=trace or {}, provider=provider),
                        timeout=metric_timeout_seconds,
                    )
                    mr_dict = getattr(mr, "__dict__", None)
                    if not isinstance(mr_dict, dict):
                        raise TypeError("metric.evaluate must return an object with __dict__")
                    metric_results.append(mr_dict)
                    if mr_dict.get("status") == "failed":
                        any_metric_failed = True
                except asyncio.TimeoutError:
                    metric_results.append(
                        MetricResult(
                            name=str(metric_name),
                            status="skipped",
                            score=None,
                            details={"reason": "metric timeout"},
                            version=str(metric_version),
                        ).__dict__
                    )
                except Exception as e:
                    any_metric_failed = True
                    metric_results.append(
                        MetricResult(
                            name=str(metric_name),
                            status="failed",
                            score=None,
                            details={"reason": str(e), "error_type": e.__class__.__name__},
                            version=str(metric_version),
                        ).__dict__
                    )
            return {
                "record_id": record.get("record_id"),
                "status": "failed" if any_metric_failed else "succeeded",
                "output": output,
                "trace": trace,
                "metrics": metric_results,
                "duration_ms": int((time.time() - start) * 1000),
            }
        except Exception as e:
            return {
                "record_id": record.get("record_id"),
                "status": "failed",
                "error": {"type": e.__class__.__name__, "message": str(e)},
                "metrics": [],
                "duration_ms": int((time.time() - start) * 1000),
            }

    async def run(self, *, records: list[dict[str, Any]], adapter: Any, metrics: list[Any], provider: Any) -> dict[str, Any]:
        sem = asyncio.Semaphore(self._max_concurrency)
        items: list[dict[str, Any]] = []

        async def worker(rec: dict[str, Any]) -> None:
            if self._cancelled:
                return
            async with sem:
                items.append(await self._run_one(record=rec, adapter=adapter, metrics=metrics, provider=provider))

        await asyncio.gather(*(worker(r) for r in records))
        failed = sum(1 for it in items if it["status"] == "failed")
        return {"summary": {"total": len(records), "failed": failed}, "items": items}
