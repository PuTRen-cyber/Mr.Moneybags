# 项目定位

- 中文名称：土老板。
- English：Mr.Moneybags。
- AI Secretary：小江 / JIA（Jiang Intelligent Assistant）。
- 类型：个人 Agent Harness。
- 核心关系：土老板负责目标，小江负责管理，Agent 负责执行。

## 当前阶段

Phase 0 工程骨架、Phase 1 Task intake 与 Phase 2A Workspace Observation 已完成。Phase 2B 新增独立 Context Builder，依据 Observation 中少量项目文件推导带来源的 ProjectContext。不实现任务执行、用户意图理解或持久化。

采用 Python 3.11+、标准库命令行入口和 unittest。选择普通 Python 包布局，直接在根目录运行；不引入应用框架或运行依赖。context 仅实现本阶段的数据模型、证据读取和确定性推导；其他预留模块保持空白。

## 核心原则

- Keep it simple.
- One task → One verification → One checkpoint.
- 目标由用户决定，管理与执行职责保持清晰。
- 每次变更保持小范围、可运行、可验证。
- 不为假设中的未来需求增加依赖、抽象或假实现。
- 不提交 API Key、Token、Password 或其他 Secret。
- 外部操作必须有明确授权；不自动执行生产环境操作。

## Phase 2B 边界

Task 使用标准库 dataclass，ID 使用 UUID4，goal 仅清理首尾空白，原始输入保留，未指定字段为待补充状态，初始状态为 NEW。CLI 与数据模型分离，不模拟智能推理。

Ground Truth != AI Interpretation。WorkspaceObservation 独立于 Task 与 CLI，固定标注 Tier 0 — Direct Evidence。只采集真实 cwd、Git 命令结果和有界文件列表；未知状态保留 null，不解释文件内容，不推断项目意图，不修改被观察工作区。

Ground Truth != Project Understanding。Evidence != Interpretation。Context can be derived. Truth must be observed or verified.

ProjectContext 使用 Derived Context / Interpretation 标识。重要结论保留来源路径，来源附带内容哈希与字节数。只执行有限、透明的规则；声明不同则显式记录，缺失内容保持未知。文档中的测试或完成状态不是运行事实。Builder 不接收 Task，User Intent 属于尚未实现的 Phase 2C。

证据读取限定允许清单、最多 8 个候选、单文件 32 KiB、总量 96 KiB；不打开敏感路径，不跟随链接，不执行任何证据中的命令。已知二进制路径直接排除；伪装文本经过有界字节检查后拒绝，不用于推导。

不调用 Codex、LLM 或其他 Agent；不实现 Prompt generation、Intent Alignment、Ambiguity Detection、User questioning、Planner、Policy/Approval、Verification/Recovery、Stable State、Context Staleness、Memory、RAG、Vector Database、MCP、Multi-Agent、A2A 或 Web UI。不提前实现 Phase 2C 及之后的功能。

## 验收与检查点

运行全部测试与真实 CLI，分别检查 Observation 和 ProjectContext，人工核对至少一个结论的来源；确认状态声明没有冒充事实、读取安全和工作区未被 Builder 修改。检查 Git 差异、状态和意外敏感内容。验证失败必须先修复并重新验证。全部通过后创建指定本地提交，不 push，停止 Phase 2B。
