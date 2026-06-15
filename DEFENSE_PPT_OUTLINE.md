# 答辩 PPT 大纲（10 页正式答辩版）

本文档用于答辩时快速制作 PPT。当前版本已压缩为更适合正式答辩的 `10` 页主线结构，强调“项目价值 + 可见成果 + 过程证据 + 反思总结”，避免正文过长、信息重复。

建议总页数：10 页主线 + 附录备用  
建议时长：8-10 分钟  
建议主线：问题 -> 方案 -> 成果 -> 证据 -> 反思

---

## 1. 封面

**标题建议：**

- 基于 Superpowers 的规约驱动 LLM 测评平台设计与实现
- AI4SE 期末项目答辩

**建议呈现内容：**

- 项目名称：RagasTest / LLM Eval 平台
- 个人信息：姓名、学号、课程名称
- 一句话简介：面向 Prompt / RAG / Workflow / Agent 四类场景的可复用 LLM 测评平台

**建议口播：**

- 先用 20 秒讲清楚项目是什么、解决什么问题、为什么值得做

---

## 2. 课程要求与我的达成路径

**标题建议：**

- 课程要求与我的完成路径
- 我如何对齐本次作业目标

**建议呈现内容：**

- 用一张对照表展示课程要求与本项目产物的对应关系：
  - `SPEC -> PLAN -> 冷启动验证 -> 实现 -> 测试 -> Docker/CI -> 反思`
  - `SPEC.md / PLAN.md / SPEC_PROCESS.md / AGENT_LOG.md / README.md / REFLECTION.md`
- 强调两个关键词：
  - 不只是“把系统做出来”
  - 而是“把过程证据留完整”

**建议口播：**

- 这一页只讲一件事：我的答辩不是单纯展示功能，而是展示“课程要求如何被工程化落实”

**可引用文档：**

- `AI4SE_Final_Project0518.md`

---

## 3. 项目背景与真实问题

**标题建议：**

- 我想解决什么问题

**建议呈现内容：**

- LLM 应用评测常见痛点：
  - 不同项目输入输出格式不统一
  - 四类场景评测难复用
  - 结果难导出、难追溯、难复现
  - 很多工具依赖特定框架或特定模型 SDK
- 本项目定位：
  - 统一 Dataset + Run + Trace + Metric 规约
  - 支持 dataset-only 评测，不强依赖外部 SUT
  - 兼顾可复用、可追溯、可部署

**建议口播：**

- 强调这不是“做一个 demo 页面”，而是在做一个可复用的评测平台

**可引用文档：**

- `SPEC.md`
- `README.md`
- `USAGE.md`

---

## 4. 总体架构与技术选型

**标题建议：**

- 系统架构设计
- 技术选型与理由

**建议呈现内容：**

- 后端：FastAPI + SQLite + SQLAlchemy + asyncio
- 前端：React + TypeScript + Vite + Nginx
- 测试：pytest、前端 lint/test/build
- 部署：Dockerfile + docker-compose.yml
- 架构核心：
  - Dataset 上传与校验
  - Run 执行引擎
  - PluginRegistry
  - SUTAdapter / ModelProvider / Metric 抽象
  - artifacts 与导出机制
- 顺带点出范围边界：
  - 做了通用评测闭环
  - 没做分布式调度和多租户等重型能力

**建议口播：**

- 解释为什么默认选择 SQLite、进程内异步、插件化抽象，而不是一开始就上重型架构

**建议展示素材：**

- 一张简化组件图：前端 -> API -> DB / artifacts / metrics / provider

**可引用文档：**

- `SPEC.md`
- `PLAN.md`
- `FRONTEND_HANDOFF.md`

---

## 5. 核心功能闭环

**标题建议：**

- 核心业务流程

**建议呈现内容：**

- 用户完整使用路径：
  - 上传 JSONL 数据集
  - 选择 eval_type 和 metrics
  - 创建并启动 Run
  - 查询 progress 与 items
  - 导出 CSV / JSON / JSONL
- 两种运行模式：
  - dataset-only：直接读取 dataset 中的 `output/trace`
  - SUT 模式：通过 HTTP adapter 调用被测系统

**建议口播：**

- 这页适合用流程图讲，体现平台不是单点功能，而是有完整闭环

**可引用文档：**

- `README.md`
- `USAGE.md`
- `FRONTEND_HANDOFF.md`

---

## 6. 系统 Demo / 可见成果

**标题建议：**

- 系统展示
- 我最终做成了什么

**建议呈现内容：**

- 前端可见功能：
  - Datasets：上传、详情、删除、demo 数据集下载
  - Runs：创建、启动、轮询、导出、删除
  - Help：四类评测的指标说明
- 后端可见结果：
  - `/healthz`
  - Run 状态与 items
  - JSON / JSONL / CSV 导出
- 部署结果：
  - Docker Compose 一键启动
  - 校园网可访问
  - 镜像可导出 tar 迁移部署

**建议口播：**

- 这页优先展示“成品长什么样”，让老师先看到结果，再回头讲过程

**建议展示素材：**

- 前端页面截图
- Run 结果截图
- 导出文件截图
- `healthz` 与 compose 启动成功截图

**可引用文档：**

- `README.md`
- `FRONTEND_HANDOFF.md`
- `docker-images-build.md`

---

## 7. 关键规约设计：为什么这个平台能覆盖 4 类评测

**标题建议：**

- 数据规约与指标设计亮点
- 为什么平台具有通用性

**建议呈现内容：**

- 四类场景统一使用 JSONL Record
- 对 `input / expected / output / trace / tags` 做统一约束
- 两个最值得强调的设计点：
  - 严格 schema 校验 + 行号级错误反馈
  - requirements 不满足时明确 `skipped`
- 指标层只讲一个代表性例子即可：
  - 例如 RAG 中 `contexts` 缺失会导致部分指标 `skipped`

**建议口播：**

- 这一页不要讲太多公式，重点讲“为什么规约清晰后，平台才真正可复用、可解释”

**可引用文档：**

- `DATASET_SPEC.md`
- `METRICS_SCENARIOS_SUMMARY.md`
- `SPEC.md`

---

## 8. Superpowers 工作流与实现推进证据

**标题建议：**

- 从需求到实现的工作流
- 我是如何把项目拆成可执行任务的

**建议呈现内容：**

- 真实流程：
  - `brainstorming`
  - `writing-plans`
  - `using-git-worktrees`
  - `subagent-driven-development`
  - `test-driven-development`
  - `verification-before-completion`
- `PLAN.md` 共拆成 15 个任务
- 每个任务有：
  - 明确目标
  - 涉及文件
  - 失败测试
  - 验证步骤
  - 完成后的 commit hash
- 可展示代表性任务：
  - Task 2：插件接口与 registry
  - Task 3：四类数据集 schema 校验
  - Task 11：Run 生命周期 API
  - Task 12：导出 API
- 对应产物：
  - `SPEC.md`
  - `PLAN.md`
  - `SPEC_PROCESS.md`
  - `AGENT_LOG.md`

**建议口播：**

- 这页重点回答“我不是只用了 AI 写代码，而是用了 AI 的工程方法论”
- 强调 task 粒度是为 subagent 和 TDD 服务的，而不是随便列待办清单

**可引用文档：**

- `PLAN.md`
- `SPEC_PROCESS.md`
- `AGENT_LOG.md`

---

## 9. 冷启动验证 + TDD 质量保障

**标题建议：**

- 规约如何经受陌生智能体检验
- 我如何证明“真的完成了”

**建议呈现内容：**

- 冷启动验证：
  - 不提供历史对话
  - 仅提供 `SPEC.md` + `PLAN.md`
  - 试跑任务 2 和任务 3
  - 暴露了 registry 边界、schema 可执行性、错误语义等问题
- TDD 与验证：
  - 后端：先写失败测试，再补实现
  - 前端：`npm run lint`、`npm test`、`npm run build`
  - 交付前：`pytest`、`ruff`、Docker 构建与健康检查
- 结论：
  - 规约经受了外部检验
  - 完成不是“感觉完成”，而是“有验证证据”

**建议口播：**

- 这一页是课程要求里的高价值证据页，建议重点讲

**建议展示素材：**

- 一张“红 -> 绿 -> 验证”的流程图
- 或展示 `SPEC_PROCESS.md` 中冷启动验证 / 某个任务的红绿灯记录

**可引用文档：**

- `SPEC_PROCESS.md`
- `AGENT_LOG.md`
- `PLAN.md`

---

## 10. 工程限制、取舍与反思

**标题建议：**

- 工程限制与补救
- 我对这次 AI4SE 实践的反思

**建议呈现内容：**

- 现实约束下的取舍：
  - 初始计划是仅后端，后续扩展为前后端可演示平台
  - PR/worktree 流程没有完全做到“每个 worktree 一个 PR”
  - 镜像未正式发布到 Docker Hub / GHCR，而采用 tar 导出
- 为什么会这样：
  - 需求扩展
  - 平台 / 网络限制
  - 交付时间约束
- 我最重要的收获：
  - 规约质量决定实现质量
  - TDD 在 AI 协作下更像放大器
  - 人的价值在于定义边界、设定验收、控制一致性

**建议口播：**

- 这一页要体现：我既理解课程理想流程，也理解真实工程中的限制与补救

**可引用文档：**

- `REFLECTION.md`
- `AGENT_LOG.md`
- `SPEC_PROCESS.md`

---

## 11. 结束页 / Q&A

**标题建议：**

- Thanks / Q&A
- 欢迎提问

**建议呈现内容：**

- 一句话总结：
  - 我完成的不只是一个 LLM 测评平台，更是一套可追溯的 AI 协作工程流程实践
- 可在角落保留仓库地址、部署地址、关键文档列表

---

## 附录 A：答辩备用页（按需追加）

如果老师追问，可从以下内容中追加 1-3 页：

- 四类评测数据规约详情
- metrics 计算逻辑与公式
- PLAN 任务拆解截图
- AGENT_LOG 过程证据
- Docker 部署与镜像导出细节

---

## 附录 B：适合现场展示的素材清单

- 前端首页或 Runs 页面截图
- Datasets 上传页面与 demo 数据集下载按钮截图
- `PLAN.md` 任务完成与 commit hash 截图
- `SPEC_PROCESS.md` 冷启动验证部分截图
- `AGENT_LOG.md` 过程证据截图
- Docker Compose 启动后 `healthz` 成功截图
- 一条 Run 的 items、metrics、导出结果截图

---

## 附录 C：答辩时可主动强调的 3 句话

- 我不是先写代码再补文档，而是先用 `SPEC + PLAN` 固定边界，再进入实现。
- 我不是只展示最终功能，而是展示从规约、验证到交付的完整证据链。
- 这个项目最重要的收获不是“AI 写了多少代码”，而是“我如何用流程让 AI 生成的结果可控、可验、可交付”。

---

## 附录 D：10 页正式版顺序总览

- 1 封面
- 2 课程要求与我的达成路径
- 3 项目背景与真实问题
- 4 总体架构与技术选型
- 5 核心功能闭环
- 6 系统 Demo / 可见成果
- 7 关键规约设计：为什么这个平台能覆盖 4 类评测
- 8 Superpowers 工作流与实现推进证据
- 9 冷启动验证 + TDD 质量保障
- 10 工程限制、取舍与反思
- 11 结束页 / Q&A
