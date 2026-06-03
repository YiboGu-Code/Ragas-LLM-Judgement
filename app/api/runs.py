from __future__ import annotations

import asyncio
import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from app.datasets.validator import validate_jsonl_lines
from app.db.models import Dataset, Run, RunItem
from app.execution.engine import RunEngine
from app.schemas.runs import RunCreateRequest, RunCreateResponse, RunGetResponse, RunItemsResponse


router = APIRouter()


def _load_records_for_run(*, dataset: Dataset) -> list[dict[str, Any]]:
    if not dataset.raw_path:
        raise ValueError("dataset raw_path is missing")
    content = Path(dataset.raw_path).read_text(encoding="utf-8")
    records = validate_jsonl_lines(lines=content.splitlines(), eval_type=dataset.eval_type)
    normalized: list[dict[str, Any]] = []
    for idx, rec in enumerate(records, start=1):
        record_id = rec.get("record_id") or f"line-{idx}"
        rec["record_id"] = record_id
        normalized.append(rec)
    return normalized


async def _execute_run_async(*, app, run_id: str) -> None:
    SessionLocal = app.state.SessionLocal
    registry = app.state.registry
    settings = app.state.settings

    with SessionLocal() as session:
        run = session.get(Run, run_id)
        if run is None:
            return
        ds = session.get(Dataset, run.dataset_id)
        if ds is None:
            run.status = "failed"
            run.finished_at = datetime.now(timezone.utc)
            session.commit()
            return
        try:
            records = _load_records_for_run(dataset=ds)
        except Exception as e:
            run.status = "failed"
            run.finished_at = datetime.now(timezone.utc)
            run.progress_total = 0
            run.progress_failed = 0
            run.progress_completed = 0
            session.commit()
            return

    config = run.config_snapshot_json
    sut_name = config["sut"]["adapter_name"]
    sut_config = config["sut"]["adapter_config"]
    metric_confs = config["metrics"]
    exec_conf = config.get("execution") or {}

    adapter_cls = registry.get_sut_adapter(sut_name)
    adapter = adapter_cls(**sut_config)

    metrics = []
    for mc in metric_confs:
        metric_cls = registry.get_metric(mc["metric_name"])
        metric_config = mc.get("metric_config") or {}
        try:
            metrics.append(metric_cls(**metric_config))
        except TypeError:
            metrics.append(metric_cls())

    engine = RunEngine(
        max_concurrency=int(exec_conf.get("max_concurrency") or settings.default_max_concurrency),
        timeout_seconds=float(exec_conf.get("timeout_seconds") or settings.default_timeout_seconds),
    )

    result = await engine.run(records=records, adapter=adapter, metrics=metrics, provider=None)

    with SessionLocal() as session:
        run = session.get(Run, run_id)
        if run is None:
            return

        run.progress_total = result["summary"]["total"]
        run.progress_failed = result["summary"]["failed"]
        run.progress_completed = result["summary"]["total"] - result["summary"]["failed"]
        run.status = "failed" if result["summary"]["failed"] > 0 else "succeeded"
        run.finished_at = datetime.now(timezone.utc)

        for item in result["items"]:
            metrics_json = {"metrics": item.get("metrics", [])}
            out_json = item.get("output")
            error_json = item.get("error")
            trace_ref = None
            ri = RunItem(
                id=str(uuid.uuid4()),
                run_id=run_id,
                record_id=str(item.get("record_id") or ""),
                status=item.get("status") or "failed",
                error_json=error_json,
                output_json=out_json,
                trace_ref=trace_ref,
                metrics_json=metrics_json,
                duration_ms=item.get("duration_ms"),
            )
            session.add(ri)

        session.commit()


def _execute_run_background(*, app, run_id: str) -> None:
    asyncio.run(_execute_run_async(app=app, run_id=run_id))


@router.post("/runs", response_model=RunCreateResponse)
def create_run(request: Request, payload: RunCreateRequest):
    SessionLocal = request.app.state.SessionLocal
    registry = request.app.state.registry

    try:
        registry.get_sut_adapter(payload.sut.adapter_name)
    except KeyError as e:
        raise HTTPException(status_code=422, detail="unknown sut adapter") from e

    for mc in payload.metrics:
        try:
            registry.get_metric(mc.metric_name)
        except KeyError as e:
            raise HTTPException(status_code=422, detail="unknown metric") from e

    with SessionLocal() as session:
        ds = session.get(Dataset, payload.dataset_id)
        if ds is None:
            raise HTTPException(status_code=404, detail="dataset not found")
        if ds.eval_type != payload.eval_type:
            raise HTTPException(status_code=422, detail="eval_type mismatch with dataset")
        if not ds.raw_path:
            raise HTTPException(status_code=422, detail="dataset is not runnable (raw_path missing)")

        run_id = str(uuid.uuid4())
        snapshot = json.loads(payload.model_dump_json())
        run = Run(
            id=run_id,
            dataset_id=payload.dataset_id,
            eval_type=payload.eval_type,
            status="created",
            config_snapshot_json=snapshot,
            progress_total=0,
            progress_completed=0,
            progress_failed=0,
        )
        session.add(run)
        session.commit()

    return RunCreateResponse(run_id=run_id, status="created")


@router.post("/runs/{run_id}/start", response_model=RunGetResponse)
def start_run(request: Request, run_id: str):
    SessionLocal = request.app.state.SessionLocal
    with SessionLocal() as session:
        run = session.get(Run, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="run not found")
        if run.status not in ("created", "queued"):
            return RunGetResponse(
                run_id=run.id,
                status=run.status,
                progress={"total": run.progress_total, "completed": run.progress_completed, "failed": run.progress_failed},
            )
        run.status = "running"
        run.started_at = datetime.now(timezone.utc)
        session.commit()

    t = threading.Thread(target=_execute_run_background, kwargs={"app": request.app, "run_id": run_id}, daemon=True)
    t.start()

    with SessionLocal() as session:
        run = session.get(Run, run_id)
        return RunGetResponse(
            run_id=run.id,
            status=run.status,
            progress={"total": run.progress_total, "completed": run.progress_completed, "failed": run.progress_failed},
        )


@router.get("/runs/{run_id}", response_model=RunGetResponse)
def get_run(request: Request, run_id: str):
    SessionLocal = request.app.state.SessionLocal
    with SessionLocal() as session:
        run = session.get(Run, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="run not found")
        return RunGetResponse(
            run_id=run.id,
            status=run.status,
            progress={"total": run.progress_total, "completed": run.progress_completed, "failed": run.progress_failed},
        )


@router.get("/runs/{run_id}/items", response_model=RunItemsResponse)
def get_run_items(request: Request, run_id: str):
    SessionLocal = request.app.state.SessionLocal
    with SessionLocal() as session:
        run = session.get(Run, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="run not found")
        items = (
            session.query(RunItem)
            .filter(RunItem.run_id == run_id)
            .order_by(RunItem.id.asc())
            .all()
        )
        out = []
        for it in items:
            out.append(
                {
                    "record_id": it.record_id,
                    "status": it.status,
                    "error": it.error_json,
                    "output": it.output_json,
                    "metrics": (it.metrics_json or {}).get("metrics", []),
                    "duration_ms": it.duration_ms,
                }
            )
        return RunItemsResponse(items=out)


@router.post("/runs/{run_id}/cancel", response_model=RunGetResponse)
def cancel_run(request: Request, run_id: str):
    SessionLocal = request.app.state.SessionLocal
    with SessionLocal() as session:
        run = session.get(Run, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="run not found")
        if run.status in ("succeeded", "failed", "canceled"):
            return RunGetResponse(
                run_id=run.id,
                status=run.status,
                progress={"total": run.progress_total, "completed": run.progress_completed, "failed": run.progress_failed},
            )
        run.status = "canceled"
        run.finished_at = datetime.now(timezone.utc)
        session.commit()
        return RunGetResponse(
            run_id=run.id,
            status=run.status,
            progress={"total": run.progress_total, "completed": run.progress_completed, "failed": run.progress_failed},
        )
