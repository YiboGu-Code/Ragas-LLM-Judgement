import time

from fastapi.testclient import TestClient

from app.main import create_app


def test_delete_run_removes_db_rows_and_artifacts(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_SQLITE_PATH", str(tmp_path / "app.db"))
    monkeypatch.setenv("APP_DATASET_DIR", str(tmp_path / "datasets"))
    monkeypatch.setenv("APP_ARTIFACT_DIR", str(tmp_path / "artifacts"))

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
            "execution": {"max_concurrency": 1, "timeout_seconds": 2, "save_artifacts": True, "artifact_redaction": "default_v1"},
        },
    )
    assert run_resp.status_code == 200, run_resp.text
    run_id = run_resp.json()["run_id"]

    start_resp = client.post(f"/runs/{run_id}/start")
    assert start_resp.status_code == 200, start_resp.text

    for _ in range(200):
        status = client.get(f"/runs/{run_id}").json()["status"]
        if status in ("succeeded", "failed", "canceled"):
            break
        time.sleep(0.01)
    assert status in ("succeeded", "failed", "canceled")

    from pathlib import Path

    artifact_root = Path(tmp_path / "artifacts" / run_id)
    assert artifact_root.exists()

    delete_resp = client.delete(f"/runs/{run_id}")
    assert delete_resp.status_code == 204, delete_resp.text

    assert client.get(f"/runs/{run_id}").status_code == 404
    assert client.get(f"/runs/{run_id}/items").status_code == 404
    assert client.get(f"/runs/{run_id}/export", params={"format": "json"}).status_code == 404

    assert not artifact_root.exists()


def test_delete_run_rejected_when_running(tmp_path, monkeypatch):
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
    run_id = run_resp.json()["run_id"]

    from app.db.models import Run

    with app.state.SessionLocal() as session:
        run = session.get(Run, run_id)
        assert run is not None
        run.status = "running"
        session.commit()

    delete_resp = client.delete(f"/runs/{run_id}")
    assert delete_resp.status_code == 409, delete_resp.text

