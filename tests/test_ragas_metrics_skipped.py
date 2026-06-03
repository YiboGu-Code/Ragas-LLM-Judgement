import pytest

from app.metrics.ragas_metrics import RagasAnswerRelevancyMetric, RagasFaithfulnessMetric


class ChatOnlyProvider:
    name = "chat_only"

    async def chat(self, *, messages, **kwargs):
        return {"text": "ok"}


@pytest.mark.anyio
async def test_ragas_faithfulness_skipped_without_embed():
    metric = RagasFaithfulnessMetric()
    record = {"type": "rag", "input": {"question": "q"}}
    trace = {"retrieval": {"contexts": ["c1"]}, "output": {"answer": "a"}}
    res = await metric.evaluate(record=record, trace=trace, provider=ChatOnlyProvider())
    assert res.status == "skipped"


@pytest.mark.anyio
async def test_ragas_answer_relevancy_skipped_without_provider():
    metric = RagasAnswerRelevancyMetric()
    record = {"type": "rag", "input": {"question": "q"}}
    trace = {"retrieval": {"contexts": ["c1"]}, "output": {"answer": "a"}}
    res = await metric.evaluate(record=record, trace=trace, provider=None)
    assert res.status == "skipped"
