from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class DatasetCreateResponse(BaseModel):
    dataset_id: str
    records_count: int
    eval_type: str
    schema_version: str


class DatasetGetResponse(BaseModel):
    dataset_id: str
    name: str | None
    eval_type: str
    schema_version: str
    records_count: int
    raw_path: str | None


class DatasetListItem(BaseModel):
    dataset_id: str
    name: str | None
    eval_type: str
    schema_version: str
    records_count: int
    created_at: datetime


class DatasetListResponse(BaseModel):
    items: list[DatasetListItem]


class DatasetBulkDeleteRequest(BaseModel):
    dataset_ids: list[str]


class BulkDeleteResult(BaseModel):
    id: str
    status: str
    detail: str | None = None


class DatasetBulkDeleteResponse(BaseModel):
    results: list[BulkDeleteResult]
