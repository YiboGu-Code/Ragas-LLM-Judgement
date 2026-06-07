# RagasTest：LLM Eval 平台（FastAPI + SQLite + React）

本项目是一个面向 Prompt / RAG / Workflow / Agent 四类场景的 LLM 测评平台。核心流程为：上传数据集（JSONL）→ 创建 Run → 启动执行 → 查看逐条 Items → 导出结果（CSV / JSON / JSONL）。

平台重点支持 dataset-only 评测：不依赖外部 SUT（被测系统），直接从数据集中的 `output` / `trace` 读取输出并计算指标；也支持可选的 SUT HTTP 适配模式。

## 在线访问

- 前端站点：`http://172.29.4.237/`
- 后端接口（直连）：`http://172.29.4.237:8000/`
- 后端接口（前端反代）：`http://172.29.4.237/api/`

说明：该地址仅在校园网环境下可访问。

## 功能概览

- 数据集（Datasets）
  - 上传 JSONL（按 eval_type 做严格 schema 校验）
  - 查看详情
  - 删除（若被 Run 引用会拒绝）
  - Demo 数据集一键下载（Prompt / RAG / Workflow / Agent 各 1 份）
- 评测执行（Runs）
  - 创建 / 启动 / 取消
  - 查看状态与进度、加载 items
  - 导出结果（下载文件）：CSV / JSON / JSONL
  - 删除（会清理 artifacts 与数据库记录）
- 指标（Metrics）
  - 基础指标：`rag_contexts_present`
  - Ragas 指标（部分需要 Provider，例如 Ark）

## 目录结构

- `app/`：后端（FastAPI）
- `frontend/`：前端（React + TypeScript + Vite + Nginx）
- `tests/`：后端测试（pytest）
- `dataset/`：示例数据集（JSONL）
- `DATASET_SPEC.md`：四类场景的数据集规约（用于指导生成合规 JSONL）
- `docker-compose.yml`：前后端一键部署

## 快速开始（Docker 一键部署）

在项目根目录执行：

```bash
# 构建镜像（镜像名固定为 ragastest-*:local）
docker compose build

# 启动
docker compose up -d
```

验证：

```bash
curl http://localhost:8000/healthz
curl http://localhost/api/healthz
```

说明：

- `frontend` 默认对外暴露 `80` 端口；后端同时暴露 `8000` 端口（见 [docker-compose.yml](file:///e:/Homework/SEEC3/RagasTest/docker-compose.yml)）。
- 运行目录下可以放置 `.env`，用于注入如 `ARK_API_KEY` 等环境变量（Ragas 指标需要 Provider 时才必需）。示例：

```env
ARK_API_KEY=YOUR_ARK_API_KEY
```

镜像打包导出（用于拷贝到其他机器部署）可参考 [docker-images-build.md](file:///e:/Homework/SEEC3/RagasTest/docker-images-build.md)。

## 本地开发

### 后端

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt -r requirements-dev.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

健康检查：

```bash
curl http://127.0.0.1:8000/healthz
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

前端开发模式通过 Vite 代理将 `/api/*` 转发到后端，避免 CORS。

## Demo 数据集下载

前端页面「Datasets」上传页提供 4 份 demo 数据集下载按钮，对应静态资源位于：

- `frontend/public/demo-datasets/prompt.jsonl`
- `frontend/public/demo-datasets/rag.jsonl`
- `frontend/public/demo-datasets/workflow.jsonl`
- `frontend/public/demo-datasets/agent.jsonl`

也可以直接访问路径下载（同域）：

- `/demo-datasets/prompt.jsonl`
- `/demo-datasets/rag.jsonl`
- `/demo-datasets/workflow.jsonl`
- `/demo-datasets/agent.jsonl`

下载后可直接在「Datasets」页面上传并创建 Run 试跑。

## 数据集规约（给 SUT / 数据生成侧）

详见 [DATASET_SPEC.md](file:///e:/Homework/SEEC3/RagasTest/DATASET_SPEC.md)。

## 参考文档

- 后端使用手册：[USAGE.md](file:///e:/Homework/SEEC3/RagasTest/USAGE.md)
- 前端对接说明：[FRONTEND_HANDOFF.md](file:///e:/Homework/SEEC3/RagasTest/FRONTEND_HANDOFF.md)
