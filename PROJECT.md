# 项目定位

- 中文名称：土老板。
- English：Mr.Moneybags。
- AI Secretary：小江 / JIA（Jiang Intelligent Assistant）。
- 类型：个人 Agent Harness。
- 核心关系：土老板负责目标，小江负责管理，Agent 负责执行。

## 当前阶段

按 v5.0 新路线图，Phase 0–3 已完成，Phase 4 新增 Intent Specification & Task Readiness。规格是可追溯、不可变、带版本的工程意图快照；就绪评估只判断是否可进入 Phase 5，不执行分解、规划或任务。

路线图重编号不代表跳过工作：旧 Phase 2A + 2B → 新 Phase 2；旧 Phase 2C → 新 Phase 3；旧 Phase 2D → 新 Phase 4；旧 Phase 2E → 新 Phase 5；旧 Phase 3 → 新 Phase 6。历史提交与实现保持原样。

| 阶段 | 定位 |
| --- | --- |
| Phase 0 | Foundation |
| Phase 1 | Task Intake |
| Phase 2 | Project Understanding |
| Phase 3 | Human Intent & Alignment |
| Phase 4 | Intent Specification & Task Readiness |
| Phase 5 | Task Decomposition & Agent Task Package |
| Phase 6 | Codex Integration |
| Phase 7 | Execution Governance |
| Phase 8 | Verification & Stable State |
| Phase 9 | Recovery & Escalation |
| Phase 10 | Checkpoint Review & Reporting |
| Phase 11 | Integrated MVP |

采用 Python 3.11+、标准库命令行入口和 unittest。选择普通 Python 包布局，直接在根目录运行；不引入应用框架或运行依赖。context 保持 Phase 2B 的数据模型、证据读取和确定性推导；其他预留模块保持空白。

## 核心原则

- Keep it simple.
- One task → One verification → One checkpoint.
- 目标由用户决定，管理与执行职责保持清晰。
- 每次变更保持小范围、可运行、可验证。
- 不为假设中的未来需求增加依赖、抽象或假实现。
- 不提交 API Key、Token、Password 或其他 Secret。
- 外部操作必须有明确授权；不自动执行生产环境操作。

## Phase 4 边界

Task 使用标准库 dataclass，ID 使用 UUID4，goal 仅清理首尾空白，原始输入保留，未指定字段为待补充状态，初始状态为 NEW。CLI 与数据模型分离，不模拟智能推理。

Ground Truth != AI Interpretation。WorkspaceObservation 独立于 Task 与 CLI，固定标注 Tier 0 — Direct Evidence。只采集真实 cwd、Git 命令结果和有界文件列表；未知状态保留 null，不解释文件内容，不推断项目意图，不修改被观察工作区。

Ground Truth != Project Understanding。Evidence != Interpretation。Context can be derived. Truth must be observed or verified.

ProjectContext 使用 Derived Context / Interpretation 标识。重要结论保留来源路径，来源附带内容哈希与字节数。只执行有限、透明的规则；声明不同则显式记录，缺失内容保持未知。文档中的测试或完成状态不是运行事实。Context Builder 仍不接收 Task，不推导用户意图。

证据读取限定允许清单、最多 8 个候选、单文件 32 KiB、总量 96 KiB；不打开敏感路径，不跟随链接，不执行任何证据中的命令。已知二进制路径直接排除；伪装文本经过有界字节检查后拒绝，不用于推导。

Conversation 原样保存多轮证据；IntentStatement、Ambiguity、Assumption 关联话轮来源。CurrentIntent 使用 Derived Intent / Interpretation 标识，保留目标、约束、范围、偏好、假设、问题和当前对齐状态，与项目证据及 Task 状态分离。历史解释通过 supersedes 关联，不覆盖原文。

决策归属分为 USER、JIA_AGENT、SHARED。歧义本身不足以打断用户：只有影响方向、范围、用户可见行为或重要后果的歧义通常需要确认。内部细节由 JIA/Agent 负责；仅在门槛以下采用显式 LOW、可逆假设，不将 ACTIVE 假设冒充用户确认。

CONFIRMED 必须来自绑定当前 revision 的 JIA 确认请求及完整受控肯定回复，且没有未解决的实质问题。含糊回复、拒绝、旧版本确认和普通继续发言都不会自动确认。该状态不是执行许可；本阶段没有执行器。

Task 是原始接收层；CurrentIntent 是活动解释；IntentSpecification 是独立版本快照。ProjectContext 不制造用户意图。声明、话轮、确认、假设和阻塞项的来源均保留，假设不自动变成已确认决策。

UNKNOWN != AMBIGUOUS != BLOCKING。就绪取决于目标、实质歧义、决策归属、可逆性和必要确认，不取决于 confidence 阈值或字段齐全。安全内部细节不阻塞，破坏性操作未确认则阻塞。READY 只允许进入后续规划阶段，不替代未来执行审批。

快照通过显式版本关联替代旧规格，历史对象不被改变；不自动识别语义变化，不持久化。有限冲突检查仅覆盖活动认证行为冲突与同名范围包含/排除，不实现通用语义推理。

不调用 Codex、LLM 或其他 Agent；不实现 Prompt、Agent Task Package、Execution Contract、Task Decomposition、Planner、Policy/Approval、Verification/Recovery、Stable State、Context Staleness、Memory、RAG、Vector Database、MCP、Skills 集成、Multi-Agent、A2A、UI、数据库、后台观察、事件监听或 ModelRouter。不提前实现新 Phase 5 及以后功能。

## 验收与检查点

运行全部测试及导出、内部重构、破坏性数据操作三个真实 CLI 示例。检查证据、项目解释、意图对齐、规格及就绪结果；确认不过度提问、不发明默认需求、不执行操作、不新增依赖，并检查读取安全、工作区变化、Git 差异与状态。全部通过后创建指定本地提交，不 push，停止 Phase 4。
