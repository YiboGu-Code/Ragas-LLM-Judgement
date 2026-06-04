import json
import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def test_save_artifacts_redacts_sensitive_strings(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_SQLITE_PATH", str(tmp_path / "app.db"))
    monkeypatch.setenv("APP_DATASET_DIR", str(tmp_path / "datasets"))
    monkeypatch.setenv("APP_ARTIFACT_DIR", str(tmp_path / "artifacts"))

    app = create_app()

    class RedactionAdapter:
        name = "redaction_adapter"

        async def execute(self, *, record, provider):
            return {
                "output": {"final": "ok"},
                "trace": {
                    "messages": [
                        {"role": "user", "content": "token sk-THISISASECRET1234567890"},
                    ]
                },
            }

    app.state.registry.register_sut_adapter(RedactionAdapter)

    client = TestClient(app)
    ds_content = b'{"type":"prompt","input":{"user_input":"hi"}}\n'
    ds_resp = client.post("/datasets", files={"file": ("ds.jsonl", ds_content, "application/jsonl")}, data={"eval_type": "prompt"})
    dataset_id = ds_resp.json()["dataset_id"]

    run_resp = client.post(
        "/runs",
        json={
            "dataset_id": dataset_id,
            "eval_type": "prompt",
            "sut": {"adapter_name": "redaction_adapter", "adapter_config": {}},
            "metrics": [],
            "provider_ref": {"provider_name": "manual", "config": {}},
            "execution": {"max_concurrency": 1, "timeout_seconds": 5, "save_artifacts": True},
        },
    )
    run_id = run_resp.json()["run_id"]
    client.post(f"/runs/{run_id}/start")

    for _ in range(200):
        status = client.get(f"/runs/{run_id}").json()["status"]
        if status in ("succeeded", "failed"):
            break
        time.sleep(0.01)
    assert status == "succeeded"

    items = client.get(f"/runs/{run_id}/items").json()["items"]
    assert len(items) == 1
    trace_ref = items[0]["trace_ref"]
    assert trace_ref

    payload = json.loads(Path(trace_ref).read_text(encoding="utf-8"))
    body = json.dumps(payload, ensure_ascii=False)
    assert "sk-THISISASECRET1234567890" not in body
    assert "[REDACTED]" in body


def test_save_artifacts_false_does_not_write_files(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_SQLITE_PATH", str(tmp_path / "app.db"))
    monkeypatch.setenv("APP_DATASET_DIR", str(tmp_path / "datasets"))
    monkeypatch.setenv("APP_ARTIFACT_DIR", str(tmp_path / "artifacts"))

    app = create_app()

    class SimpleAdapter:
        name = "simple_adapter"

        async def execute(self, *, record, provider):
            return {"output": {"final": "ok"}, "trace": {"messages": [{"role": "user", "content": "sk-SECRET1234567890"}]}}

    app.state.registry.register_sut_adapter(SimpleAdapter)

    client = TestClient(app)
    ds_content = b'{"type":"prompt","input":{"user_input":"hi"}}\n'
    ds_resp = client.post("/datasets", files={"file": ("ds.jsonl", ds_content, "application/jsonl")}, data={"eval_type": "prompt"})
    dataset_id = ds_resp.json()["dataset_id"]

    run_resp = client.post(
        "/runs",
        json={
            "dataset_id": dataset_id,
            "eval_type": "prompt",
            "sut": {"adapter_name": "simple_adapter", "adapter_config": {}},
            "metrics": [],
            "provider_ref": {"provider_name": "manual", "config": {}},
            "execution": {"max_concurrency": 1, "timeout_seconds": 5, "save_artifacts": False},
        },
    )
    run_id = run_resp.json()["run_id"]
    client.post(f"/runs/{run_id}/start")

    for _ in range(200):
        status = client.get(f"/runs/{run_id}").json()["status"]
        if status in ("succeeded", "failed"):
            break
        time.sleep(0.01)
    assert status == "succeeded"

    items = client.get(f"/runs/{run_id}/items").json()["items"]
    assert len(items) == 1
    assert items[0]["trace_ref"] is None
    assert not (tmp_path / "artifacts").exists() or not any((tmp_path / "artifacts").rglob("*.json"))
