# AI4SE 期末项目：使用 Superpowers 进行规约驱动的智能体开发

> *Spec-Driven, Subagent-Built, Human-Owned.*

---

## 一、项目概述

本期末项目要求学生综合运用本课程所学的 AI4SE 知识，使用 **[Superpowers](https://github.com/obra/superpowers)** —— 一套面向编码智能体的、内置完整软件开发方法论的技能框架 —— 完成一个具有一定规模的真实软件项目。

Superpowers 的核心思路与本课程理念高度契合：智能体不会一上来就写代码，而是先 **brainstorming** 出 spec，再产出**实现计划**，再以 **subagent-driven development** 的方式逐项执行，并强制 **TDD（红–绿–重构）** 与 **两阶段代码评审**。这种结构化、技能自动触发的工作流，让你能够把精力聚焦在 **真正属于人类的判断**：架构、产品、质量。

本项目关注的核心问题是：

- 你能否引导 Superpowers 的 brainstorming 产出一份足够清晰的 spec？
- 你能否驾驭 plan + subagent 工作流，让智能体长时间自主推进而不脱轨？
- 你能否对智能体生成的代码做出有意义的评审与修正？

---

## 二、学习目标

完成本项目后，学生应能够：

1. 使用 Superpowers 的方法论从模糊想法走到可执行的规约与计划
2. 设计端到端的智能体工作流，掌握 task 拆分、subagent 派发、并行 worktree 等技巧
3. 在 AI 协作场景中坚持 TDD 与"先验证再宣称完成"的工程纪律
4. 通过 prompt / context engineering 提升智能体输出质量
5. 阅读、评审并修正智能体生成的代码
6. 完成从需求 → 规约 → 计划 → 实现 → 容器化 → 部署的完整工程闭环
7. 对当前 agentic SE 方法论形成自己的批判性见解

---

## 三、总体要求

### 3.1 主题与规模

- **主题自定**：Web 应用、CLI 工具、数据分析平台、AI 原生应用、IDE 插件、游戏、面向开发者的工具等均可。
- **规模建议**：有效代码量约 3000–8000 行（含测试），至少 3–5 个核心功能模块；不接受纯 demo 或玩具级项目。
- **必须解决一个真实的小问题**：你应该能在 30 秒内向陌生人说清"这东西为什么有人会用"。
- **技术栈不设限制**，但需在规约中说明选型理由。

### 3.2 独立完成

本项目为 **个人项目**，不允许组队。Superpowers 的设计哲学正是要把"一个人 + 智能体"的产能放大到接近一个小团队，本项目正是要让每位学生亲身体验这种放大效应：你既是 PM、架构师，也是 reviewer 与最终责任人。

### 3.3 工具链

**强制要求：**

- **必须使用 Superpowers 框架**：任选一种支持的编码智能体（Claude Code、OpenAI Codex CLI/App、Cursor Agent、OpenCode、GitHub Copilot CLI、Gemini CLI 均可），并按 Superpowers 文档安装插件。
- 必须 **如实遵循 Superpowers 的 7 步工作流**（见下文 §4）。允许在合理理由下偏离，但偏离必须在 `AGENT_LOG.md` 中记录与解释。
- **TDD 是硬性要求**，由 Superpowers 的 `test-driven-development` 技能强制执行：先红、再绿、再重构。不接受"先写实现再补测试"的做法。

**强烈推荐（凡涉及前端 / UI 的项目）：**

- **使用 [Open Design (nexu-io/open-design)](https://github.com/nexu-io/open-design) 进行前端界面开发**。它是 Anthropic Claude Design 的开源、本地优先实现，提供 19 个前端 skill（landing / dashboard / pricing / docs / blog / mobile-app / deck / 各类业务模板）与 71 个品牌级设计系统（Linear / Stripe / Vercel / Notion / Cursor / Apple / Anthropic …），并内置 **反 AI-slop 机制**（首轮 question form、brand-spec 抽取、5 维自评、P0/P1/P2 checklist），能显著提升 agent 产出界面的质量。
- 纯 CLI / 纯后端项目可豁免；混合项目（有任何 web 界面、移动端 UI、营销页、文档站等）必须使用。

**鼓励：**

- 组合使用多种智能体（例如 Claude Code 主导 + Codex 做某个模块）并对其表现进行比较。

---

## 四、工作流程与交付要求

> **本部分覆盖 Superpowers 全流程：`brainstorming` → `writing-plans` → `using-git-worktrees` → `subagent-driven-development` / `executing-plans` → `test-driven-development` → `requesting-code-review` → `finishing-a-development-branch`。在 SPEC 与 PLAN 完成并通过冷启动验证之前，禁止编写任何实现代码。**

### 4.1 规约与计划生成

启动你的智能体，让 Superpowers 的 `brainstorming` 技能介入。它会主动追问"你究竟想做什么"，分块呈现设计供你逐步签字确认。**学生须把此过程视为一种**与智能体共同设计**的训练**：你不是在"领旨"，而是在"质询"——任何含糊处都要逼智能体补足。

签字确认设计后，触发 `writing-plans` 技能，把设计拆解成"每步 2–5 分钟、明确文件路径、明确验证步骤"的 task 列表。

### 4.2 交付物 1：`SPEC.md`（设计文档）

由 brainstorming 流程沉淀的设计文档，必须包含但不限于：

1. **问题陈述**：要解决什么问题？目标用户是谁？为什么值得做？
2. **用户故事**：至少 5 个，遵循 INVEST 原则。
3. **功能规约**：按模块拆分，每项描述输入 / 行为 / 输出 / 边界条件 / 错误处理。
4. **非功能性需求**：性能、安全、可用性、可观测性。
5. **系统架构**：组件图、数据流、外部依赖。
6. **数据模型**：主要实体、字段、关系、约束。
7. **API 设计**（如适用）：端点、参数、返回结构、错误码。
8. **技术选型与理由**：语言、框架、数据库、部署平台。**若项目含前端，须明确所选 [Open Design 设计系统](https://github.com/nexu-io/open-design)（71 选 1 或自定义）与适用的 Open Design skill（如 `saas-landing` / `dashboard` / `mobile-app` 等），并简述选择理由（与目标用户、品牌调性的匹配度）。**
9. **验收标准**：每个功能"完成"的客观判定标准。
10. **风险与未决问题**：你预见到的可能让智能体翻车的地方。

### 4.3 交付物 2：`PLAN.md`（实现计划）

由 `writing-plans` 技能产出的任务列表，要求：

- 每个 task 颗粒度足够细，可由一个 subagent 在一次会话内完成
- 每个 task 包含：目标、涉及文件、预期实现要点、**验证步骤**（包括将要写的失败测试）
- 显式标出 task 之间的依赖与可并行的部分（用于实现时的 worktree 并行）

### 4.4 交付物 3：`SPEC_PROCESS.md`（过程文档）

记录与 Superpowers 协作生成 spec 与 plan 的过程：

- **brainstorming 关键节点**：智能体追问了哪些好问题？哪些问题让你修正了原来的设想？
- **至少 3 轮关键迭代** 的对话节选与你的处理决策
- 哪些建议是 AI 提出而你采纳的？哪些是你推翻或修正的？为什么？
- 反思：Superpowers 的 brainstorming 技能在你的项目里做得好的地方与让你不满的地方

### 4.5 自我验证：用"陌生"智能体冷启动试跑

正式进入实现前，学生须用 **一个与主开发智能体不同** 的 agent，在 **不喂入你与主 agent 的对话历史** 的前提下，仅凭 `SPEC.md` + `PLAN.md` 来尝试实现 1–2 个 task（约 1–2 小时）。

**为什么必须换一个 agent：** 你和主 agent 在 brainstorming 阶段会沉淀大量共享的隐性上下文（"它知道我说的'用户'指的是 B 端管理员"），这种隐性上下文会让你严重高估 spec 的清晰度。一个新鲜的 agent 会在你忘了明文写下的每个假设上绊倒——而这些绊倒，恰恰是 spec 质量最有价值的反馈信号。这正是单人项目里最接近"同侪评审"效果的内部机制。

**操作要求：**

- 第二个智能体的 **类型必须不同**（例：主开发用 Claude Code，则验证用 Codex / Cursor / Gemini CLI / OpenCode / Qwen Code 任选其一）
- 启动一个 **全新的 session**，不导入任何先前会话或 memory
- 仅向它提供 SPEC.md + PLAN.md，**不补充任何口头解释**
- 指定它从 PLAN 中选 1–2 个 task 自主推进；明确告诉它"遇到不确定的地方就停下来问，而不是凭猜测继续"

**记录到 `SPEC_PROCESS.md` 的内容：**

- 第二个 agent 在哪些地方停下来问了问题？这些问题暴露了哪些 spec 缺陷？
- 它做出了哪些与你原意不一致的解读？是 spec 写错了，还是它读错了？
- 它产出的代码 / 测试与你预期的差距多大？为什么？
- 你由此对 SPEC.md / PLAN.md 做了哪些修订？请给出 **修订前后的关键 diff**。

**这是规约工作中最关键的"客观证据"。** 一份"经过冷启动验证、并据此修订过"的 spec，比一份"看起来很完整但从未受过外部检验"的 spec 含金量高得多。

### 4.6 实现工作流

学生须按 Superpowers 既定流程推进，关键节点如下：

1. **使用 git worktrees 隔离工作区**：每个独立功能 / 大模块开一个 worktree，对应一个 PR。
2. **subagent 驱动开发**：每个 task 派发一个新鲜的 subagent，由它完成单一任务。
3. **TDD 强制**：每个功能都按红–绿–重构推进；先写失败测试，跑出红色，再让 subagent 写最少代码使其变绿，再重构。**没有先于测试写出的实现**。
4. **两阶段评审**：每个 task 完成后由 Superpowers 触发"先 spec 合规检查 → 再代码质量检查"。Critical issue 必须修复才能进入下一 task。
5. **完成分支**：所有 task 完成后由 `finishing-a-development-branch` 决定 merge / PR / 保留 / 丢弃。

### 4.7 GitHub 仓库要求

- 公开 GitHub 仓库（私有仓需将助教加为协作者）。
- **完整的 commit 历史与 PR 工作流**：拒绝单次 commit 提交全部代码；每个 worktree 对应一个 PR。
- 在 commit message / PR 描述中标注由哪个 subagent 完成、人工修改了哪些部分。
- **PLAN.md 应被持续更新**：每完成一个 task 就勾掉，并附上对应 commit hash。
- 维护 `AGENT_LOG.md`（详见 §4.9）。

### 4.8 测试要求

- 必须有可一键运行的测试命令（`make test` 或等价命令）。
- CI（GitHub Actions）必须配置：每次 push 自动跑测试 + 构建 Docker 镜像。

### 4.9 `AGENT_LOG.md`

按时间顺序记录关键节点，每条建议包含：

- **时间戳与 task 编号**
- **触发的 Superpowers 技能**（`brainstorming` / `writing-plans` / `subagent-driven-development` / `test-driven-development` / `requesting-code-review` / `systematic-debugging` 等）
- **关键 prompt / context 配置**
- **subagent 输出的关键片段或链接**（如 commit hash）
- **人工干预**：你修改了什么？为什么？
- **学到的教训**：可复用的 prompt 模板、踩坑、应对策略

这份日志是实现工作中最重要的"过程证据"。

### 4.10 容器化（必做）

- 提供 `Dockerfile`，多服务项目须提供 `docker-compose.yml`。
- 镜像须可通过 **单条 `docker build` + 单条 `docker run`** 完成构建与启动。
- README 中给出运行命令、端口、环境变量说明。
- 推送到 Docker Hub 或 GHCR，提供公开镜像地址。
- CI 中包含镜像构建步骤。

### 4.11 云部署（可选）

学生可自由选择：

- 海外：Vercel / Render / Railway / Fly.io / AWS / GCP / Azure
- 国内：阿里云 / 腾讯云 / 华为云 / 火山引擎
- 多数厂商有学生免费额度，GitHub Student Pack 也包含若干云服务

要求：

- 提供截止日期前可访问的公网地址
- README 中说明部署架构、CI/CD、遇到的问题
- **注意控制成本**，优先使用免费额度

---

## 五、最终交付物清单

通过同一个 GitHub 仓库链接提交，包含：

1. `SPEC.md`、`PLAN.md`、`SPEC_PROCESS.md`
2. 完整源代码（带规范的 commit / PR 历史）
3. `Dockerfile`（与 `docker-compose.yml`，如适用）
4. `README.md`：项目简介、安装、运行、Docker 命令、目录结构
5. `AGENT_LOG.md`：智能体使用过程记录
6. CI 配置（`.github/workflows/`）
7. `REFLECTION.md`（1500–2500 字反思报告，详见下文）
8. （可选）线上部署 URL
9. （可选）5–10 分钟演示视频链接

### 反思报告（`REFLECTION.md`）建议内容

至少回答以下问题：

- 哪些 Superpowers 技能在你的项目里发挥了最大作用？哪些感觉是"形式大于实质"？
- TDD 强制在 AI 协作下的体感如何？它是阻碍还是放大器？
- subagent-driven 工作流让智能体能自主跑多久不偏题？什么样的 task 拆解颗粒度最优？
- SPEC 与 PLAN 的质量如何影响了后续实现质量？是否有过"规约不清晰导致 subagent 跑偏"的具体案例？
- 你设计的最有效的 prompt / context 策略是什么？为什么有效？
- （若使用了 Open Design）它的 skill 库与设计系统在多大程度上消除了"AI 生成界面千篇一律"的问题？
- 如果重做，你会改变哪些做法？
- 你对 Superpowers 这套方法论的批判：它假设了什么？这些假设在你的项目里成立吗？
- 你对当前 AI4SE 工具与方法论的整体看法。

---

## 六、学术规范声明

- 若有部分代码你认为更适合自己手写（如核心算法），请在该文件或函数顶部明确注释。
- 使用第三方代码必须遵守其许可证，并在 README 中列出。
- 反思报告必须由学生本人撰写，禁止使用 AI 代写（可用 AI 辅助润色，但需标注）。

---

## 七、推荐资源

**必读**

- Superpowers 仓库与文档：[https://github.com/obra/superpowers](https://github.com/obra/superpowers)
- Superpowers 发布博文（Jesse Vincent）：[https://blog.fsck.com/2025/10/09/superpowers/](https://blog.fsck.com/2025/10/09/superpowers/)
- Open Design 仓库与文档（前端 / UI 项目必读）：[https://github.com/nexu-io/open-design](https://github.com/nexu-io/open-design)
- 你所选编码智能体的 Superpowers 安装与使用文档

---

## 八、其它

这门课最想教给你的，不是"如何让 AI 替你做作业"，而是 **当 AI 能完成大部分编码工作时，一个工程师的真正价值在哪里**。

Superpowers 给你的是"流程脚手架"——它替你管住了 TDD、评审、计划这些容易在 AI 协作中崩塌的纪律。但它不能替你回答"做什么"和"做对了吗"。这两个问题，是这门课要训练你拥有的判断力。

如果你只是把题目扔给 Superpowers 然后把结果原封不动交上来，你很难真正完成本项目的目标——本项目鼓励 **你能解释 Superpowers 为什么这样做、它在哪里仍然不够好、你如何引导它做对**。

希望这个项目让你对自己作为软件工程师在 AI 时代的角色，有一个更清醒、更踏实的认识。
