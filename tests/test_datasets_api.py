from fastapi.testclient import TestClient

from app.main import create_app


def test_upload_dataset_prompt_ok(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_SQLITE_PATH", str(tmp_path / "app.db"))
    monkeypatch.setenv("APP_DATASET_DIR", str(tmp_path / "datasets"))

    app = create_app()
    client = TestClient(app)

    content = b'{"type":"prompt","input":{"user_input":"hi"}}\n'

    resp = client.post(
        "/datasets",
        files={"file": ("ds.jsonl", content, "application/jsonl")},
        data={"name": "ds1", "eval_type": "prompt"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "dataset_id" in body
    assert body["records_count"] == 1
    assert body["eval_type"] == "prompt"


def test_upload_dataset_schema_error_returns_422(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_SQLITE_PATH", str(tmp_path / "app.db"))
    monkeypatch.setenv("APP_DATASET_DIR", str(tmp_path / "datasets"))

    app = create_app()
    client = TestClient(app)

    content = b'{"type":"prompt","input":{"system_prompt":"x"}}\n'
    resp = client.post(
        "/datasets",
        files={"file": ("ds.jsonl", content, "application/jsonl")},
        data={"eval_type": "prompt"},
    )
    assert resp.status_code == 422, resp.text
