from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class MetricRequirement:
    needs_provider_chat: bool = False
    needs_provider_embed: bool = False
    needs_rag_contexts: bool = False
    needs_ground_truth: bool = False


@dataclass(frozen=True)
class MetricResult:
    name: str
    status: str
    score: float | None
    details: dict[str, Any]
    version: str


@runtime_checkable
class ModelProvider(Protocol):
    name: str

    async def chat(self, *, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]: ...

    async def embed(self, *, texts: list[str], **kwargs: Any) -> list[list[float]]: ...


@runtime_checkable
class Metric(Protocol):
    name: str
    version: str
    requirements: MetricRequirement

    async def evaluate(
        self, *, record: dict[str, Any], trace: dict[str, Any], provider: ModelProvider | None
    ) -> MetricResult: ...


@runtime_checkable
class SUTAdapter(Protocol):
    name: str

    async def execute(self, *, record: dict[str, Any], provider: ModelProvider | None) -> dict[str, Any]: ...
