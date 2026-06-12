from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SutConfig(BaseModel):
    adapter_name: str
    adapter_config: dict


class MetricConfig(BaseModel):
    metric_name: str
    metric_config: dict


class ProviderRef(BaseModel):
    provider_name: str
    config: dict


class ExecutionConfig(BaseModel):
    max_concurrency: int | None = None
    timeout_seconds: float | None = None
    save_artifacts: bool | None = None
    artifact_redaction: str | None = None


class RunCreateRequest(BaseModel):
    dataset_id: str
    eval_type: str
    sut: SutConfig | None = None
    metrics: list[MetricConfig]
    provider_ref: ProviderRef
    execution: ExecutionConfig | None = None


class RunCreateResponse(BaseModel):
    run_id: str
    status: str


class RunGetResponse(BaseModel):
    run_id: str
    status: str
    progress: dict


class RunItemsResponse(BaseModel):
    items: list[dict]


class RunListItem(BaseModel):
    run_id: str
    dataset_id: str
    eval_type: str
    status: str
    progress: dict
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class RunListResponse(BaseModel):
    items: list[RunListItem]
