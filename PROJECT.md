# 项目定位

- 中文名称：土老板。
- English：Mr.Moneybags。
- AI Secretary：小江 / JIA（Jiang Intelligent Assistant）。
- 类型：个人 Agent Harness。
- 核心关系：土老板负责目标，小江负责管理，Agent 负责执行。

## 当前阶段

Phase 0–5.5C 已完成。Phase 5.5D 增加独立 Task Safety Gate，在未来委派前对既有 AgentTaskPackage 进行有限确定性检查。Phase 4/5 与语义契约保持不变；Phase 6 Codex Integration 暂停，等待实际语义理解通过 Shadow Evaluation，接入实现不等于质量验收。

路线图重编号不代表跳过工作：旧 Phase 2A + 2B → 新 Phase 2；旧 Phase 2C → 新 Phase 3；旧 Phase 2D → 新 Phase 4；旧 Phase 2E → 新 Phase 5；旧 Phase 3 → 新 Phase 6。历史提交与实现保持原样。

| 阶段 | 定位 |
| --- | --- |
| Phase 0 | Foundation |
| Phase 1 | Task Intake |
| Phase 2 | Project Understanding |
| Phase 3 | Human Intent & Alignment |
| Phase 4 | Intent Specification & Task Readiness |
| Phase 5 | Rolling Planning, Current Work Unit & Agent Task Package |
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

## Phase 5.5C 边界

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

JIA 管理 WHAT / WHY / 阶段与边界，Coding Agent 管理普通 HOW。轻量指少打断、少重复且复杂度与任务相称。规划不生成完整项目蓝图，也不做贪心任务评分或实现琐事拆分。

planning 是独立纯领域模块。无明确未来考虑时走 FAST_PATH，将当前范围保持为一个可验证成果；明确未来考虑触发 ROLLING，后续方向只是未承诺导航。未来方向最多三个，超出时合并并保留来源。当前范围不会因未来方向而扩大；对无法识别阶段的复杂范围不宣称通用规划能力。

工作包分别保留用户解释、工作假设和项目证据；所有规划规则附来源。已有测试方式可作为验证期待的依据，不变成用户偏好或执行命令。简报仅显示当前目标、理由、范围和完成条件。READY_FOR_DELEGATION 不是已执行或已审批。

计划、工作单元与包使用不可变版本快照，替代关系显式记录，历史含义保留。不自动推进阶段，不持久化。

Model interprets; domain decides。唯一外部调用为显式选择后的语义模型请求；OpenAI 和 DeepSeek HTTP 适配器位于 providers，必须显式指定提供方，模型领域不依赖厂商 API。没有 SDK、新运行依赖、自动路由、重试或回退。

Semantic Interpreter consumes Semantic Context, not full Project Context。当前 user 原文最多 8000 字符，此前最多 4 轮、每轮 4000 字符；超限拒绝而非截断原文。可选摘要每组最多 8 项、每项 240 字符，目标 240 字符；可选项目事实默认空、最多 8 项、内容 512 字符、来源 240 字符。摘要和事实仅作参考，不能冒充 Human 证据；不读取新工作区内容，不发送完整项目上下文。

模型输出复用 SemanticResult；严格拒绝额外字段及缺失结构。只验证发送窗口内的 user 精确片段，不修复引用、不提升信任等级。TransportFailure、ModelOutputFailure、EvidenceValidationFailure 分别表示传输、输出和证据问题；错误保留原话轮并阻止下游构建。模型修订产生新的候选快照，以原有 previous/supersedes 机制保留旧规格，不引入记忆系统。

不调用 Codex 或其他 Agent；不实现 Coding Agent Prompt、AgentAdapter、执行、监控、Policy/Approval、Verification/Recovery、Stable State、Memory、RAG、Vector Database、MCP、Skills 集成、Multi-Agent、A2A、UI、数据库、后台观察、进度轮询或 ModelRouter。不提前实现 Phase 6。

## 验收与检查点

Task Safety Gate 仅检查工作包中的目标、范围、约束、行为要求和验收条件。缺失目标会阻止委派；有限的破坏性操作、敏感区域和整体范围扩张规则要求确认；普通开发工作保持 LOW/ALLOW。规则不使用 LLM，不授予执行权限，不代表完整安全保证或自主审批，也未接入 Agent。

语义层区分当前目标/范围、未来考虑、受保护约束、普通实现委派和实质歧义。每项解释关联 user 原文片段，解释不是引用本身；引用验证不能证明解释忠实。未来内容不进入当前工作单元及验收条件；普通实现委派不授权破坏性操作、发布、push 或扩展产品范围。

Phase 4/5 领域规则不重构。默认与注入解释器统一经过证据验证；解释失败保留原文并输出结构化错误，不回退到旧路径、不生成可执行规格。默认适配仅支持单用户话轮，证据粒度为完整话轮；不提供通用语义理解。运行时集成测试证明契约已接线，不代替真实 Shadow Evaluation。CLI 内部 JSON 过多仍留待后续交互工作；本阶段不实现 Reporter。

运行全部回归及运行时集成测试；验证默认路径和模型模式调用同一语义边界、模拟 HTTP/客户端结果改变实际下游状态、保护约束/普通委派/当前未来分离/修订贯穿原管线，错误安全停止。单元测试不访问外部网络。真实模型 smoke 仅在已安全配置环境凭据和模型后运行；本次未配置，未执行，不宣称真实 Shadow Gate 通过。检查安全、Git 差异与状态。全部通过后创建指定本地提交，不 push，停止 Phase 5.5C。
