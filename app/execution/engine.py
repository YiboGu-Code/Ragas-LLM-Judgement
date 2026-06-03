from __future__ import annotations

import asyncio
import time
from typing import Any


class RunEngine:
    def __init__(self, *, max_concurrency: int, timeout_seconds: float) -> None:
        self._max_concurrency = max_concurrency
        self._timeout_seconds = timeout_seconds
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    async def _run_one(self, *, record: dict[str, Any], adapter: Any, metrics: list[Any], provider: Any) -> dict[str, Any]:
        start = time.time()
        try:
            trace_obj = await asyncio.wait_for(
                adapter.execute(record=record, provider=provider),
                timeout=self._timeout_seconds,
            )
            trace = trace_obj.get("trace") if isinstance(trace_obj, dict) else None
            output = trace_obj.get("output") if isinstance(trace_obj, dict) else None
            metric_results: list[dict[str, Any]] = []
            for metric in metrics:
                mr = await metric.evaluate(record=record, trace=trace or {}, provider=provider)
                metric_results.append(mr.__dict__)
            return {
                "record_id": record.get("record_id"),
                "status": "succeeded",
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
