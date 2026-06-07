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
    assert status == "succeeded"

    items_resp = client.get(f"/runs/{run_id}/items")
    assert items_resp.status_code == 200, items_resp.text
    items = items_resp.json()["items"]
    assert len(items) == 1
    assert items[0]["record_id"]

    jsonl_resp = client.get(f"/runs/{run_id}/export", params={"format": "jsonl"})
    assert jsonl_resp.status_code == 200
    assert jsonl_resp.text.strip().startswith("{")

    csv_resp = client.get(f"/runs/{run_id}/export", params={"format": "csv"})
    assert csv_resp.status_code == 200
    assert "record_id" in csv_resp.text.splitlines()[0]

    json_resp = client.get(f"/runs/{run_id}/export", params={"format": "json"})
    assert json_resp.status_code == 200
    body = json_resp.json()
    assert body["run"]["run_id"] == run_id


def test_create_run_without_sut_defaults_to_dataset_adapter(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_SQLITE_PATH", str(tmp_path / "app.db"))
    monkeypatch.setenv("APP_DATASET_DIR", str(tmp_path / "datasets"))

    app = create_app()
    client = TestClient(app)

    ds_content = b'{"type":"prompt","input":{"user_input":"hi"},"trace":{"output":{"answer":"ok"}}}\n'
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
            "execution": {"max_concurrency": 1, "timeout_seconds": 1, "save_artifacts": False},
        },
    )
    assert run_resp.status_code == 200, run_resp.text

    from app.db.models import Run

    with app.state.SessionLocal() as session:
        run = session.get(Run, run_resp.json()["run_id"])
        assert run is not None
        assert run.config_snapshot_json["sut"]["adapter_name"] == "dataset"


def test_dataset_adapter_uses_record_trace_output_and_fails_when_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_SQLITE_PATH", str(tmp_path / "app.db"))
    monkeypatch.setenv("APP_DATASET_DIR", str(tmp_path / "datasets"))

    app = create_app()

    class OutputPresentMetric:
        name = "output_present"
        version = "1"
        requirements = type("Req", (), {})()

        async def evaluate(self, *, record, trace, provider):
            ok = isinstance(trace, dict) and isinstance(trace.get("output"), dict) and bool(trace["output"])
            status = "ok" if ok else "failed"
            score = 1.0 if ok else 0.0
            return type(
                "MetricResultObj",
                (),
                {"__dict__": {"name": self.name, "status": status, "score": score, "details": {}, "version": self.version}},
            )()

    app.state.registry.register_metric(OutputPresentMetric)
    client = TestClient(app)

    ds_content = (
        b'{"record_id":"r1","type":"prompt","input":{"user_input":"hi"},"output":{"answer":"ok"},"trace":{"messages":[]}}\n'
        b'{"record_id":"r2","type":"prompt","input":{"user_input":"hi2"}}\n'
    )
    ds_resp = client.post("/datasets", files={"file": ("ds.jsonl", ds_content, "application/jsonl")}, data={"eval_type": "prompt"})
    assert ds_resp.status_code == 200, ds_resp.text
    dataset_id = ds_resp.json()["dataset_id"]

    run_resp = client.post(
        "/runs",
        json={
            "dataset_id": dataset_id,
            "eval_type": "prompt",
            "metrics": [{"metric_name": "output_present", "metric_config": {}}],
            "provider_ref": {"provider_name": "none", "config": {}},
            "execution": {"max_concurrency": 1, "timeout_seconds": 2, "save_artifacts": False},
        },
    )
    assert run_resp.status_code == 200, run_resp.text
    run_id = run_resp.json()["run_id"]

    start_resp = client.post(f"/runs/{run_id}/start")
    assert start_resp.status_code == 200, start_resp.text

    for _ in range(200):
        status = client.get(f"/runs/{run_id}").json()["status"]
        if status in ("succeeded", "failed"):
            break
        time.sleep(0.01)
    assert status == "failed"

    items_resp = client.get(f"/runs/{run_id}/items")
    assert items_resp.status_code == 200, items_resp.text
    items = sorted(items_resp.json()["items"], key=lambda x: x["record_id"])
    assert [it["record_id"] for it in items] == ["r1", "r2"]

    assert items[0]["status"] == "succeeded"
    assert items[0]["output"] == {"answer": "ok"}
    assert items[0]["metrics"][0]["status"] == "ok"

    assert items[1]["status"] == "failed"
    assert items[1]["error"]["type"]


def test_run_failed_when_provider_env_missing_reports_error_item(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_SQLITE_PATH", str(tmp_path / "app.db"))
    monkeypatch.setenv("APP_DATASET_DIR", str(tmp_path / "datasets"))
    monkeypatch.delenv("ARK_API_KEY_TEST", raising=False)

    app = create_app()
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
            "sut": {"adapter_name": "http", "adapter_config": {"base_url": "http://127.0.0.1:9000", "timeout_seconds": 1}},
            "metrics": [{"metric_name": "ragas_answer_relevancy", "metric_config": {}}],
            "provider_ref": {"provider_name": "ark", "config": {"api_key_env": "ARK_API_KEY_TEST"}},
            "execution": {"max_concurrency": 1, "timeout_seconds": 1, "save_artifacts": False},
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
    assert status == "failed"

    items_resp = client.get(f"/runs/{run_id}/items")
    assert items_resp.status_code == 200, items_resp.text
    items = items_resp.json()["items"]
    assert len(items) == 1
    assert items[0]["record_id"] == "__run__"
    assert items[0]["error"]["type"]
    assert "ARK_API_KEY" in (items[0]["error"]["message"] or "")
