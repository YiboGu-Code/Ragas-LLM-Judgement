from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from app.core.config import Settings
from app.db.migrate import create_all
from app.db.session import create_engine_and_sessionmaker


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

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    from app.api.datasets import router as datasets_router

    app.include_router(datasets_router)

    return app


app = create_app()
