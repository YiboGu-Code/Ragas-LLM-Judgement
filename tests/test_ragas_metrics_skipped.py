import pytest

from app.metrics.ragas_metrics import RagasAnswerRelevancyMetric, RagasFaithfulnessMetric


class LlmOnlyProvider:
    name = "llm_only"

    def get_ragas_llm(self):
        return object()


@pytest.mark.anyio
async def test_ragas_faithfulness_ok_without_provider():
    metric = RagasFaithfulnessMetric()
    record = {"type": "rag", "input": {"question": "q"}}
    trace = {"retrieval": {"contexts": ["c1"]}, "output": {"answer": "a"}}
    res = await metric.evaluate(record=record, trace=trace, provider=None)
    assert res.status == "ok"
    assert res.score is not None
    assert 0.0 <= res.score <= 1.0


@pytest.mark.anyio
async def test_ragas_answer_relevancy_skipped_without_provider():
    metric = RagasAnswerRelevancyMetric()
    record = {"type": "prompt", "input": {"user_input": "q"}}
    trace = {"output": {"answer": "a"}}
    res = await metric.evaluate(record=record, trace=trace, provider=LlmOnlyProvider())
    assert res.status == "skipped"
