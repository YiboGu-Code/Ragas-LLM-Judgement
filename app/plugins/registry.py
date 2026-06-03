from __future__ import annotations

from typing import Any, Type


class PluginRegistry:
    def __init__(self) -> None:
        self._metrics: dict[str, Type[Any]] = {}
        self._sut_adapters: dict[str, Type[Any]] = {}
        self._providers: dict[str, Type[Any]] = {}

    def register_metric(self, metric_cls: Type[Any]) -> None:
        name = getattr(metric_cls, "name", None)
        if not name:
            raise ValueError("metric_cls.name is required")
        self._metrics[str(name)] = metric_cls

    def get_metric(self, name: str) -> Type[Any]:
        return self._metrics[name]

    def register_sut_adapter(self, adapter_cls: Type[Any]) -> None:
        name = getattr(adapter_cls, "name", None)
        if not name:
            raise ValueError("adapter_cls.name is required")
        self._sut_adapters[str(name)] = adapter_cls

    def get_sut_adapter(self, name: str) -> Type[Any]:
        return self._sut_adapters[name]

    def register_provider(self, provider_cls: Type[Any]) -> None:
        name = getattr(provider_cls, "name", None)
        if not name:
            raise ValueError("provider_cls.name is required")
        self._providers[str(name)] = provider_cls

    def get_provider(self, name: str) -> Type[Any]:
        return self._providers[name]
