from __future__ import annotations

from sqlalchemy.engine import Engine

from app.db.models import Base


def create_all(engine: Engine) -> None:
    Base.metadata.create_all(bind=engine)
