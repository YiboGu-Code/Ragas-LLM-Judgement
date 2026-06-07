from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def test_delete_dataset_removes_db_row_and_raw_file(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_SQLITE_PATH", str(tmp_path / "app.db"))
    monkeypatch.setenv("APP_DATASET_DIR", str(tmp_path / "datasets"))

    app = create_app()
    client = TestClient(app)

    ds_content = b'{"record_id":"p1","type":"prompt","input":{"user_input":"hi"},"trace":{"output":{"answer":"ok"}}}\n'
    ds_resp = client.post("/datasets", files={"file": ("ds.jsonl", ds_content, "application/jsonl")}, data={"eval_type": "prompt"})
    assert ds_resp.status_code == 200, ds_resp.text
    dataset_id = ds_resp.json()["dataset_id"]

    raw_path = Path(tmp_path / "datasets" / f"{dataset_id}.jsonl")
    assert raw_path.exists()

    delete_resp = client.delete(f"/datasets/{dataset_id}")
    assert delete_resp.status_code == 204, delete_resp.text

    assert client.get(f"/datasets/{dataset_id}").status_code == 404
    assert not raw_path.exists()


def test_delete_dataset_rejected_when_referenced_by_run(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_SQLITE_PATH", str(tmp_path / "app.db"))
    monkeypatch.setenv("APP_DATASET_DIR", str(tmp_path / "datasets"))

    app = create_app()
    client = TestClient(app)

    ds_content = b'{"record_id":"p1","type":"prompt","input":{"user_input":"hi"},"trace":{"output":{"answer":"ok"}}}\n'
    ds_resp = client.post("/datasets", files={"file": ("ds.jsonl", ds_content, "application/jsonl")}, data={"eval_type": "prompt"})
    assert ds_resp.status_code == 200, ds_resp.text
    dataset_id = ds_resp.json()["dataset_id"]

    run_resp = client.post(
        "/runs",
        json={
            "dataset_id": dataset_id,
            "eval_type": "prompt",
            "metrics": [{"metric_name": "ragas_answer_relevancy", "metric_config": {}}],
            "provider_ref": {"provider_name": "none", "config": {}},
            "execution": {"max_concurrency": 1, "timeout_seconds": 2, "save_artifacts": False},
        },
    )
    assert run_resp.status_code == 200, run_resp.text

    delete_resp = client.delete(f"/datasets/{dataset_id}")
    assert delete_resp.status_code == 409, delete_resp.text


def test_delete_dataset_404_when_not_found(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_SQLITE_PATH", str(tmp_path / "app.db"))
    monkeypatch.setenv("APP_DATASET_DIR", str(tmp_path / "datasets"))

    app = create_app()
    client = TestClient(app)

    resp = client.delete("/datasets/not-found")
    assert resp.status_code == 404, resp.text

