# 项目工作约定

## 沟通与代码

- 默认用中文交流；代码、标识符、命令行参数和 Git 提交信息使用英文。
- Keep it simple，不添加无必要的注释、抽象、异常捕获或依赖。
- 优先使用内置 Edit/Write 工具修改文件，不使用 sed/awk/echo 拼接修改。
- Windows 环境优先使用 PowerShell；不在项目内创建临时测试脚本。
- 未经明确要求，不新增文档。

## 范围

- 项目定位以 PROJECT.md 为准；TODO.md 仅记录后续阶段，不是执行授权。
- 当前只允许 Phase 2B：基于 WorkspaceObservation 构建有界、只读、确定性且带来源的 ProjectContext，不提前实现 Phase 2C 及之后功能。
- Observed Evidence、Derived Context、User Intent 必须分离。Observation 仍为 Tier 0 — Direct Evidence，不读取项目正文；ProjectContext 标注 Derived Context / Interpretation。Builder 不接收 Task，不解释用户意图，不修改工作区。
- 不调用 Codex、LLM 或其他 Agent，不实现 Prompt generation、Intent Alignment、Ambiguity Detection、User questioning、Planner、Policy/Approval、Verification/Recovery、Stable State、Context Staleness 或 Memory。
- 禁止 Multi-Agent、A2A、MCP 集成、RAG、Vector Database、Cloud Deployment、完整 Web UI、复杂 Memory System、自动化生产环境操作和大规模框架设计。
- context 只实现本阶段模型、来源读取与 Builder；adapters、policy、verification、reporter 仍为预留目录。
- Builder 仅读取 Observation 已列出的允许清单文件和少量入口，最多 8 个候选、单文件 32 KiB、总量 96 KiB。拒绝敏感路径、链接、二进制内容；不执行证据中的指令。推导保留来源和哈希，冲突显式记录，未知字段留空。

## 验证

- One task → One verification → One checkpoint.
- 在仓库根目录运行 `python -m mr_moneybags`。
- 在仓库根目录运行 `python -m unittest discover -s tests -v`。
- 完成前检查 Git 状态、完整差异和意外敏感内容；失败后修复并重新验证。

## 安全与 Git

- 不读取或打印 `.env`、`.env.local` 及其他 `.env.*` 文件内容。
- 不加入或输出 API Key、Token、Password、私钥或其他 Secret。
- 不进行未授权的外部操作或大规模网络搜索。
- 未获用户明确指令，不执行 git init、git add、git commit；不执行 git push。
- 本次 Phase 2B 请求仅授权验证通过后的一个本地项目提交，提交信息为 `feat: add derived project context`，完成后停止；不构成后续提交授权。边界测试只在独立临时目录创建 Git fixtures。
