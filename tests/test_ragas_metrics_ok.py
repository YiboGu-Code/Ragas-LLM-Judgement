import pytest

import app.metrics.ragas_metrics as ragas_metrics
from app.metrics.ragas_metrics import (
    RagasAgentGoalAccuracyMetric,
    RagasAnswerCorrectnessMetric,
    RagasAnswerRelevancyMetric,
    RagasFaithfulnessMetric,
)


class FullProvider:
    def get_ragas_llm(self):
        return object()

    def get_ragas_embeddings(self):
        return object()


@pytest.mark.anyio
async def test_score_single_turn_sets_metric_llm_and_embeddings(monkeypatch):
    class DummyResult:
        def __init__(self, scores):
            self.scores = scores

    class DummyMetric:
        name = "answer_relevancy"

        def __init__(self):
            self.llm = None
            self.embeddings = None

    async def fake_aevaluate(*, dataset, metrics, llm, embeddings, show_progress):
        assert dataset is not None
        assert llm is not None
        assert embeddings is not None
        assert len(metrics) == 1
        assert metrics[0].llm is llm
        assert metrics[0].embeddings is embeddings
        return DummyResult(scores=[{metrics[0].name: 0.1}])

    monkeypatch.setattr(ragas_metrics, "aevaluate", fake_aevaluate)

    score = await ragas_metrics._score_single_turn(
        ragas_metric=DummyMetric(),
        sample={"user_input": "q", "response": "a"},
        llm=object(),
        embeddings=object(),
    )
    assert score == 0.1


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
async def test_ragas_faithfulness_ok():
    metric = RagasFaithfulnessMetric()
    record = {"type": "rag", "input": {"question": "q"}}
    trace = {"retrieval": {"contexts": ["abc"]}, "output": {"answer": "abc"}}
    res = await metric.evaluate(record=record, trace=trace, provider=None)
    assert res.status == "ok"
    assert res.score == 1.0


@pytest.mark.anyio
async def test_ragas_answer_correctness_short_circuits_when_reference_equals_answer(monkeypatch):
    async def fake_score_single_turn(*, ragas_metric, sample, llm, embeddings):
        raise AssertionError("_score_single_turn should not be called when reference == answer")

    monkeypatch.setattr(ragas_metrics, "_score_single_turn", fake_score_single_turn)

    metric = RagasAnswerCorrectnessMetric()
    record = {"type": "prompt", "input": {"user_input": "q"}, "expected": {"reference": "a"}}
    trace = {"output": {"answer": "a"}}
    res = await metric.evaluate(record=record, trace=trace, provider=FullProvider())
    assert res.status == "ok"
    assert res.score == 1.0


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


@pytest.mark.anyio
async def test_ragas_metrics_truncate_long_text(monkeypatch):
    async def fake_score_single_turn(*, ragas_metric, sample, llm, embeddings):
        assert len(sample["user_input"]) == ragas_metrics._MAX_TEXT_CHARS
        assert len(sample["response"]) == ragas_metrics._MAX_TEXT_CHARS
        return 0.5

    monkeypatch.setattr(ragas_metrics, "_score_single_turn", fake_score_single_turn)

    metric = RagasAnswerRelevancyMetric()
    record = {"type": "prompt", "input": {"user_input": "q" * (ragas_metrics._MAX_TEXT_CHARS + 10)}}
    trace = {"output": {"answer": "a" * (ragas_metrics._MAX_TEXT_CHARS + 10)}}
    res = await metric.evaluate(record=record, trace=trace, provider=FullProvider())
    assert res.status == "ok"
    assert res.score == 0.5
