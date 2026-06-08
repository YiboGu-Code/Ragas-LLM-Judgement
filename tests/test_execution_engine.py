import pytest

from app.execution.engine import RunEngine
from app.plugins.interfaces import MetricRequirement, MetricResult


class DummyAdapter:
    name = "dummy"

    async def execute(self, *, record, provider):
        return {"output": {"final": record["input"]["x"]}, "trace": {"messages": []}}


class DummyMetric:
    name = "dummy_metric"
    version = "1"
    requirements = MetricRequirement()

    async def evaluate(self, *, record, trace, provider):
        return MetricResult(name=self.name, status="ok", score=1.0, details={}, version=self.version)


@pytest.mark.anyio
async def test_engine_runs_all_items():
    engine = RunEngine(max_concurrency=2, timeout_seconds=5)
    records = [
        {"record_id": "r1", "type": "prompt", "input": {"x": "a"}},
        {"record_id": "r2", "type": "prompt", "input": {"x": "b"}},
    ]
    results = await engine.run(records=records, adapter=DummyAdapter(), metrics=[DummyMetric()], provider=None)
    assert results["summary"]["total"] == 2
    assert results["summary"]["failed"] == 0
    assert results["items"][0]["metrics"][0]["name"] == "dummy_metric"


class SlowAdapter:
    name = "slow"

    async def execute(self, *, record, provider):
        import asyncio

        await asyncio.sleep(1)
        return {"output": {"final": "late"}, "trace": {"messages": []}}


@pytest.mark.anyio
async def test_engine_timeout_marks_item_failed():
    engine = RunEngine(max_concurrency=1, timeout_seconds=0.01)
    results = await engine.run(
        records=[{"record_id": "r1", "type": "prompt", "input": {"x": "a"}}],
        adapter=SlowAdapter(),
        metrics=[],
        provider=None,
    )
    assert results["summary"]["failed"] == 1
    assert results["items"][0]["status"] == "failed"


class ExplodingMetric:
    name = "exploding_metric"
    version = "1"
    requirements = MetricRequirement()

    async def evaluate(self, *, record, trace, provider):
        raise ValueError("boom")


class SlowMetric:
    name = "slow_metric"
    version = "1"
    requirements = MetricRequirement()

    async def evaluate(self, *, record, trace, provider):
        import asyncio

        await asyncio.sleep(0.1)
        return MetricResult(name=self.name, status="ok", score=1.0, details={}, version=self.version)


@pytest.mark.anyio
async def test_engine_metric_exception_does_not_crash_item():
    engine = RunEngine(max_concurrency=1, timeout_seconds=1)
    results = await engine.run(
        records=[{"record_id": "r1", "type": "prompt", "input": {"x": "a"}}],
        adapter=DummyAdapter(),
        metrics=[ExplodingMetric(), DummyMetric()],
        provider=None,
    )
    assert results["summary"]["failed"] == 1
    assert results["items"][0]["status"] == "failed"
    assert [m["name"] for m in results["items"][0]["metrics"]] == ["exploding_metric", "dummy_metric"]
    assert results["items"][0]["metrics"][0]["status"] == "failed"
    assert results["items"][0]["metrics"][1]["status"] == "ok"


@pytest.mark.anyio
async def test_engine_metric_timeout_marks_metric_failed():
    engine = RunEngine(max_concurrency=1, timeout_seconds=0.01)
    results = await engine.run(
        records=[{"record_id": "r1", "type": "prompt", "input": {"x": "a"}}],
        adapter=DummyAdapter(),
        metrics=[SlowMetric()],
        provider=None,
    )
    assert results["summary"]["failed"] == 0
    assert results["items"][0]["status"] == "succeeded"
    assert results["items"][0]["metrics"][0]["name"] == "slow_metric"
    assert results["items"][0]["metrics"][0]["status"] == "skipped"
