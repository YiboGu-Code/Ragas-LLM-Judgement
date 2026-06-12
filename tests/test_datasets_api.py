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


def test_list_datasets_returns_shared_uploaded_datasets(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_SQLITE_PATH", str(tmp_path / "app.db"))
    monkeypatch.setenv("APP_DATASET_DIR", str(tmp_path / "datasets"))

    app = create_app()
    client = TestClient(app)

    first = client.post(
        "/datasets",
        files={"file": ("first.jsonl", b'{"type":"prompt","input":{"user_input":"first"}}\n', "application/jsonl")},
        data={"name": "first-dataset", "eval_type": "prompt"},
    )
    assert first.status_code == 200, first.text

    second = client.post(
        "/datasets",
        files={"file": ("second.jsonl", b'{"type":"prompt","input":{"user_input":"second"}}\n', "application/jsonl")},
        data={"name": "second-dataset", "eval_type": "prompt"},
    )
    assert second.status_code == 200, second.text

    resp = client.get("/datasets")
    assert resp.status_code == 200, resp.text

    body = resp.json()
    assert [item["name"] for item in body["items"]] == ["second-dataset", "first-dataset"]
    assert body["items"][0]["dataset_id"] == second.json()["dataset_id"]
    assert body["items"][1]["dataset_id"] == first.json()["dataset_id"]
    assert body["items"][0]["records_count"] == 1
    assert body["items"][0]["created_at"]


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
