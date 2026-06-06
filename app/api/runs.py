from __future__ import annotations

import asyncio
import csv
import io
import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from app.datasets.validator import validate_jsonl_lines
from app.artifacts.store import save_trace_artifact
from app.db.models import Artifact, Dataset, Run, RunItem
from app.execution.engine import RunEngine
from app.schemas.runs import RunCreateRequest, RunCreateResponse, RunGetResponse, RunItemsResponse


router = APIRouter()


def _provider_config_contains_secrets(config: Any) -> bool:
    if not isinstance(config, dict):
        return False
    forbidden = ("api_key", "access_token", "token", "secret", "password")
    for k in config.keys():
        if isinstance(k, str) and any(s in k.lower() for s in forbidden):
            return True
    return False


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
        except Exception:
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
    provider_ref = config.get("provider_ref") or {}
    exec_conf = config.get("execution") or {}
    save_artifacts = exec_conf.get("save_artifacts")
    if save_artifacts is None:
        save_artifacts = settings.save_artifacts
    redaction_policy = exec_conf.get("artifact_redaction") or "default_v1"

    adapter_cls = registry.get_sut_adapter(sut_name)
    adapter = adapter_cls(**sut_config)

    provider = None
    provider_name = provider_ref.get("provider_name")
    provider_config = provider_ref.get("config") or {}
    if provider_name and provider_name not in ("manual", "none"):
        try:
            provider_cls = registry.get_provider(str(provider_name))
            try:
                provider = provider_cls(**provider_config)
            except TypeError:
                provider = provider_cls()
        except KeyError:
            provider = None
        except Exception:
            with SessionLocal() as session:
                run = session.get(Run, run_id)
                if run is not None:
                    run.status = "failed"
                    run.finished_at = datetime.now(timezone.utc)
                    session.commit()
            return

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

    result = await engine.run(records=records, adapter=adapter, metrics=metrics, provider=provider)

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
            if save_artifacts and item.get("trace") is not None:
                artifact_id, artifact_path = save_trace_artifact(
                    artifact_dir=settings.artifact_dir,
                    run_id=run_id,
                    record_id=str(item.get("record_id") or ""),
                    trace=item.get("trace") or {},
                    redaction_policy=redaction_policy,
                )
                session.add(
                    Artifact(
                        id=artifact_id,
                        run_id=run_id,
                        record_id=str(item.get("record_id") or ""),
                        path=artifact_path,
                        redaction_policy=redaction_policy,
                    )
                )
                trace_ref = artifact_path
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

    if _provider_config_contains_secrets(payload.provider_ref.config):
        raise HTTPException(status_code=422, detail="provider_ref.config must not include secrets; use environment variables")

    if payload.provider_ref.provider_name not in ("manual", "none"):
        try:
            registry.get_provider(payload.provider_ref.provider_name)
        except KeyError as e:
            raise HTTPException(status_code=422, detail="unknown provider") from e

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
                    "trace_ref": it.trace_ref,
                    "metrics": (it.metrics_json or {}).get("metrics", []),
                    "duration_ms": it.duration_ms,
                }
            )
        return RunItemsResponse(items=out)


@router.get("/runs/{run_id}/export")
def export_run(request: Request, run_id: str, format: str = Query(..., pattern="^(jsonl|csv|json)$")):
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

        normalized_items: list[dict[str, Any]] = []
        metric_names: set[str] = set()
        for it in items:
            metrics = (it.metrics_json or {}).get("metrics", [])
            for m in metrics:
                if isinstance(m, dict) and "name" in m:
                    metric_names.add(str(m["name"]))
            normalized_items.append(
                {
                    "record_id": it.record_id,
                    "status": it.status,
                    "error": it.error_json,
                    "output": it.output_json,
                    "trace_ref": it.trace_ref,
                    "metrics": metrics,
                    "duration_ms": it.duration_ms,
                }
            )

        run_obj = {
            "run_id": run.id,
            "dataset_id": run.dataset_id,
            "eval_type": run.eval_type,
            "status": run.status,
            "progress": {"total": run.progress_total, "completed": run.progress_completed, "failed": run.progress_failed},
        }

        if format == "json":
            return JSONResponse({"run": run_obj, "items": normalized_items})

        if format == "jsonl":
            lines = [json.dumps(item, ensure_ascii=False) for item in normalized_items]
            return PlainTextResponse("\n".join(lines) + ("\n" if lines else ""), media_type="application/jsonl")

        output = io.StringIO()
        fieldnames = ["record_id", "status", "duration_ms", "error_type", "error_message"]
        for name in sorted(metric_names):
            fieldnames.append(f"metric.{name}.status")
            fieldnames.append(f"metric.{name}.score")

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for item in normalized_items:
            row: dict[str, Any] = {
                "record_id": item["record_id"],
                "status": item["status"],
                "duration_ms": item["duration_ms"],
                "error_type": (item["error"] or {}).get("type") if isinstance(item.get("error"), dict) else None,
                "error_message": (item["error"] or {}).get("message") if isinstance(item.get("error"), dict) else None,
            }
            metric_map = {m.get("name"): m for m in item.get("metrics", []) if isinstance(m, dict) and m.get("name")}
            for name in sorted(metric_names):
                m = metric_map.get(name) or {}
                row[f"metric.{name}.status"] = m.get("status")
                row[f"metric.{name}.score"] = m.get("score")
            writer.writerow(row)

        return PlainTextResponse(output.getvalue(), media_type="text/csv")



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
