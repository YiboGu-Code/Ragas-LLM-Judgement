import pytest

import app.metrics.ragas_metrics as ragas_metrics
from app.metrics.ragas_metrics import (
    RagasAgentGoalAccuracyMetric,
    RagasAnswerRelevancyMetric,
    RagasFaithfulnessMetric,
)


class FullProvider:
    def get_ragas_llm(self):
        return object()

    def get_ragas_embeddings(self):
        return object()


@pytest.mark.anyio
async def test_ragas_answer_relevancy_ok(monkeypatch):
    async def fake_score_single_turn(*, ragas_metric, sample, llm, embeddings):
        assert sample["user_input"] == "q"
        assert sample["response"] == "a"
        assert llm is not None
        assert embeddings is not None
        return 0.42

    monkeypatch.setattr(ragas_metrics, "_score_single_turn", fake_score_single_turn)

    metric = RagasAnswerRelevancyMetric()
    record = {"type": "prompt", "input": {"user_input": "q"}}
    trace = {"output": {"answer": "a"}}
    res = await metric.evaluate(record=record, trace=trace, provider=FullProvider())
    assert res.status == "ok"
    assert res.score == 0.42


@pytest.mark.anyio
async def test_ragas_faithfulness_ok(monkeypatch):
    async def fake_score_single_turn(*, ragas_metric, sample, llm, embeddings):
        assert sample["user_input"] == "q"
        assert sample["response"] == "a"
        assert sample["retrieved_contexts"] == ["c1"]
        assert llm is not None
        assert embeddings is None
        return 0.9

    monkeypatch.setattr(ragas_metrics, "_score_single_turn", fake_score_single_turn)

    metric = RagasFaithfulnessMetric()
    record = {"type": "rag", "input": {"question": "q"}}
    trace = {"retrieval": {"contexts": ["c1"]}, "output": {"answer": "a"}}
    res = await metric.evaluate(record=record, trace=trace, provider=FullProvider())
    assert res.status == "ok"
    assert res.score == 0.9


@pytest.mark.anyio
async def test_ragas_agent_goal_accuracy_ok(monkeypatch):
    class DummyResult:
        def __init__(self, scores):
            self.scores = scores

    async def fake_aevaluate(*, dataset, metrics, llm, embeddings, show_progress):
        assert llm is not None
        assert embeddings is None
        assert len(metrics) == 1
        return DummyResult(scores=[{metrics[0].name: 1.0}])

    monkeypatch.setattr(ragas_metrics, "aevaluate", fake_aevaluate)

    metric = RagasAgentGoalAccuracyMetric()
    record = {"type": "agent", "input": {"task": "t"}}
    trace = {"agent": {"messages": [{"role": "user", "content": "t"}, {"role": "assistant", "content": "ok"}]}}
    res = await metric.evaluate(record=record, trace=trace, provider=FullProvider())
    assert res.status == "ok"
    assert res.score == 1.0
