from __future__ import annotations

import json
import math
import os
import re
from typing import Any, Iterable

from ragas import aevaluate
from ragas.dataset_schema import EvaluationDataset, MultiTurnSample
from ragas.messages import AIMessage, HumanMessage, ToolMessage
from ragas.metrics._answer_correctness import AnswerCorrectness
from ragas.metrics._answer_relevance import AnswerRelevancy
from ragas.metrics._context_precision import ContextPrecision
from ragas.metrics._context_recall import ContextRecall
from ragas.metrics._faithfulness import Faithfulness
from ragas.metrics._goal_accuracy import AgentGoalAccuracyWithoutReference

from app.plugins.interfaces import MetricRequirement, MetricResult


_MAX_TEXT_CHARS = int(os.getenv("RAGAS_MAX_TEXT_CHARS") or "800")
_MAX_CONTEXTS = int(os.getenv("RAGAS_MAX_CONTEXTS") or "3")
_HEURISTIC_SHINGLE_N = int(os.getenv("RAGAS_HEURISTIC_SHINGLE_N") or "2")


def _is_nan(value: Any) -> bool:
    return isinstance(value, float) and math.isnan(value)


def _truncate_text(text: str, *, max_chars: int) -> str:
    if max_chars <= 0:
        return text
    if len(text) <= max_chars:
        return text
    return text[:max_chars]


_NON_WORD_RE = re.compile(r"[\s\r\n\t]+", re.UNICODE)
_PUNCT_RE = re.compile(r"[^\w\u4e00-\u9fff]+", re.UNICODE)


def _normalize_text_for_overlap(text: str) -> str:
    t = text.strip().lower()
    t = _NON_WORD_RE.sub(" ", t)
    t = _PUNCT_RE.sub("", t)
    return t


def _shingles(text: str, *, n: int) -> set[str]:
    if n <= 0:
        n = 2
    t = _normalize_text_for_overlap(text)
    if not t:
        return set()
    if len(t) <= n:
        return {t}
    return {t[i : i + n] for i in range(0, len(t) - n + 1)}


def _overlap_ratio(*, numerator: set[str], denominator: set[str]) -> float:
    if not denominator:
        return 0.0
    return len(numerator & denominator) / float(len(denominator))


def _heuristic_faithfulness(*, answer: str, contexts: list[str]) -> float:
    ans = _shingles(answer, n=_HEURISTIC_SHINGLE_N)
    ctx = _shingles("".join(contexts), n=_HEURISTIC_SHINGLE_N)
    if not ans or not ctx:
        return 0.0
    return max(0.0, min(1.0, _overlap_ratio(numerator=ctx, denominator=ans)))


def _heuristic_context_recall(*, reference: str, contexts: list[str]) -> float:
    ref = _shingles(reference, n=_HEURISTIC_SHINGLE_N)
    ctx = _shingles("".join(contexts), n=_HEURISTIC_SHINGLE_N)
    return max(0.0, min(1.0, _overlap_ratio(numerator=ctx, denominator=ref)))



def _extract_answer(trace: dict[str, Any]) -> str | None:
    out = trace.get("output")
    if isinstance(out, dict):
        answer = out.get("answer")
        if isinstance(answer, str) and answer.strip():
            return answer
        text = out.get("text")
        if isinstance(text, str) and text.strip():
            return text
    if isinstance(out, str) and out.strip():
        return out
    return None


def _extract_user_input(record: dict[str, Any]) -> str | None:
    record_type = record.get("type")
    inp = record.get("input") or {}
    if record_type == "prompt":
        val = inp.get("user_input")
        return val if isinstance(val, str) and val.strip() else None
    if record_type == "rag":
        val = inp.get("question")
        return val if isinstance(val, str) and val.strip() else None
    if record_type == "workflow":
        val = inp.get("goal")
        return val if isinstance(val, str) and val.strip() else None
    if record_type == "agent":
        val = inp.get("task")
        return val if isinstance(val, str) and val.strip() else None
    for k in ("question", "user_input", "goal", "task"):
        val = inp.get(k)
        if isinstance(val, str) and val.strip():
            return val
    return None


def _extract_reference(record: dict[str, Any]) -> str | None:
    expected = record.get("expected") or {}
    if not isinstance(expected, dict):
        return None
    for k in ("reference", "ground_truth", "answer", "expected_answer"):
        val = expected.get(k)
        if isinstance(val, str) and val.strip():
            return val
    return None


def _iter_context_texts(contexts: Any) -> Iterable[str]:
    if not isinstance(contexts, list):
        return []
    out: list[str] = []
    for c in contexts:
        if isinstance(c, str):
            if c.strip():
                out.append(c)
            continue
        if isinstance(c, dict):
            text = c.get("text")
            if isinstance(text, str) and text.strip():
                out.append(text)
                continue
        out.append(json.dumps(c, ensure_ascii=False))
    return out


def _get_ragas_llm(provider: Any):
    fn = getattr(provider, "get_ragas_llm", None)
    if not callable(fn):
        raise ValueError("provider missing get_ragas_llm()")
    return fn()


def _get_ragas_embeddings(provider: Any):
    fn = getattr(provider, "get_ragas_embeddings", None)
    if not callable(fn):
        raise ValueError("provider missing get_ragas_embeddings()")
    return fn()


async def _score_single_turn(*, ragas_metric: Any, sample: dict[str, Any], llm: Any, embeddings: Any | None) -> float | None:
    ds = EvaluationDataset.from_list([sample])
    result = await aevaluate(dataset=ds, metrics=[ragas_metric], llm=llm, embeddings=embeddings, show_progress=False)
    if not result.scores:
        return None
    key = getattr(ragas_metric, "name", None) or getattr(ragas_metric, "__class__", type("x", (), {})).__name__
    score = result.scores[0].get(str(key))
    if score is None or _is_nan(score):
        return None
    return float(score)


def _messages_from_trace(*, record: dict[str, Any], trace: dict[str, Any]) -> list[Any] | None:
    msgs = ((trace.get("agent") or {}).get("messages")) if isinstance(trace.get("agent"), dict) else None
    if isinstance(msgs, list) and msgs:
        out: list[Any] = []
        for m in msgs:
            if not isinstance(m, dict):
                continue
            role = m.get("role")
            content = m.get("content")
            if not isinstance(content, str) or not content.strip():
                continue
            content = _truncate_text(content, max_chars=_MAX_TEXT_CHARS)
            if role == "user":
                out.append(HumanMessage(content=content))
            elif role == "assistant":
                out.append(AIMessage(content=content))
            elif role == "tool":
                out.append(ToolMessage(content=content))
        if out:
            return out
    user_input = _extract_user_input(record)
    answer = _extract_answer(trace)
    if user_input and answer:
        user_input = _truncate_text(user_input, max_chars=_MAX_TEXT_CHARS)
        answer = _truncate_text(answer, max_chars=_MAX_TEXT_CHARS)
        return [HumanMessage(content=user_input), AIMessage(content=answer)]
    return None


class RagasFaithfulnessMetric:
    name = "ragas_faithfulness"
    version = "1"
    requirements = MetricRequirement(needs_rag_contexts=True)

    async def evaluate(self, *, record: dict, trace: dict, provider) -> MetricResult:
        contexts = (trace.get("retrieval") or {}).get("contexts")
        context_texts = list(_iter_context_texts(contexts))
        if not context_texts:
            return MetricResult(self.name, "skipped", None, {"reason": "missing trace.retrieval.contexts"}, self.version)
        answer = _extract_answer(trace)
        if not answer:
            return MetricResult(self.name, "skipped", None, {"reason": "missing trace.output.answer"}, self.version)
        answer = _truncate_text(answer, max_chars=_MAX_TEXT_CHARS)
        context_texts = [_truncate_text(t, max_chars=_MAX_TEXT_CHARS) for t in context_texts[:_MAX_CONTEXTS]]
        score = _heuristic_faithfulness(answer=answer, contexts=context_texts)
        return MetricResult(
            self.name,
            "ok",
            float(score),
            {"method": "heuristic", "heuristic": "shingle_overlap", "shingle_n": _HEURISTIC_SHINGLE_N},
            self.version,
        )


class RagasAnswerRelevancyMetric:
    name = "ragas_answer_relevancy"
    version = "1"
    requirements = MetricRequirement(needs_provider_chat=True, needs_provider_embed=True)

    async def evaluate(self, *, record: dict, trace: dict, provider) -> MetricResult:
        user_input = _extract_user_input(record)
        if not user_input:
            return MetricResult(self.name, "skipped", None, {"reason": "missing record input"}, self.version)
        user_input = _truncate_text(user_input, max_chars=_MAX_TEXT_CHARS)
        answer = _extract_answer(trace)
        if not answer:
            return MetricResult(self.name, "skipped", None, {"reason": "missing trace.output.answer"}, self.version)
        answer = _truncate_text(answer, max_chars=_MAX_TEXT_CHARS)
        if provider is None:
            return MetricResult(self.name, "skipped", None, {"reason": "missing provider"}, self.version)
        try:
            llm = _get_ragas_llm(provider)
            embeddings = _get_ragas_embeddings(provider)
        except Exception as e:
            return MetricResult(self.name, "skipped", None, {"reason": str(e)}, self.version)
        score = await _score_single_turn(
            ragas_metric=AnswerRelevancy(),
            sample={"user_input": user_input, "response": answer},
            llm=llm,
            embeddings=embeddings,
        )
        if score is None:
            return MetricResult(self.name, "skipped", None, {"reason": "ragas returned empty score"}, self.version)
        return MetricResult(self.name, "ok", score, {"ragas_metric": "answer_relevancy"}, self.version)


class RagasContextPrecisionMetric:
    name = "ragas_context_precision"
    version = "1"
    requirements = MetricRequirement(needs_provider_chat=True, needs_rag_contexts=True, needs_ground_truth=True)

    async def evaluate(self, *, record: dict, trace: dict, provider) -> MetricResult:
        user_input = _extract_user_input(record)
        if not user_input:
            return MetricResult(self.name, "skipped", None, {"reason": "missing record input"}, self.version)
        user_input = _truncate_text(user_input, max_chars=_MAX_TEXT_CHARS)
        reference = _extract_reference(record)
        if not reference:
            return MetricResult(self.name, "skipped", None, {"reason": "missing record.expected.reference"}, self.version)
        reference = _truncate_text(reference, max_chars=_MAX_TEXT_CHARS)
        contexts = (trace.get("retrieval") or {}).get("contexts")
        context_texts = list(_iter_context_texts(contexts))
        if not context_texts:
            return MetricResult(self.name, "skipped", None, {"reason": "missing trace.retrieval.contexts"}, self.version)
        if provider is None:
            return MetricResult(self.name, "skipped", None, {"reason": "missing provider"}, self.version)
        try:
            llm = _get_ragas_llm(provider)
        except Exception as e:
            return MetricResult(self.name, "skipped", None, {"reason": str(e)}, self.version)
        context_texts = [_truncate_text(t, max_chars=_MAX_TEXT_CHARS) for t in context_texts[:_MAX_CONTEXTS]]
        score = await _score_single_turn(
            ragas_metric=ContextPrecision(),
            sample={"user_input": user_input, "reference": reference, "retrieved_contexts": context_texts},
            llm=llm,
            embeddings=None,
        )
        if score is None:
            return MetricResult(self.name, "skipped", None, {"reason": "ragas returned empty score"}, self.version)
        return MetricResult(self.name, "ok", score, {"ragas_metric": "context_precision"}, self.version)


class RagasContextRecallMetric:
    name = "ragas_context_recall"
    version = "1"
    requirements = MetricRequirement(needs_rag_contexts=True, needs_ground_truth=True)

    async def evaluate(self, *, record: dict, trace: dict, provider) -> MetricResult:
        reference = _extract_reference(record)
        if not reference:
            return MetricResult(self.name, "skipped", None, {"reason": "missing record.expected.reference"}, self.version)
        reference = _truncate_text(reference, max_chars=_MAX_TEXT_CHARS)
        contexts = (trace.get("retrieval") or {}).get("contexts")
        context_texts = list(_iter_context_texts(contexts))
        if not context_texts:
            return MetricResult(self.name, "skipped", None, {"reason": "missing trace.retrieval.contexts"}, self.version)
        context_texts = [_truncate_text(t, max_chars=_MAX_TEXT_CHARS) for t in context_texts[:_MAX_CONTEXTS]]
        score = _heuristic_context_recall(reference=reference, contexts=context_texts)
        return MetricResult(
            self.name,
            "ok",
            float(score),
            {"method": "heuristic", "heuristic": "shingle_overlap", "shingle_n": _HEURISTIC_SHINGLE_N},
            self.version,
        )


class RagasAnswerCorrectnessMetric:
    name = "ragas_answer_correctness"
    version = "1"
    requirements = MetricRequirement(needs_provider_chat=True, needs_provider_embed=True, needs_ground_truth=True)

    async def evaluate(self, *, record: dict, trace: dict, provider) -> MetricResult:
        user_input = _extract_user_input(record)
        if not user_input:
            return MetricResult(self.name, "skipped", None, {"reason": "missing record input"}, self.version)
        reference = _extract_reference(record)
        if not reference:
            return MetricResult(self.name, "skipped", None, {"reason": "missing record.expected.reference"}, self.version)
        answer = _extract_answer(trace)
        if not answer:
            return MetricResult(self.name, "skipped", None, {"reason": "missing trace.output.answer"}, self.version)
        if reference.strip() == answer.strip():
            return MetricResult(self.name, "ok", 1.0, {"ragas_metric": "answer_correctness", "shortcut": "reference_equals_answer"}, self.version)
        user_input = _truncate_text(user_input, max_chars=_MAX_TEXT_CHARS)
        reference = _truncate_text(reference, max_chars=_MAX_TEXT_CHARS)
        answer = _truncate_text(answer, max_chars=_MAX_TEXT_CHARS)
        if provider is None:
            return MetricResult(self.name, "skipped", None, {"reason": "missing provider"}, self.version)
        try:
            llm = _get_ragas_llm(provider)
            embeddings = _get_ragas_embeddings(provider)
        except Exception as e:
            return MetricResult(self.name, "skipped", None, {"reason": str(e)}, self.version)
        score = await _score_single_turn(
            ragas_metric=AnswerCorrectness(),
            sample={"user_input": user_input, "response": answer, "reference": reference},
            llm=llm,
            embeddings=embeddings,
        )
        if score is None:
            return MetricResult(self.name, "skipped", None, {"reason": "ragas returned empty score"}, self.version)
        return MetricResult(self.name, "ok", score, {"ragas_metric": "answer_correctness"}, self.version)


class RagasAgentGoalAccuracyMetric:
    name = "ragas_agent_goal_accuracy"
    version = "1"
    requirements = MetricRequirement(needs_provider_chat=True)

    async def evaluate(self, *, record: dict, trace: dict, provider) -> MetricResult:
        if provider is None:
            return MetricResult(self.name, "skipped", None, {"reason": "missing provider"}, self.version)
        try:
            llm = _get_ragas_llm(provider)
        except Exception as e:
            return MetricResult(self.name, "skipped", None, {"reason": str(e)}, self.version)

        messages = _messages_from_trace(record=record, trace=trace)
        if not messages:
            return MetricResult(self.name, "skipped", None, {"reason": "missing trace.agent.messages"}, self.version)

        sample = MultiTurnSample(user_input=messages).model_dump()
        ds = EvaluationDataset.from_list([sample])
        metric = AgentGoalAccuracyWithoutReference()
        result = await aevaluate(dataset=ds, metrics=[metric], llm=llm, embeddings=None, show_progress=False)
        if not result.scores:
            return MetricResult(self.name, "skipped", None, {"reason": "ragas returned empty score"}, self.version)
        score = result.scores[0].get(metric.name)
        if score is None or _is_nan(score):
            return MetricResult(self.name, "skipped", None, {"reason": "ragas returned empty score"}, self.version)
        return MetricResult(self.name, "ok", float(score), {"ragas_metric": metric.name}, self.version)
