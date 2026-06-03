from __future__ import annotations

from app.plugins.interfaces import MetricRequirement, MetricResult


class RagContextsPresentMetric:
    name = "rag_contexts_present"
    version = "1"
    requirements = MetricRequirement(needs_rag_contexts=True)

    async def evaluate(self, *, record: dict, trace: dict, provider) -> MetricResult:
        contexts = (trace.get("retrieval") or {}).get("contexts")
        if contexts is None:
            return MetricResult(
                name=self.name,
                status="skipped",
                score=None,
                details={"reason": "missing trace.retrieval.contexts"},
                version=self.version,
            )
        return MetricResult(
            name=self.name,
            status="ok",
            score=1.0 if len(contexts) > 0 else 0.0,
            details={"contexts_count": len(contexts)},
            version=self.version,
        )
