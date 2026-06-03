# Ragas LLM 测评平台（后端）实现计划

> **面向 AI 代理的工作者：** 推荐使用 superpowers:subagent-driven-development 逐任务实现本计划；每个任务完成后触发两阶段评审（spec 合规 → 代码质量）。步骤使用复选框（`- [ ]`）语法跟踪进度，并在完成后补充对应 commit hash。

**目标：** 实现一个仅后端的通用测评平台：支持 Dataset(JSONL) 上传与严格 schema 校验；支持创建/启动/查询/取消评测 Run；支持 Prompt/RAG/Workflow/Agent 四类评测的统一输入/输出；支持可插拔的 ModelProvider / SUTAdapter / Metric；默认 SQLite 持久化与本地 artifacts；支持结果导出 JSONL/CSV/JSON；提供 Docker 与 CI。

**架构：** FastAPI HTTP API + 进程内异步执行引擎（基于 asyncio 并发）+ SQLite（SQLAlchemy）+ 本地 artifacts 存储；通过 registry 注册插件（provider/sut/metric）。

**技术栈：** Python 3.11、FastAPI、Uvicorn、Pydantic、SQLAlchemy 2、pytest、httpx、ragas（用于部分 RAG 指标）。

---

## 进度（持续更新）

- [x] 任务 1：初始化仓库与 Python 依赖（commit: e871524）
- [x] 任务 2：插件接口与 registry（commit: 857a961）
- [x] 任务 3：四类评测 Dataset JSONL schema 与校验（commit: 71d88d5）
- [x] 任务 4：SQLite ORM 数据模型与 create_all（commit: 39df4a2）
- [x] 任务 5：FastAPI app + /healthz（commit: 9b7a8f0）
- [x] 任务 6：Dataset 上传/查询 API（commit: b9050a2）
- [x] 任务 7：HTTP SUTAdapter（commit: 4e5cfdb）
- [x] 任务 8：进程内异步 RunEngine（commit: 5ae7a9b）
- [x] 任务 9：基础指标与严格 skipped 规则（commit: a8411cf）
- [x] 任务 10：Ragas 指标封装（requirements + skipped）（commit: 94b30c7）
- [x] 任务 11：Run 生命周期 API（commit: c88f014）
- [ ] 任务 12：导出 API（jsonl/csv/json）
- [ ] 任务 13：脱敏与 artifacts 开关
- [ ] 任务 14：Dockerfile + GitHub Actions CI
- [ ] 任务 15：最终验证 + push GitHub

## 0. 预期目录结构（实现后）

- `app/main.py`：FastAPI 应用入口，路由注册
- `app/core/config.py`：配置（路径、并发度、开关）
- `app/db/`：SQLite 连接与 ORM
  - `app/db/session.py`
  - `app/db/models.py`
- `app/schemas/`：Pydantic request/response schema
- `app/datasets/`：JSONL 解析与 schema 校验
  - `app/datasets/records.py`
  - `app/datasets/validator.py`
- `app/plugins/`：接口定义与 registry
  - `app/plugins/interfaces.py`
  - `app/plugins/registry.py`
- `app/execution/`：run 执行引擎
  - `app/execution/engine.py`
  - `app/execution/types.py`
- `app/metrics/`：内置指标
  - `app/metrics/base.py`
  - `app/metrics/basic.py`
  - `app/metrics/ragas_metrics.py`
- `app/sut/`：内置 SUT 适配器（最少提供“示例/占位”与 HTTP 回调适配）
  - `app/sut/base.py`
  - `app/sut/http_adapter.py`
- `data/datasets/`：上传数据集原始文件（可配置开关）
- `artifacts/`：每条 record 的 trace 制品（可配置开关）
- `tests/`：pytest 测试
- `requirements.txt`、`requirements-dev.txt`
- `Dockerfile`
- `.github/workflows/ci.yml`

---

## 1. 任务 1：初始化仓库与 Python 依赖

**目标：** 让工程能被安装、测试、运行，并为后续 TDD 提供基础环境。

**文件：**

- 创建：`requirements.txt`
- 创建：`requirements-dev.txt`
- 创建：`.gitignore`
- 创建：`app/__init__.py`
- 创建：`tests/__init__.py`

- [ ] **步骤 1：创建 requirements**

`requirements.txt` 内容：

```txt
fastapi==0.115.0
uvicorn==0.30.6
pydantic==2.8.2
pydantic-settings==2.4.0
sqlalchemy==2.0.34
python-multipart==0.0.9
ragas==0.1.14
numpy==1.26.4
```

`requirements-dev.txt` 内容：

```txt
pytest==8.3.2
httpx==0.27.2
ruff==0.6.8
```

- [ ] **步骤 2：创建 .gitignore**

`.gitignore` 内容：

```gitignore
__pycache__/
*.pyc
.pytest_cache/
.ruff_cache/
.venv/
.env
data/
artifacts/
*.db
```

- [ ] **步骤 3：创建包目录占位文件**

创建空文件：

- `app/__init__.py`
- `tests/__init__.py`

- [ ] **步骤 4：验证安装与测试框架可运行（本地）**

运行：

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
pytest -q
```

预期：pytest 运行但提示 0 tests（后续会补 tests）。

- [ ] **步骤 5：Commit**

```bash
git init
git add requirements.txt requirements-dev.txt .gitignore app/__init__.py tests/__init__.py
git commit -m "chore: bootstrap python backend skeleton"
```

---

## 2. 任务 2：定义核心类型与插件接口（ModelProvider / SUTAdapter / Metric）

**目标：** 固化通用抽象层，使平台不依赖任何具体模型/业务实现。

**文件：**

- 创建：`app/plugins/interfaces.py`
- 创建：`app/plugins/registry.py`
- 创建：`app/execution/types.py`
- 测试：`tests/test_plugin_registry.py`

- [ ] **步骤 1：编写失败测试（registry 能注册与获取）**

`tests/test_plugin_registry.py`：

```python
import pytest

from app.plugins.registry import PluginRegistry


def test_registry_can_register_and_get_metric():
    registry = PluginRegistry()

    class MyMetric:
        name = "my_metric"

    registry.register_metric(MyMetric)
    metric_cls = registry.get_metric("my_metric")
    assert metric_cls is MyMetric


def test_registry_unknown_plugin_raises_key_error():
    registry = PluginRegistry()
    with pytest.raises(KeyError):
        registry.get_metric("missing")
```

- [ ] **步骤 2：运行测试验证失败**

运行：

```bash
pytest -q
```

预期：FAIL，提示 `ModuleNotFoundError: app.plugins.registry`。

- [ ] **步骤 3：实现 interfaces 与 registry（最小让测试通过）**

`app/plugins/interfaces.py`：

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class MetricRequirement:
    needs_provider_chat: bool = False
    needs_provider_embed: bool = False
    needs_rag_contexts: bool = False
    needs_ground_truth: bool = False


@dataclass(frozen=True)
class MetricResult:
    name: str
    status: str
    score: float | None
    details: dict[str, Any]
    version: str


@runtime_checkable
class ModelProvider(Protocol):
    name: str

    async def chat(self, *, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]: ...

    async def embed(self, *, texts: list[str], **kwargs: Any) -> list[list[float]]: ...


@runtime_checkable
class Metric(Protocol):
    name: str
    version: str
    requirements: MetricRequirement

    async def evaluate(self, *, record: dict[str, Any], trace: dict[str, Any], provider: ModelProvider | None) -> MetricResult: ...


@runtime_checkable
class SUTAdapter(Protocol):
    name: str

    async def execute(self, *, record: dict[str, Any], provider: ModelProvider | None) -> dict[str, Any]: ...
```

`app/plugins/registry.py`：

```python
from __future__ import annotations

from typing import Any, Type


class PluginRegistry:
    def __init__(self) -> None:
        self._metrics: dict[str, Type[Any]] = {}
        self._sut_adapters: dict[str, Type[Any]] = {}
        self._providers: dict[str, Type[Any]] = {}

    def register_metric(self, metric_cls: Type[Any]) -> None:
        name = getattr(metric_cls, "name", None)
        if not name:
            raise ValueError("metric_cls.name is required")
        self._metrics[str(name)] = metric_cls

    def get_metric(self, name: str) -> Type[Any]:
        return self._metrics[name]

    def register_sut_adapter(self, adapter_cls: Type[Any]) -> None:
        name = getattr(adapter_cls, "name", None)
        if not name:
            raise ValueError("adapter_cls.name is required")
        self._sut_adapters[str(name)] = adapter_cls

    def get_sut_adapter(self, name: str) -> Type[Any]:
        return self._sut_adapters[name]

    def register_provider(self, provider_cls: Type[Any]) -> None:
        name = getattr(provider_cls, "name", None)
        if not name:
            raise ValueError("provider_cls.name is required")
        self._providers[str(name)] = provider_cls

    def get_provider(self, name: str) -> Type[Any]:
        return self._providers[name]
```

- [ ] **步骤 4：运行测试验证通过**

```bash
pytest -q
```

预期：PASS。

- [ ] **步骤 5：Commit**

```bash
git add app/plugins/interfaces.py app/plugins/registry.py tests/test_plugin_registry.py
git commit -m "feat: add plugin interfaces and registry"
```

---

## 3. 任务 3：定义 Dataset Record 的严格 schema（四类评测）

**目标：** 让输入约束可机器校验，失败时返回精确行号与原因。

**文件：**

- 创建：`app/datasets/records.py`
- 创建：`app/datasets/validator.py`
- 测试：`tests/test_dataset_validation.py`

- [ ] **步骤 1：编写失败测试（Prompt record 缺字段时报错含 line_number）**

`tests/test_dataset_validation.py`：

```python
import pytest

from app.datasets.validator import validate_jsonl_lines


def test_validate_prompt_missing_user_input_reports_line_number():
    lines = [
        '{"type":"prompt","input":{"system_prompt":"x"}}',
    ]
    with pytest.raises(ValueError) as exc:
        validate_jsonl_lines(lines=lines, eval_type="prompt")
    assert "line=1" in str(exc.value)
```

- [ ] **步骤 2：运行测试验证失败**

```bash
pytest -q
```

预期：FAIL，提示找不到 `app.datasets.validator`。

- [ ] **步骤 3：实现 record 模型与 JSONL 校验（最小让测试通过）**

`app/datasets/records.py`：

```python
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


EvalType = Literal["prompt", "rag", "workflow", "agent"]


class BaseRecord(BaseModel):
    record_id: str | None = None
    type: EvalType
    input: dict[str, Any]
    expected: dict[str, Any] | None = None
    tags: dict[str, Any] | None = None


class PromptInput(BaseModel):
    user_input: str
    system_prompt: str | None = None
    variables: dict[str, Any] | None = None
    constraints: dict[str, Any] | None = None


class PromptRecord(BaseModel):
    record_id: str | None = None
    type: Literal["prompt"] = Field(default="prompt")
    input: PromptInput
    expected: dict[str, Any] | None = None
    tags: dict[str, Any] | None = None


class RagInput(BaseModel):
    question: str
    retrieval_config: dict[str, Any] | None = None


class RagRecord(BaseModel):
    record_id: str | None = None
    type: Literal["rag"] = Field(default="rag")
    input: RagInput
    expected: dict[str, Any] | None = None
    tags: dict[str, Any] | None = None


class WorkflowInput(BaseModel):
    goal: str
    inputs: dict[str, Any] | None = None
    workflow_ref: dict[str, Any] | None = None


class WorkflowRecord(BaseModel):
    record_id: str | None = None
    type: Literal["workflow"] = Field(default="workflow")
    input: WorkflowInput
    expected: dict[str, Any] | None = None
    tags: dict[str, Any] | None = None


class AgentInput(BaseModel):
    task: str
    tools_allowed: list[str] | None = None
    environment: dict[str, Any] | None = None
    termination_criteria: dict[str, Any] | None = None


class AgentRecord(BaseModel):
    record_id: str | None = None
    type: Literal["agent"] = Field(default="agent")
    input: AgentInput
    expected: dict[str, Any] | None = None
    tags: dict[str, Any] | None = None
```

`app/datasets/validator.py`：

```python
from __future__ import annotations

import json
from typing import Any, Iterable

from pydantic import ValidationError

from app.datasets.records import AgentRecord, EvalType, PromptRecord, RagRecord, WorkflowRecord


def _parse_json(line: str, *, line_number: int) -> dict[str, Any]:
    try:
        value = json.loads(line)
    except json.JSONDecodeError as e:
        raise ValueError(f"invalid json line={line_number}: {e.msg}") from e
    if not isinstance(value, dict):
        raise ValueError(f"invalid json object line={line_number}: expected object")
    return value


def validate_jsonl_lines(*, lines: Iterable[str], eval_type: EvalType) -> list[dict[str, Any]]:
    parsed: list[dict[str, Any]] = []
    for idx, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        obj = _parse_json(line, line_number=idx)
        try:
            if eval_type == "prompt":
                rec = PromptRecord.model_validate(obj)
            elif eval_type == "rag":
                rec = RagRecord.model_validate(obj)
            elif eval_type == "workflow":
                rec = WorkflowRecord.model_validate(obj)
            elif eval_type == "agent":
                rec = AgentRecord.model_validate(obj)
            else:
                raise ValueError(f"unsupported eval_type={eval_type}")
        except ValidationError as e:
            raise ValueError(f"schema error line={idx}: {e.errors()}") from e
        parsed.append(rec.model_dump(mode="json"))
    if not parsed:
        raise ValueError("empty dataset")
    return parsed
```

- [ ] **步骤 4：运行测试验证通过**

```bash
pytest -q
```

预期：PASS。

- [ ] **步骤 5：补充更多 schema 测试（同任务内）**

在 `tests/test_dataset_validation.py` 追加：

```python
def test_validate_rag_ok():
    lines = ['{"type":"rag","input":{"question":"q"}}']
    records = validate_jsonl_lines(lines=lines, eval_type="rag")
    assert records[0]["type"] == "rag"


def test_validate_empty_dataset_rejected():
    with pytest.raises(ValueError):
        validate_jsonl_lines(lines=[], eval_type="prompt")
```

运行：

```bash
pytest -q
```

预期：PASS。

- [ ] **步骤 6：Commit**

```bash
git add app/datasets/records.py app/datasets/validator.py tests/test_dataset_validation.py
git commit -m "feat: add strict dataset schema validation for four eval types"
```

---

## 4. 任务 4：SQLite 数据模型与持久化（Dataset/Run/RunItem/Artifact）

**目标：** 让 dataset/run/item 的状态可追溯，可分页查询与导出。

**文件：**

- 创建：`app/db/session.py`
- 创建：`app/db/models.py`
- 创建：`app/db/migrate.py`（简单 create_all）
- 测试：`tests/test_db_models.py`

- [ ] **步骤 1：编写失败测试（能创建 tables 并插入 dataset）**

`tests/test_db_models.py`：

```python
from app.db.migrate import create_all
from app.db.session import create_engine_and_sessionmaker
from app.db.models import Dataset


def test_can_create_tables_and_insert_dataset(tmp_path):
    db_path = tmp_path / "test.db"
    engine, SessionLocal = create_engine_and_sessionmaker(sqlite_path=str(db_path))
    create_all(engine)

    with SessionLocal() as session:
        ds = Dataset(id="ds1", name="n", eval_type="prompt", schema_version="v1", records_count=1, raw_path=None)
        session.add(ds)
        session.commit()

    with SessionLocal() as session:
        loaded = session.get(Dataset, "ds1")
        assert loaded is not None
        assert loaded.eval_type == "prompt"
```

- [ ] **步骤 2：运行测试验证失败**

```bash
pytest -q
```

预期：FAIL，缺少 `app.db.*`。

- [ ] **步骤 3：实现 DB session 与 models（最小让测试通过）**

`app/db/session.py`：

```python
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def create_engine_and_sessionmaker(*, sqlite_path: str):
    engine = create_engine(
        f"sqlite+pysqlite:///{sqlite_path}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    return engine, SessionLocal
```

`app/db/models.py`：

```python
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    eval_type: Mapped[str] = mapped_column(String, nullable=False)
    schema_version: Mapped[str] = mapped_column(String, nullable=False)
    records_count: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_path: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    dataset_id: Mapped[str] = mapped_column(String, nullable=False)
    eval_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    config_snapshot_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    progress_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    progress_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    progress_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class RunItem(Base):
    __tablename__ = "run_items"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(String, nullable=False)
    record_id: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    error_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    output_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    trace_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    metrics_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(String, nullable=False)
    record_id: Mapped[str] = mapped_column(String, nullable=False)
    path: Mapped[str] = mapped_column(String, nullable=False)
    redaction_policy: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
```

`app/db/migrate.py`：

```python
from __future__ import annotations

from sqlalchemy.engine import Engine

from app.db.models import Base


def create_all(engine: Engine) -> None:
    Base.metadata.create_all(bind=engine)
```

- [ ] **步骤 4：运行测试验证通过**

```bash
pytest -q
```

预期：PASS。

- [ ] **步骤 5：Commit**

```bash
git add app/db/session.py app/db/models.py app/db/migrate.py tests/test_db_models.py
git commit -m "feat: add sqlite persistence models"
```

---

## 5. 任务 5：FastAPI 应用骨架与健康检查

**目标：** 提供可运行的服务入口，后续逐步挂载 API。

**文件：**

- 创建：`app/main.py`
- 创建：`tests/test_healthz.py`

- [ ] **步骤 1：编写失败测试（/healthz 返回 ok）**

`tests/test_healthz.py`：

```python
from fastapi.testclient import TestClient

from app.main import app


def test_healthz_ok():
    client = TestClient(app)
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

- [ ] **步骤 2：运行测试验证失败**

```bash
pytest -q
```

预期：FAIL，缺少 `app.main`。

- [ ] **步骤 3：实现最小 FastAPI app**

`app/main.py`：

```python
from fastapi import FastAPI


app = FastAPI(title="LLM Eval Backend", version="0.1.0")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
```

- [ ] **步骤 4：运行测试验证通过**

```bash
pytest -q
```

预期：PASS。

- [ ] **步骤 5：Commit**

```bash
git add app/main.py tests/test_healthz.py
git commit -m "feat: add fastapi app entry and healthz"
```

---

## 6. 任务 6：Dataset 上传 API（保存原始文件 + 严格校验 + 落库）

**目标：** 实现 `POST /datasets` 与 `GET /datasets/{dataset_id}`。

**文件：**

- 创建：`app/core/config.py`
- 创建：`app/schemas/datasets.py`
- 创建：`app/api/datasets.py`
- 修改：`app/main.py`
- 测试：`tests/test_datasets_api.py`

- [ ] **步骤 1：编写失败测试（上传 prompt 数据集成功返回 dataset_id 与 records_count）**

`tests/test_datasets_api.py`：

```python
from fastapi.testclient import TestClient

from app.main import app


def test_upload_dataset_prompt_ok(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_SQLITE_PATH", str(tmp_path / "app.db"))
    monkeypatch.setenv("APP_DATASET_DIR", str(tmp_path / "datasets"))

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
```

- [ ] **步骤 2：运行测试验证失败**

```bash
pytest -q
```

预期：FAIL，`/datasets` 404。

- [ ] **步骤 3：实现 config + DB 初始化依赖**

`app/core/config.py`：

```python
from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    sqlite_path: str = "app.db"
    dataset_dir: str = "data/datasets"
    artifact_dir: str = "artifacts"
    save_raw_datasets: bool = True
    save_artifacts: bool = True
    default_max_concurrency: int = 4
    default_timeout_seconds: int = 120

    class Config:
        env_prefix = "APP_"


settings = Settings()
```

在 `app/main.py` 中新增启动时创建表（先用简单方式）：

```python
from app.core.config import settings
from app.db.migrate import create_all
from app.db.session import create_engine_and_sessionmaker

engine, SessionLocal = create_engine_and_sessionmaker(sqlite_path=settings.sqlite_path)
create_all(engine)
```

并提供一个依赖函数让 API 获取 SessionLocal（后续可重构为更标准的依赖注入）。

- [ ] **步骤 4：实现 datasets API 与 schema**

`app/schemas/datasets.py`：

```python
from pydantic import BaseModel


class DatasetCreateResponse(BaseModel):
    dataset_id: str
    records_count: int
    eval_type: str
    schema_version: str
```

`app/api/datasets.py`（核心逻辑：接收上传文件→逐行校验→保存→落库）：

```python
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile

from app.core.config import settings
from app.datasets.validator import validate_jsonl_lines
from app.db.models import Dataset
from app.main import SessionLocal
from app.schemas.datasets import DatasetCreateResponse


router = APIRouter()


@router.post("/datasets", response_model=DatasetCreateResponse)
def create_dataset(
    file: UploadFile = File(...),
    name: str | None = Form(default=None),
    eval_type: str = Form(...),
):
    dataset_id = str(uuid.uuid4())
    dataset_dir = Path(settings.dataset_dir)
    dataset_dir.mkdir(parents=True, exist_ok=True)

    raw_path = None
    content = file.file.read().decode("utf-8")
    lines = content.splitlines()
    records = validate_jsonl_lines(lines=lines, eval_type=eval_type)  # raises ValueError

    if settings.save_raw_datasets:
        raw_path = str(dataset_dir / f"{dataset_id}.jsonl")
        Path(raw_path).write_text(content, encoding="utf-8")

    with SessionLocal() as session:
        ds = Dataset(
            id=dataset_id,
            name=name,
            eval_type=eval_type,
            schema_version="v1",
            records_count=len(records),
            raw_path=raw_path,
        )
        session.add(ds)
        session.commit()

    return DatasetCreateResponse(dataset_id=dataset_id, records_count=len(records), eval_type=eval_type, schema_version="v1")
```

在 `app/main.py` 注册路由：

```python
from app.api.datasets import router as datasets_router

app.include_router(datasets_router)
```

- [ ] **步骤 5：运行测试验证通过**

```bash
pytest -q
```

预期：PASS。

- [ ] **步骤 6：补充失败用例测试（schema 错误返回 422 且包含 line）**

在 `tests/test_datasets_api.py` 追加：

```python
def test_upload_dataset_schema_error_returns_4xx(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_SQLITE_PATH", str(tmp_path / "app.db"))
    monkeypatch.setenv("APP_DATASET_DIR", str(tmp_path / "datasets"))
    client = TestClient(app)
    content = b'{"type":"prompt","input":{"system_prompt":"x"}}\n'
    resp = client.post(
        "/datasets",
        files={"file": ("ds.jsonl", content, "application/jsonl")},
        data={"eval_type": "prompt"},
    )
    assert resp.status_code in (400, 422)
```

随后把 `create_dataset` 中的 `ValueError` 映射成 FastAPI 的 `HTTPException(status_code=422, detail=...)`，确保返回结构稳定。

- [ ] **步骤 7：Commit**

```bash
git add app/core/config.py app/schemas/datasets.py app/api/datasets.py app/main.py tests/test_datasets_api.py
git commit -m "feat: add dataset upload and validation api"
```

---

## 7. 任务 7：SUT HTTP 适配器（通用接入：平台调用你的被测系统）

**目标：** 提供一个不绑定业务代码的 SUTAdapter：平台通过 HTTP 调用外部 SUT，拿到标准化 trace。

**文件：**

- 创建：`app/sut/http_adapter.py`
- 测试：`tests/test_sut_http_adapter.py`

- [ ] **步骤 1：编写失败测试（adapter 发送 record 并返回 trace）**

`tests/test_sut_http_adapter.py`：

```python
import httpx
import pytest

from app.sut.http_adapter import HttpSUTAdapter


class MockTransport(httpx.BaseTransport):
    def handle_request(self, request):
        content = b'{"output":{"final":"ok"},"trace":{"messages":[]}}'
        return httpx.Response(200, content=content, request=request)


@pytest.mark.anyio
async def test_http_sut_adapter_returns_trace():
    adapter = HttpSUTAdapter(base_url="http://sut", timeout_seconds=5)
    adapter._client = httpx.Client(transport=MockTransport(), base_url="http://sut")
    trace = await adapter.execute(record={"type": "prompt", "input": {"user_input": "hi"}}, provider=None)
    assert trace["output"]["final"] == "ok"
```

- [ ] **步骤 2：运行测试验证失败**

```bash
pytest -q
```

预期：FAIL，缺少 `app.sut.http_adapter`。

- [ ] **步骤 3：实现 HttpSUTAdapter**

`app/sut/http_adapter.py`：

```python
from __future__ import annotations

import httpx


class HttpSUTAdapter:
    name = "http"

    def __init__(self, *, base_url: str, timeout_seconds: int) -> None:
        self._client = httpx.Client(base_url=base_url, timeout=timeout_seconds)

    async def execute(self, *, record: dict, provider) -> dict:
        resp = self._client.post("/execute", json={"record": record})
        resp.raise_for_status()
        return resp.json()
```

- [ ] **步骤 4：运行测试验证通过**

```bash
pytest -q
```

预期：PASS。

- [ ] **步骤 5：Commit**

```bash
git add app/sut/http_adapter.py tests/test_sut_http_adapter.py
git commit -m "feat: add http sut adapter"
```

---

## 8. 任务 8：执行引擎（进程内异步 Run 执行、并发、超时、取消）

**目标：** 以统一流程执行每条 record：调用 SUT → 产出 trace → 计算 metrics → 保存 item。

**文件：**

- 创建：`app/execution/engine.py`
- 创建：`app/metrics/basic.py`
- 测试：`tests/test_execution_engine.py`

- [ ] **步骤 1：编写失败测试（engine 能并发执行并写入 results）**

`tests/test_execution_engine.py`：

```python
import pytest

from app.execution.engine import RunEngine
from app.plugins.interfaces import MetricRequirement, MetricResult


class DummyAdapter:
    name = "dummy"

    async def execute(self, *, record, provider):
        return {"output": {"final": record["input"]["x"]}, "trace": {"messages": []}}


class DummyMetric:
    name = "dummy_metric"
    version = "1"
    requirements = MetricRequirement()

    async def evaluate(self, *, record, trace, provider):
        return MetricResult(name=self.name, status="ok", score=1.0, details={}, version=self.version)


@pytest.mark.anyio
async def test_engine_runs_all_items():
    engine = RunEngine(max_concurrency=2, timeout_seconds=5)
    records = [{"record_id": "r1", "type": "prompt", "input": {"x": "a"}}, {"record_id": "r2", "type": "prompt", "input": {"x": "b"}}]
    results = await engine.run(records=records, adapter=DummyAdapter(), metrics=[DummyMetric()], provider=None)
    assert results["summary"]["total"] == 2
    assert results["items"][0]["metrics"][0]["name"] == "dummy_metric"
```

- [ ] **步骤 2：运行测试验证失败**

```bash
pytest -q
```

预期：FAIL，缺少 `RunEngine`。

- [ ] **步骤 3：实现最小 RunEngine（并发 + 超时）**

`app/execution/engine.py`：

```python
from __future__ import annotations

import asyncio
import time
from typing import Any


class RunEngine:
    def __init__(self, *, max_concurrency: int, timeout_seconds: int) -> None:
        self._max_concurrency = max_concurrency
        self._timeout_seconds = timeout_seconds
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    async def _run_one(self, *, record: dict[str, Any], adapter: Any, metrics: list[Any], provider: Any) -> dict[str, Any]:
        start = time.time()
        try:
            trace_obj = await asyncio.wait_for(adapter.execute(record=record, provider=provider), timeout=self._timeout_seconds)
            metric_results = []
            for metric in metrics:
                metric_results.append((await metric.evaluate(record=record, trace=trace_obj.get("trace", {}), provider=provider)).__dict__)
            return {
                "record_id": record.get("record_id"),
                "status": "succeeded",
                "output": trace_obj.get("output"),
                "trace": trace_obj.get("trace"),
                "metrics": metric_results,
                "duration_ms": int((time.time() - start) * 1000),
            }
        except Exception as e:
            return {
                "record_id": record.get("record_id"),
                "status": "failed",
                "error": {"message": str(e), "type": e.__class__.__name__},
                "metrics": [],
                "duration_ms": int((time.time() - start) * 1000),
            }

    async def run(self, *, records: list[dict[str, Any]], adapter: Any, metrics: list[Any], provider: Any) -> dict[str, Any]:
        sem = asyncio.Semaphore(self._max_concurrency)
        items: list[dict[str, Any]] = []

        async def worker(rec: dict[str, Any]) -> None:
            if self._cancelled:
                return
            async with sem:
                items.append(await self._run_one(record=rec, adapter=adapter, metrics=metrics, provider=provider))

        await asyncio.gather(*(worker(r) for r in records))
        failed = sum(1 for it in items if it["status"] == "failed")
        return {"summary": {"total": len(records), "failed": failed}, "items": items}
```

- [ ] **步骤 4：运行测试验证通过**

```bash
pytest -q
```

预期：PASS。

- [ ] **步骤 5：Commit**

```bash
git add app/execution/engine.py tests/test_execution_engine.py
git commit -m "feat: add in-process async run engine"
```

---

## 9. 任务 9：Metric 体系（requirements + skipped 规则）与基础指标

**目标：** 把 SPEC 中“缺字段必须 skipped、禁止猜测补全”落实到代码。

**文件：**

- 创建：`app/metrics/basic.py`
- 测试：`tests/test_metric_requirements.py`

- [ ] **步骤 1：编写失败测试（缺 rag contexts 时指标 skipped）**

`tests/test_metric_requirements.py`：

```python
import pytest

from app.metrics.basic import RagContextsPresentMetric


@pytest.mark.anyio
async def test_rag_contexts_present_metric_skipped_when_missing():
    metric = RagContextsPresentMetric()
    record = {"type": "rag", "input": {"question": "q"}}
    trace = {"retrieval": {}}
    res = await metric.evaluate(record=record, trace=trace, provider=None)
    assert res.status == "skipped"
```

- [ ] **步骤 2：运行测试验证失败**

```bash
pytest -q
```

预期：FAIL，缺少 `app.metrics.basic`。

- [ ] **步骤 3：实现基础指标**

`app/metrics/basic.py`：

```python
from __future__ import annotations

from app.plugins.interfaces import MetricRequirement, MetricResult


class RagContextsPresentMetric:
    name = "rag_contexts_present"
    version = "1"
    requirements = MetricRequirement(needs_rag_contexts=False)

    async def evaluate(self, *, record: dict, trace: dict, provider) -> MetricResult:
        contexts = (trace.get("retrieval") or {}).get("contexts")
        if contexts is None:
            return MetricResult(
                name=self.name,
                status="skipped",
                score=None,
                details={"reason": "missing trace.retrieval.contexts"},
                version=self.version,
            )
        return MetricResult(
            name=self.name,
            status="ok",
            score=1.0 if len(contexts) > 0 else 0.0,
            details={"contexts_count": len(contexts)},
            version=self.version,
        )
```

- [ ] **步骤 4：运行测试验证通过**

```bash
pytest -q
```

预期：PASS。

- [ ] **步骤 5：Commit**

```bash
git add app/metrics/basic.py tests/test_metric_requirements.py
git commit -m "feat: add basic metrics with strict skipped behavior"
```

---

## 10. 任务 10：Ragas 指标封装（最小可用：faithfulness / answer_relevancy）

**目标：** 在不绑定供应商 SDK 的前提下，通过 ModelProvider 接口驱动 Ragas 指标；不满足 requirements 时严格 skipped。

**文件：**

- 创建：`app/metrics/ragas_metrics.py`
- 测试：`tests/test_ragas_metrics_skipped.py`

- [ ] **步骤 1：编写失败测试（provider 缺 embed 时 skipped）**

`tests/test_ragas_metrics_skipped.py`：

```python
import pytest

from app.metrics.ragas_metrics import RagasFaithfulnessMetric


class ChatOnlyProvider:
    name = "chat_only"

    async def chat(self, *, messages, **kwargs):
        return {"text": "ok"}


@pytest.mark.anyio
async def test_ragas_metric_skipped_without_embed():
    metric = RagasFaithfulnessMetric()
    record = {"type": "rag", "input": {"question": "q"}}
    trace = {"retrieval": {"contexts": ["c1"]}, "output": {"answer": "a"}}
    res = await metric.evaluate(record=record, trace=trace, provider=ChatOnlyProvider())
    assert res.status == "skipped"
```

- [ ] **步骤 2：运行测试验证失败**

```bash
pytest -q
```

预期：FAIL，缺少 `app.metrics.ragas_metrics`。

- [ ] **步骤 3：实现 Ragas 指标封装（先保证 skipped 逻辑）**

`app/metrics/ragas_metrics.py`（先实现 requirements 检查与 skipped，后续再把 ragas evaluate 接上）：

```python
from __future__ import annotations

from app.plugins.interfaces import MetricRequirement, MetricResult


def _has_method(obj, name: str) -> bool:
    return callable(getattr(obj, name, None))


class RagasFaithfulnessMetric:
    name = "ragas_faithfulness"
    version = "1"
    requirements = MetricRequirement(needs_provider_chat=True, needs_provider_embed=True, needs_rag_contexts=True)

    async def evaluate(self, *, record: dict, trace: dict, provider) -> MetricResult:
        contexts = ((trace.get("retrieval") or {}).get("contexts")) or None
        if not contexts:
            return MetricResult(self.name, "skipped", None, {"reason": "missing contexts"}, self.version)
        if provider is None:
            return MetricResult(self.name, "skipped", None, {"reason": "missing provider"}, self.version)
        if not _has_method(provider, "chat") or not _has_method(provider, "embed"):
            return MetricResult(self.name, "skipped", None, {"reason": "provider missing chat/embed"}, self.version)
        return MetricResult(self.name, "skipped", None, {"reason": "ragas integration not wired yet"}, self.version)
```

- [ ] **步骤 4：运行测试验证通过**

```bash
pytest -q
```

预期：PASS。

- [ ] **步骤 5：在同任务内补齐 answer_relevancy 的同类封装与 tests**

新增 `RagasAnswerRelevancyMetric` 与对应 skipped test（缺 contexts 或缺 provider 时 skipped）。

- [ ] **步骤 6：Commit**

```bash
git add app/metrics/ragas_metrics.py tests/test_ragas_metrics_skipped.py
git commit -m "feat: add ragas metric wrappers with strict requirements checks"
```

---

## 11. 任务 11：Run API（创建/启动/查询/items/取消）

**目标：** 完成核心平台能力闭环：通过 API 触发后台执行并持久化结果。

**文件：**

- 创建：`app/schemas/runs.py`
- 创建：`app/api/runs.py`
- 修改：`app/main.py`
- 测试：`tests/test_runs_api.py`

- [ ] **步骤 1：编写失败测试（创建 run 并启动，最终可查询到 items）**

`tests/test_runs_api.py`（以 dummy adapter/metric 作为内置注册项，确保可 determinism）：

```python
import time

from fastapi.testclient import TestClient

from app.main import app


def test_create_and_run(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_SQLITE_PATH", str(tmp_path / "app.db"))
    monkeypatch.setenv("APP_DATASET_DIR", str(tmp_path / "datasets"))
    monkeypatch.setenv("APP_ARTIFACT_DIR", str(tmp_path / "artifacts"))

    client = TestClient(app)
    ds_content = b'{"type":"prompt","input":{"user_input":"hi"}}\n'
    ds_resp = client.post("/datasets", files={"file": ("ds.jsonl", ds_content, "application/jsonl")}, data={"eval_type": "prompt"})
    dataset_id = ds_resp.json()["dataset_id"]

    run_resp = client.post(
        "/runs",
        json={
            "dataset_id": dataset_id,
            "eval_type": "prompt",
            "sut": {"adapter_name": "http", "adapter_config": {"base_url": "http://sut", "timeout_seconds": 5}},
            "metrics": [{"metric_name": "rag_contexts_present", "metric_config": {}}],
            "provider_ref": {"provider_name": "manual", "config": {}},
            "execution": {"max_concurrency": 1, "timeout_seconds": 5, "save_artifacts": False},
        },
    )
    assert run_resp.status_code == 200, run_resp.text
    run_id = run_resp.json()["run_id"]

    start_resp = client.post(f"/runs/{run_id}/start")
    assert start_resp.status_code == 200

    for _ in range(30):
        status = client.get(f"/runs/{run_id}").json()["status"]
        if status in ("succeeded", "failed"):
            break
        time.sleep(0.05)

    items = client.get(f"/runs/{run_id}/items").json()["items"]
    assert len(items) == 1
```

- [ ] **步骤 2：实现 run schemas**

`app/schemas/runs.py`：

```python
from __future__ import annotations

from pydantic import BaseModel


class SutConfig(BaseModel):
    adapter_name: str
    adapter_config: dict


class MetricConfig(BaseModel):
    metric_name: str
    metric_config: dict


class ProviderRef(BaseModel):
    provider_name: str
    config: dict


class ExecutionConfig(BaseModel):
    max_concurrency: int | None = None
    timeout_seconds: int | None = None
    save_artifacts: bool | None = None


class RunCreateRequest(BaseModel):
    dataset_id: str
    eval_type: str
    sut: SutConfig
    metrics: list[MetricConfig]
    provider_ref: ProviderRef
    execution: ExecutionConfig | None = None


class RunCreateResponse(BaseModel):
    run_id: str
    status: str


class RunGetResponse(BaseModel):
    run_id: str
    status: str
    progress: dict
    aggregate: dict | None = None


class RunItemsResponse(BaseModel):
    items: list[dict]
```

- [ ] **步骤 3：实现 runs API（最小能跑通测试）**

`app/api/runs.py` 要点：

- `POST /runs`：落库 Run(status=created, snapshot=请求体)；预创建 run_items（根据 dataset 记录数与 record_id）
- `POST /runs/{id}/start`：启动后台任务（asyncio.create_task），状态→running
- 执行时：读取 dataset JSONL → 解析 records → 逐条 run_engine.run_one（或 batch）→ 写 run_items
- `GET /runs/{id}`、`GET /runs/{id}/items`、`POST /runs/{id}/cancel`

- [ ] **步骤 4：运行测试验证失败→逐步实现直到 PASS**

运行：

```bash
pytest -q
```

预期：先失败（404 或未实现）；迭代实现直至 PASS。

- [ ] **步骤 5：Commit**

```bash
git add app/schemas/runs.py app/api/runs.py app/main.py tests/test_runs_api.py
git commit -m "feat: add run lifecycle api with in-process async execution"
```

---

## 12. 任务 12：结果导出 API（jsonl/csv/json）

**目标：** 满足 SPEC 的导出要求，字段稳定、脚本可解析。

**文件：**

- 创建：`app/api/export.py`
- 修改：`app/main.py`
- 测试：`tests/test_export_api.py`

- [ ] **步骤 1：编写失败测试（导出 jsonl 至少包含 record_id 与 metrics）**

`tests/test_export_api.py`：

```python
from fastapi.testclient import TestClient

from app.main import app


def test_export_jsonl_returns_lines(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_SQLITE_PATH", str(tmp_path / "app.db"))
    client = TestClient(app)

    resp = client.get("/runs/does-not-exist/export?format=jsonl")
    assert resp.status_code == 404
```

- [ ] **步骤 2：实现导出路由（先 404 正确，再补实际导出）**

实现 `GET /runs/{run_id}/export?format=...`：

- run 不存在：404
- jsonl：逐条 `run_items` 输出
- csv：扁平化（`metric.<name>` 列）
- json：包含 summary + items

- [ ] **步骤 3：补充成功导出测试（基于任务 11 的 run 流程复用）**

在测试中先创建 dataset/run 并跑完，然后请求 export，断言内容格式正确。

- [ ] **步骤 4：Commit**

```bash
git add app/api/export.py app/main.py tests/test_export_api.py
git commit -m "feat: add run export api (jsonl/csv/json)"
```

---

## 13. 任务 13：安全与脱敏（不回显 provider_ref 敏感信息、artifacts 可关闭）

**目标：** 落实 SPEC 安全要求。

**文件：**

- 修改：`app/api/runs.py`
- 修改：`app/api/datasets.py`
- 创建：`app/core/redaction.py`
- 测试：`tests/test_redaction.py`

- [ ] **步骤 1：编写失败测试（provider_ref 不在 RunGetResponse 中原样回显）**

`tests/test_redaction.py`：

```python
from app.core.redaction import redact_dict


def test_redact_hides_api_key_like_fields():
    data = {"api_key": "secret", "nested": {"token": "t"}}
    redacted = redact_dict(data)
    assert redacted["api_key"] != "secret"
    assert redacted["nested"]["token"] != "t"
```

- [ ] **步骤 2：实现 redact_dict**

`app/core/redaction.py`：

```python
from __future__ import annotations

from typing import Any


SENSITIVE_KEYS = {"api_key", "apikey", "token", "access_token", "secret"}


def redact_dict(value: Any) -> Any:
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if str(k).lower() in SENSITIVE_KEYS:
                out[k] = "***"
            else:
                out[k] = redact_dict(v)
        return out
    if isinstance(value, list):
        return [redact_dict(x) for x in value]
    return value
```

- [ ] **步骤 3：在 API 返回中应用脱敏与开关**

- `GET /runs/{id}` 返回 snapshot 摘要时，对 provider_ref/config 做 `redact_dict`
- artifacts 保存受 `save_artifacts` 与全局开关控制

- [ ] **步骤 4：运行测试验证通过**

```bash
pytest -q
```

- [ ] **步骤 5：Commit**

```bash
git add app/core/redaction.py app/api/runs.py tests/test_redaction.py
git commit -m "feat: add redaction and artifact saving controls"
```

---

## 14. 任务 14：Dockerfile 与 CI（GitHub Actions）

**目标：** 满足课程容器化与 CI 要求：push 自动跑测试 + 构建镜像。

**文件：**

- 创建：`Dockerfile`
- 创建：`.github/workflows/ci.yml`

- [ ] **步骤 1：编写 Dockerfile**

`Dockerfile`：

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **步骤 2：编写 GitHub Actions**

`.github/workflows/ci.yml`：

```yaml
name: ci

on:
  push:
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: pytest -q

  docker:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - run: docker build -t llm-eval-backend:ci .
```

- [ ] **步骤 3：本地验证 Docker 构建**

```bash
docker build -t llm-eval-backend:local .
docker run --rm -p 8000:8000 llm-eval-backend:local
```

预期：访问 `GET /healthz` 返回 `{"status":"ok"}`。

- [ ] **步骤 4：Commit**

```bash
git add Dockerfile .github/workflows/ci.yml
git commit -m "chore: add dockerfile and ci workflow"
```

---

## 15. 任务 15：最终验证（本地命令与最小端到端演示）

**目标：** 在宣称完成前给出可重复的验证证据。

**步骤：**

- [ ] **步骤 1：静态检查**

```bash
ruff check .
```

- [ ] **步骤 2：单元测试**

```bash
pytest -q
```

- [ ] **步骤 3：端到端 smoke（API）**

启动：

```bash
uvicorn app.main:app --reload
```

上传数据集（示例）：

```bash
curl -X POST http://127.0.0.1:8000/datasets \
  -F "eval_type=prompt" \
  -F "file=@./examples/prompt.jsonl"
```

创建 run：

```bash
curl -X POST http://127.0.0.1:8000/runs \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id":"<DATASET_ID>",
    "eval_type":"prompt",
    "sut":{"adapter_name":"http","adapter_config":{"base_url":"http://127.0.0.1:9000","timeout_seconds":10}},
    "metrics":[{"metric_name":"rag_contexts_present","metric_config":{}}],
    "provider_ref":{"provider_name":"manual","config":{}},
    "execution":{"max_concurrency":2,"timeout_seconds":10,"save_artifacts":false}
  }'
```

启动 run：

```bash
curl -X POST http://127.0.0.1:8000/runs/<RUN_ID>/start
```

导出：

```bash
curl "http://127.0.0.1:8000/runs/<RUN_ID>/export?format=jsonl"
```

- [ ] **步骤 4：Commit（如有最后的修正）**

```bash
git add -A
git commit -m "chore: finalize backend mvp"
```

---

## 执行交接（实现方式选择）

计划已完成并保存到 [PLAN.md](file:///e:/Homework/SEEC3/RagasTest/PLAN.md)。

两种执行方式：

1. **子代理驱动（推荐）**：使用 superpowers:subagent-driven-development，每个任务派发一个新子代理 + 两阶段审查
2. **内联执行**：使用 superpowers:executing-plans，在当前会话中按任务批量执行并设置检查点
