# 项目定位

- 中文名称：土老板。
- English：Mr.Moneybags。
- AI Secretary：小江 / JIA（Jiang Intelligent Assistant）。
- 类型：个人 Agent Harness。
- 核心关系：土老板负责目标，小江负责管理，Agent 负责执行。

## 当前阶段

Phase 0 工程骨架与 Phase 1 Task intake 已完成。Phase 2A 在 Task 接收后只读观察当前工作区，展示结构化 WorkspaceObservation。不实现任务执行或持久化。

采用 Python 3.11+、标准库命令行入口和 unittest。选择普通 Python 包布局，直接在根目录运行；不引入应用框架或运行依赖。五个模块仅预留位置，职责和接口待后续阶段明确。

## 核心原则

- Keep it simple.
- One task → One verification → One checkpoint.
- 目标由用户决定，管理与执行职责保持清晰。
- 每次变更保持小范围、可运行、可验证。
- 不为假设中的未来需求增加依赖、抽象或假实现。
- 不提交 API Key、Token、Password 或其他 Secret。
- 外部操作必须有明确授权；不自动执行生产环境操作。

## Phase 2A 边界

Task 使用标准库 dataclass，ID 使用 UUID4，goal 仅清理首尾空白，原始输入保留，未指定字段为待补充状态，初始状态为 NEW。CLI 与数据模型分离，不模拟智能推理。

Ground Truth != AI Interpretation。WorkspaceObservation 独立于 Task 与 CLI，固定标注 Tier 0 — Direct Evidence。只采集真实 cwd、Git 命令结果和有界文件列表；未知状态保留 null，不解释文件内容，不推断项目意图，不修改被观察工作区。

不调用 Codex、LLM 或其他 Agent；不实现完整 Context Engine、Derived Context、Context Staleness、Policy Engine、Verification / Recovery、Multi-Agent、A2A、MCP 集成、RAG、Vector Database、Cloud Deployment、完整 Web UI、Memory、自动化生产环境操作或大规模框架设计。不提前实现 Phase 2B 及之后的功能。

## 验收与检查点

运行程序和真实工作区观察、运行全部测试、核对观察前后工作区未改变、检查 Git 状态及差异，并检查意外敏感内容。验证失败必须先修复并重新验证。全部通过后按本阶段授权创建一次本地 Git commit，不 push，停止 Phase 2A。
