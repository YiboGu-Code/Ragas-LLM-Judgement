import time

from fastapi.testclient import TestClient

from app.main import create_app


def test_create_and_run(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_SQLITE_PATH", str(tmp_path / "app.db"))
    monkeypatch.setenv("APP_DATASET_DIR", str(tmp_path / "datasets"))

    app = create_app()

    class DummyAdapter:
        name = "dummy"

        async def execute(self, *, record, provider):
            return {"output": {"final": record["input"]["user_input"]}, "trace": {"messages": []}}

    class DummyMetric:
        name = "dummy_metric"
        version = "1"
        requirements = type("Req", (), {})()

        async def evaluate(self, *, record, trace, provider):
            return type(
                "MetricResultObj",
                (),
                {"__dict__": {"name": self.name, "status": "ok", "score": 1.0, "details": {}, "version": self.version}},
            )()

    app.state.registry.register_sut_adapter(DummyAdapter)
    app.state.registry.register_metric(DummyMetric)

    client = TestClient(app)

    ds_content = b'{"type":"prompt","input":{"user_input":"hi"}}\n'
    ds_resp = client.post("/datasets", files={"file": ("ds.jsonl", ds_content, "application/jsonl")}, data={"eval_type": "prompt"})
    assert ds_resp.status_code == 200, ds_resp.text
    dataset_id = ds_resp.json()["dataset_id"]

    run_resp = client.post(
        "/runs",
        json={
            "dataset_id": dataset_id,
            "eval_type": "prompt",
            "sut": {"adapter_name": "dummy", "adapter_config": {}},
            "metrics": [{"metric_name": "dummy_metric", "metric_config": {}}],
            "provider_ref": {"provider_name": "manual", "config": {}},
            "execution": {"max_concurrency": 2, "timeout_seconds": 5, "save_artifacts": False},
        },
    )
    assert run_resp.status_code == 200, run_resp.text
    run_id = run_resp.json()["run_id"]

    start_resp = client.post(f"/runs/{run_id}/start")
    assert start_resp.status_code == 200, start_resp.text

    for _ in range(100):
        status = client.get(f"/runs/{run_id}").json()["status"]
        if status in ("succeeded", "failed"):
            break
        time.sleep(0.01)

    items_resp = client.get(f"/runs/{run_id}/items")
    assert items_resp.status_code == 200, items_resp.text
    items = items_resp.json()["items"]
    assert len(items) == 1
    assert items[0]["record_id"]
