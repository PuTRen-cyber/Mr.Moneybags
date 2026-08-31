# 项目定位

- 中文名称：土老板。
- English：Mr.Moneybags。
- AI Secretary：小江 / JIA（Jiang Intelligent Assistant）。
- 类型：个人 Agent Harness。
- 核心关系：土老板负责目标，小江负责管理，Agent 负责执行。

## 当前阶段

Phase 0–2B 已完成。Phase 2C 新增独立项目会话、有限意图提取、歧义检测、决策归属和对齐门槛。只验证确定性领域链路，不实现任务执行、完整自然语言理解或持久化。

采用 Python 3.11+、标准库命令行入口和 unittest。选择普通 Python 包布局，直接在根目录运行；不引入应用框架或运行依赖。context 保持 Phase 2B 的数据模型、证据读取和确定性推导；其他预留模块保持空白。

## 核心原则

- Keep it simple.
- One task → One verification → One checkpoint.
- 目标由用户决定，管理与执行职责保持清晰。
- 每次变更保持小范围、可运行、可验证。
- 不为假设中的未来需求增加依赖、抽象或假实现。
- 不提交 API Key、Token、Password 或其他 Secret。
- 外部操作必须有明确授权；不自动执行生产环境操作。

## Phase 2C 边界

Task 使用标准库 dataclass，ID 使用 UUID4，goal 仅清理首尾空白，原始输入保留，未指定字段为待补充状态，初始状态为 NEW。CLI 与数据模型分离，不模拟智能推理。

Ground Truth != AI Interpretation。WorkspaceObservation 独立于 Task 与 CLI，固定标注 Tier 0 — Direct Evidence。只采集真实 cwd、Git 命令结果和有界文件列表；未知状态保留 null，不解释文件内容，不推断项目意图，不修改被观察工作区。

Ground Truth != Project Understanding。Evidence != Interpretation。Context can be derived. Truth must be observed or verified.

ProjectContext 使用 Derived Context / Interpretation 标识。重要结论保留来源路径，来源附带内容哈希与字节数。只执行有限、透明的规则；声明不同则显式记录，缺失内容保持未知。文档中的测试或完成状态不是运行事实。Context Builder 仍不接收 Task，不推导用户意图。

证据读取限定允许清单、最多 8 个候选、单文件 32 KiB、总量 96 KiB；不打开敏感路径，不跟随链接，不执行任何证据中的命令。已知二进制路径直接排除；伪装文本经过有界字节检查后拒绝，不用于推导。

Conversation 原样保存多轮证据；IntentStatement、Ambiguity、Assumption 关联话轮来源。CurrentIntent 使用 Derived Intent / Interpretation 标识，保留目标、约束、范围、偏好、假设、问题和当前对齐状态，与项目证据及 Task 状态分离。历史解释通过 supersedes 关联，不覆盖原文。

决策归属分为 USER、JIA_AGENT、SHARED。歧义本身不足以打断用户：只有影响方向、范围、用户可见行为或重要后果的歧义通常需要确认。内部细节由 JIA/Agent 负责；仅在门槛以下采用显式 LOW、可逆假设，不将 ACTIVE 假设冒充用户确认。

CONFIRMED 必须来自绑定当前 revision 的 JIA 确认请求及完整受控肯定回复，且没有未解决的实质问题。含糊回复、拒绝、旧版本确认和普通继续发言都不会自动确认。该状态不是执行许可；本阶段没有执行器。

不调用 Codex、LLM 或其他 Agent；不实现 Prompt、Agent Task Package、Task Decomposition、Planner、Policy/Approval、Verification/Recovery、Stable State、Context Staleness、Memory、RAG、Vector Database、MCP、Skills 集成、Multi-Agent、A2A、UI、数据库、后台观察、事件监听或 ModelRouter。不提前实现 Phase 2D/2E/3。

## 验收与检查点

运行全部测试及导出、内部重构、破坏性数据操作三个真实 CLI 示例。分别检查证据、项目解释和意图对齐；确认不过度提问、不发明默认需求、不执行操作、不新增依赖，并检查读取安全、工作区变化、Git 差异与状态。全部通过后创建指定本地提交，不 push，停止 Phase 2C。
