from __future__ import annotations

from app.plugins.interfaces import MetricRequirement, MetricResult


def _has_method(obj, name: str) -> bool:
    return callable(getattr(obj, name, None))


class RagasFaithfulnessMetric:
    name = "ragas_faithfulness"
    version = "1"
    requirements = MetricRequirement(needs_provider_chat=True, needs_provider_embed=True, needs_rag_contexts=True)

    async def evaluate(self, *, record: dict, trace: dict, provider) -> MetricResult:
        contexts = (trace.get("retrieval") or {}).get("contexts")
        if not contexts:
            return MetricResult(self.name, "skipped", None, {"reason": "missing trace.retrieval.contexts"}, self.version)
        answer = (trace.get("output") or {}).get("answer")
        if not answer:
            return MetricResult(self.name, "skipped", None, {"reason": "missing trace.output.answer"}, self.version)
        if provider is None:
            return MetricResult(self.name, "skipped", None, {"reason": "missing provider"}, self.version)
        if not _has_method(provider, "chat") or not _has_method(provider, "embed"):
            return MetricResult(self.name, "skipped", None, {"reason": "provider missing chat/embed"}, self.version)
        return MetricResult(self.name, "skipped", None, {"reason": "ragas integration not wired yet"}, self.version)


class RagasAnswerRelevancyMetric:
    name = "ragas_answer_relevancy"
    version = "1"
    requirements = MetricRequirement(needs_provider_chat=True)

    async def evaluate(self, *, record: dict, trace: dict, provider) -> MetricResult:
        question = (record.get("input") or {}).get("question")
        if not question:
            return MetricResult(self.name, "skipped", None, {"reason": "missing record.input.question"}, self.version)
        answer = (trace.get("output") or {}).get("answer")
        if not answer:
            return MetricResult(self.name, "skipped", None, {"reason": "missing trace.output.answer"}, self.version)
        if provider is None:
            return MetricResult(self.name, "skipped", None, {"reason": "missing provider"}, self.version)
        if not _has_method(provider, "chat"):
            return MetricResult(self.name, "skipped", None, {"reason": "provider missing chat"}, self.version)
        return MetricResult(self.name, "skipped", None, {"reason": "ragas integration not wired yet"}, self.version)
