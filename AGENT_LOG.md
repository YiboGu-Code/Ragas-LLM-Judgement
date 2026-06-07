# AGENT_LOG：智能体协作过程记录（项目过程证据）

本文件用于记录本仓库在使用 Superpowers 方法论（brainstorming → writing-plans → TDD → 验证 → 迭代交付）过程中的关键节点与证据。内容以“可追溯”为目标：尽量引用具体文件路径与 commit hash，避免只写结论不写证据。

> 说明：历史过程中存在“需求迭代追加前端”等范围变更，本日志按时间线做了归纳；若需要更细粒度，可在此基础上补充更完整的对话节选与每次人工干预的原因。

## 1. 规约与计划阶段

- **触发技能：** `brainstorming` → `writing-plans`
- **产物：**
  - [SPEC.md](file:///e:/Homework/SEEC3/RagasTest/SPEC.md)
  - [PLAN.md](file:///e:/Homework/SEEC3/RagasTest/PLAN.md)
  - [SPEC_PROCESS.md](file:///e:/Homework/SEEC3/RagasTest/SPEC_PROCESS.md)

## 2. 后端实现阶段（TDD + 逐步验收）

以下为后端主线关键里程碑（部分任务在 [PLAN.md](file:///e:/Homework/SEEC3/RagasTest/PLAN.md) 已记录 commit）：

- **插件接口与注册表（registry）**：`857a961`
- **数据集 schema 与校验**：`71d88d5`
- **SQLite ORM 与迁移/初始化**：`39df4a2`
- **FastAPI 入口与 `/healthz`**：`9b7a8f0`
- **Datasets 上传/查询 API**：`b9050a2`
- **SUT HTTP 适配器**：`4e5cfdb`
- **Run 执行引擎（并发/超时/取消）**：`5ae7a9b`
- **基础指标与严格 skipped 规则**：`a8411cf`
- **Ragas 指标封装（requirements + skipped）**：`94b30c7`
- **Runs 生命周期 API（创建/启动/查询/items/取消）**：`c88f014`
- **导出 API（jsonl/csv/json）**：`a36621f`
- **artifacts 保存与脱敏**：`3b291dd`
- **CI + Dockerfile（后端）**：`23084e6`

## 3. 范围变更：追加前端与联调能力

后续需求从“仅后端”扩展为“前后端可用、支持 dataset-only 联调与演示部署”，对应的主要交付物包括：

- **前端工程（React + Vite + TypeScript）**：见 `frontend/` 目录
- **前端功能：**
  - Datasets：上传、详情、删除、demo 数据集下载
  - Runs：创建（metrics 选择含 provider 依赖）、启动、轮询、items 展示、导出（下载文件）、删除
  - Help：四类 eval_type 的指标选择说明
- **部署：**
  - `docker-compose.yml` 一键部署前后端
  - 前端 Nginx 反代 `/api` 到后端

该阶段的聚合提交：

- `df82d82`：`feat: complete dataset-only eval platform`

## 4. 验证与问题处理（节选）

- **验证：** 持续以 `pytest`、前端 `npm test/lint/build`、Docker 构建与启动作为交付前证据。
- **典型问题与处理：**
  - Docker Hub 拉取失败：改用可访问的基础镜像源（见 Dockerfile 变更）
  - PowerShell 命令链：避免使用 `&&`，改为 `;`
  - 删除接口 405：补齐后端 `DELETE` 路由并在前端对接
  - 导出 JSON/JSONL 下载行为：前端改为 Blob 下载并指定文件名后缀

## 5. 远程仓库推送（GitHub / GitLab）

- GitHub：`origin` 指向 `https://github.com/YiboGu-Code/Ragas-LLM-Judgement.git`，已完成强制覆盖推送
- GitLab：`gitlab` 指向 `https://git.nju.edu.cn/2026_software_engineering_three/assessment_project.git`
  - 曾遇到 `main` 受保护分支禁止 force push
  - 放开保护后已 force push 覆盖 `main`
  - 临时分支 `overwrite-main` 已删除

## 6. 待补充（交付前自检项）

- **冷启动验证（第二智能体）**：按 [AI4SE_Final_Project0518.md](file:///e:/Homework/SEEC3/RagasTest/AI4SE_Final_Project0518.md) §4.5 要求执行，并把证据补充到 [SPEC_PROCESS.md](file:///e:/Homework/SEEC3/RagasTest/SPEC_PROCESS.md)
- **反思报告**：完善 [REFLECTION.md](file:///e:/Homework/SEEC3/RagasTest/REFLECTION.md) 为 1500–2500 字的个人反思（需本人撰写）
