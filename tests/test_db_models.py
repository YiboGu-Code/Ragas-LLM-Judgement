from app.db.migrate import create_all
from app.db.models import Dataset
from app.db.session import create_engine_and_sessionmaker


def test_can_create_tables_and_insert_dataset(tmp_path):
    db_path = tmp_path / "test.db"
    engine, SessionLocal = create_engine_and_sessionmaker(sqlite_path=str(db_path))
    create_all(engine)

    with SessionLocal() as session:
        ds = Dataset(
            id="ds1",
            name="n",
            eval_type="prompt",
            schema_version="v1",
            records_count=1,
            raw_path=None,
        )
        session.add(ds)
        session.commit()

    with SessionLocal() as session:
        loaded = session.get(Dataset, "ds1")
        assert loaded is not None
        assert loaded.eval_type == "prompt"
