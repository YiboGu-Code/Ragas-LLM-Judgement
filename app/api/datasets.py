from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, Response, UploadFile

from app.datasets.validator import validate_jsonl_lines
from app.db.models import Dataset, Run
from app.schemas.datasets import DatasetCreateResponse, DatasetGetResponse


router = APIRouter()


@router.post("/datasets", response_model=DatasetCreateResponse)
def create_dataset(
    request: Request,
    file: UploadFile = File(...),
    name: str | None = Form(default=None),
    eval_type: str = Form(...),
):
    settings = request.app.state.settings
    dataset_id = str(uuid.uuid4())

    raw_bytes = file.file.read()
    try:
        content = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as e:
        raise HTTPException(status_code=422, detail="dataset file must be utf-8") from e

    lines = content.splitlines()
    try:
        records = validate_jsonl_lines(lines=lines, eval_type=eval_type)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    raw_path: str | None = None
    if settings.save_raw_datasets:
        dataset_dir = Path(settings.dataset_dir)
        dataset_dir.mkdir(parents=True, exist_ok=True)
        raw_path = str(dataset_dir / f"{dataset_id}.jsonl")
        Path(raw_path).write_text(content, encoding="utf-8")

    SessionLocal = request.app.state.SessionLocal
    with SessionLocal() as session:
        ds = Dataset(
            id=dataset_id,
            name=name,
            eval_type=eval_type,
            schema_version="v1",
            records_count=len(records),
            raw_path=raw_path,
        )
        session.add(ds)
        session.commit()

    return DatasetCreateResponse(
        dataset_id=dataset_id,
        records_count=len(records),
        eval_type=eval_type,
        schema_version="v1",
    )


@router.get("/datasets/{dataset_id}", response_model=DatasetGetResponse)
def get_dataset(request: Request, dataset_id: str):
    SessionLocal = request.app.state.SessionLocal
    with SessionLocal() as session:
        ds = session.get(Dataset, dataset_id)
        if ds is None:
            raise HTTPException(status_code=404, detail="dataset not found")
        return DatasetGetResponse(
            dataset_id=ds.id,
            name=ds.name,
            eval_type=ds.eval_type,
            schema_version=ds.schema_version,
            records_count=ds.records_count,
            raw_path=ds.raw_path,
        )


@router.delete("/datasets/{dataset_id}", status_code=204)
def delete_dataset(request: Request, dataset_id: str):
    SessionLocal = request.app.state.SessionLocal

    with SessionLocal() as session:
        ds = session.get(Dataset, dataset_id)
        if ds is None:
            raise HTTPException(status_code=404, detail="dataset not found")

        existing_run = session.query(Run).filter(Run.dataset_id == dataset_id).first()
        if existing_run is not None:
            raise HTTPException(status_code=409, detail="dataset is referenced by runs; delete runs first")

        if ds.raw_path:
            try:
                Path(ds.raw_path).unlink(missing_ok=True)
            except Exception:
                pass

        session.delete(ds)
        session.commit()

    return Response(status_code=204)
