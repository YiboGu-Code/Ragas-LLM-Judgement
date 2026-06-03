import pytest

from app.plugins.registry import PluginRegistry


def test_registry_can_register_and_get_metric():
    registry = PluginRegistry()

    class MyMetric:
        name = "my_metric"

    registry.register_metric(MyMetric)
    metric_cls = registry.get_metric("my_metric")
    assert metric_cls is MyMetric


def test_registry_unknown_plugin_raises_key_error():
    registry = PluginRegistry()
    with pytest.raises(KeyError):
        registry.get_metric("missing")
