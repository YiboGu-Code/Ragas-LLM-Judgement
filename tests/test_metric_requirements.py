import pytest

from app.metrics.basic import RagContextsPresentMetric


@pytest.mark.anyio
async def test_rag_contexts_present_metric_skipped_when_missing():
    metric = RagContextsPresentMetric()
    record = {"type": "rag", "input": {"question": "q"}}
    trace = {"retrieval": {}}
    res = await metric.evaluate(record=record, trace=trace, provider=None)
    assert res.status == "skipped"


@pytest.mark.anyio
async def test_rag_contexts_present_metric_ok_when_present():
    metric = RagContextsPresentMetric()
    record = {"type": "rag", "input": {"question": "q"}}
    trace = {"retrieval": {"contexts": ["c1", "c2"]}}
    res = await metric.evaluate(record=record, trace=trace, provider=None)
    assert res.status == "ok"
    assert res.score == 1.0
