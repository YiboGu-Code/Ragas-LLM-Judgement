from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from app.core.config import Settings
from app.db.migrate import create_all
from app.db.session import create_engine_and_sessionmaker
from app.plugins.registry import PluginRegistry


def create_app() -> FastAPI:
    settings = Settings()

    sqlite_path = Path(settings.sqlite_path)
    if sqlite_path.parent != Path("."):
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)

    engine, SessionLocal = create_engine_and_sessionmaker(sqlite_path=settings.sqlite_path)
    create_all(engine)

    app = FastAPI(title="LLM Eval Backend", version="0.1.0")
    app.state.settings = settings
    app.state.SessionLocal = SessionLocal
    app.state.registry = PluginRegistry()

    from app.metrics.basic import RagContextsPresentMetric
    from app.metrics.ragas_metrics import (
        RagasAgentGoalAccuracyMetric,
        RagasAnswerCorrectnessMetric,
        RagasAnswerRelevancyMetric,
        RagasContextPrecisionMetric,
        RagasContextRecallMetric,
        RagasFaithfulnessMetric,
    )
    from app.providers import ArkProvider
    from app.sut.http_adapter import HttpSUTAdapter

    app.state.registry.register_metric(RagContextsPresentMetric)
    app.state.registry.register_metric(RagasFaithfulnessMetric)
    app.state.registry.register_metric(RagasAnswerRelevancyMetric)
    app.state.registry.register_metric(RagasContextPrecisionMetric)
    app.state.registry.register_metric(RagasContextRecallMetric)
    app.state.registry.register_metric(RagasAnswerCorrectnessMetric)
    app.state.registry.register_metric(RagasAgentGoalAccuracyMetric)
    app.state.registry.register_sut_adapter(HttpSUTAdapter)
    app.state.registry.register_provider(ArkProvider)

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    from app.api.datasets import router as datasets_router
    from app.api.runs import router as runs_router

    app.include_router(datasets_router)
    app.include_router(runs_router)

    return app


app = create_app()
