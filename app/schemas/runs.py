from __future__ import annotations

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


class RunCreateRequest(BaseModel):
    dataset_id: str
    eval_type: str
    sut: SutConfig
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
