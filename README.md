# 土老板 / Mr.Moneybags

个人 Agent Harness 项目。AI Secretary 为小江 / JIA（Jiang Intelligent Assistant）。

**土老板负责目标，小江负责管理，Agent 负责执行。**

当前为 Phase 5.5B — Runtime Semantic Interpretation Path：真实 CLI 统一经过 SemanticInterpreter → 语义验证 → CurrentIntent → 既有 Phase 4/5。默认解释器在接口内部复用原有限规则，未接入真实模型。六个部分展示 JSON 后退出。不调用 LLM、Codex 或其他 Agent，不执行任务或文档命令、不持久化，不启动聊天循环。

v5.0 路线图已重编号：旧 Phase 2A/2B 合并为新 Phase 2，旧 Phase 2C 对应新 Phase 3，旧 Phase 2D 对应新 Phase 4。没有跳过阶段，也没有重写已接受实现或 Git 历史。完整路线图见 PROJECT.md。

## 运行

需要 Python 3.11 或更高版本。在仓库根目录执行，无需安装第三方依赖：

```powershell
python -m mr_moneybags
```

输入示例（每次只接收一行，回车提交）：

```text
Mr.Moneybags | JIA - Submit one task; no agent execution.
Task: 请整理本周工作计划
```

随后输出包含 `id`、`raw_input`、`goal`、`expected_outcome`、`constraints`、`acceptance_criteria`、`status` 的 JSON。

- `id`：本地生成 UUID4 字符串。
- `raw_input`：完整保留输入行内容（不含提交用的行结束符）。
- `goal`：仅去除输入首尾空白，保留内部空白。
- `expected_outcome`、`constraints`、`acceptance_criteria`：默认 `null`，表示待补充，不推断用户意图。
- `status`：初始为 `NEW`。

空白任务会显示错误并以退出码 1 结束；输入流结束时不创建 Task，以退出码 0 结束。

## Workspace Observation

Task 后显示 `Workspace Observation:` 及独立 JSON，数据等级固定为 `Tier 0 — Direct Evidence`。Ground Truth != AI Interpretation。

- `cwd` 来自运行时 `Path.cwd()`；`files` 为相对于该目录的实际文件路径，使用 `/` 分隔。即使在 Git 子目录中启动，也只扫描当前目录及其下层。
- `is_git_repository`、`is_inside_work_tree`、`git_root`、`branch`、`head_commit` 来自 Git 的 `rev-parse` 和 `symbolic-ref`；`working_tree_clean` 来自仓库范围的 `git status --porcelain=v1`，包含暂存、未暂存和未忽略的未跟踪变更。
- 未安装 Git、权限问题、命令失败或超时的字段保留 `null`，并在 `errors` 记录错误码。非 Git 目录的 `is_git_repository` 为 `false`；无可解析提交时 `head_commit` 为 `null`；detached HEAD 时 `branch` 为 `null`。裸仓库或在 Git 内部目录运行时记录 `not_in_working_tree`，不声称工作树干净，也不扫描内部文件。
- 每条 Git 命令最多等待 5 秒。禁用可选锁和 fsmonitor；不运行写入命令。Git 状态出现警告也保留 `working_tree_clean: null`，不猜测结果。
- 文件扫描最多返回 200 个文件，检查 2,000 个目录项（包含被过滤项），向下进入 3 层目录。达到边界或访问失败时 `files_truncated` 为 `true`；结果排序，但受限扫描的子集取决于文件系统枚举顺序。
- 跳过 `.git`、`.venv`、`venv`、常见 Python 缓存、`.cache`、`.tox`、`.nox`、`node_modules`、`dist`、`build`、`secrets`、`.egg-info`；跳过 `.env`、`.env.*`、`.key`、`.pem`、`.pyc`、`.pyo`；不跟随符号链接或 Windows junction/reparse point。
- Observation 只读取目录项和文件元信息，不打开文件内容，不解释 README/PROJECT，不修改工作区。多个观察步骤不是原子快照，不保证扫描期间并发改动的一致性；不实现 Staleness。Derived Context 由下面的独立 Builder 生成，不写入 Observation。

## Project Context

`build_project_context(observation)` 不接收 Task。CLI 在 Observation JSON 后单独显示 `Project Context (Derived Understanding):`。

Observed Evidence 是观察到的证据；Derived Context 是项目证据的解释；User Intent 由独立的 Phase 3（旧 Phase 2C）conversation 模块处理。Context Builder 仍不处理用户意图。

- `ProjectContext` 包含项目名称、声明的摘要、技术、候选入口与测试命令、重要文件、架构说明、假设、来源、Python 版本声明、冲突、警告和实际读取字节数。可信级别固定为 `Derived Context / Interpretation`，不是 Tier 0，也不代表已验证的运行状态。
- 每条 `DerivedClaim` 保存 `value` 与 `sources`。来源路径关联 `SourceArtifact` 的路径、SHA-256 和完整字节数；不保存完整文件正文。哈希标识本次读取内容，不实现自动过期检测。
- 只从 Observation 已列出的路径中选择，不重新递归搜索。根目录允许清单按顺序为 `pyproject.toml`、`README.md`、`PROJECT.md`、`package.json`、`requirements.txt`、`Cargo.toml`、`go.mod`、`pom.xml`、`build.gradle`、`Makefile`、`AGENTS.md`；再考虑最多两个已观察到的 `__main__.py`、`main.py`、`app.py`、`manage.py`。入口路径最多四段，优先 `__main__.py`。
- 最多选择 8 个候选文件，单文件最大 32 KiB，总读取最多 96 KiB。超限文件跳过，不把部分内容当成完整证据；被拒绝文件的探测字节也计入总量。
- 打开前拒绝越界路径、绝对路径、Windows ADS、敏感路径、依赖/缓存/构建目录及符号链接、junction/reparse point、硬链接；路径的父目录也检查链接。敏感规则包括 `.env`、`.env.*`、`*.pem`、`*.key`、`credentials*`、`secrets*`，这些文件不打开。仅接受普通文件，并在读取前后核对打开文件的身份、大小和修改时间。
- 已知二进制文件名不在允许清单中。允许清单中的文件先检查最多 512 字节前缀，再在预算内检查完整内容；二进制特征或非 UTF-8 内容不进入证据集合。伪装成文本的二进制需要有界读取才能识别，不能保证零字节探测。
- 当前规则仅识别 Python 项目元数据、Python 入口、requirements 中的依赖声明，以及 package.json 中的 Node.js 项目和脚本声明。其他允许清单文件只保留为证据，不自动推断技术或架构。
- 项目名称与摘要优先取元数据；无声明时使用 README 首个标题和首个普通文本行。README 标题是显示名称的回退来源，不与包名自动作同名判断。Markdown 围栏及行内代码中的有限 Python/npm 命令仅作为候选；不会执行。AGENTS 内容在此仅是数据，不作为 Builder 指令。
- 元数据名称/摘要存在不同声明时，字段为 `null` 并保留全部候选。Python 版本声明的字面值不同会记录冲突及来源；不实现约束求解器，不声称这些声明一定不兼容。缺失信息为 `null` 或 `[]`，架构说明和假设默认留空。
- README 的 “Tests pass” 或 PROJECT 的“已完成”不产生 `tests_passed`、已完成功能等真实状态。`source_declarations_are_unverified` 提醒这些声明未被验证。无 Git 项目同样可生成有限 Context。

## Conversation / Intent Alignment

CLI 将 Task 原始输入原样放入首个 user 话轮，输出会话证据和独立 AlignmentResult，其中包含 Current Intent、Ambiguities、Assumptions、Questions Required、Alignment State。Task.status 保持独立，既不复制为对齐状态，也不代表执行授权。

- `ProjectConversation` 可追加 user/jia 话轮，保留 UUID、顺序和原始文本。`ConversationTurn` 与派生 `IntentStatement` 不可变；后续解释通过 `supersedes` 引用旧解释，不删除历史证据。
- `IntentExtractor` 识别有限中英文模式：I want / I need / 我想、must / 必须、do not / should not / 不要、I prefer、以后、include / exclude、expected outcome，以及显式格式说明。未知文本仅作为低置信度目标候选，不模拟完整 NLP；同轮多个目标合并表达，不分解任务。
- 每条解释、歧义和假设保留 `source_turn_ids`。解释标注 `Derived Intent / Interpretation`，与原始话轮证据分开。confidence 为固定规则标记（0.8 命中规则、0.5 原句候选），不是已验证概率。
- `CurrentIntent` 包含目标、预期结果、约束、偏好、范围内/外、行为要求、未来考虑、假设、待确认问题、来源、revision 和状态。项目技术声明不自动成为用户偏好；ProjectContext 不传给意图解析器。Ambiguity 的 `context_sources` 可表达项目证据冲突，但本阶段不自动推理这类冲突。
- 确定性歧义检测覆盖未指定导出格式、模糊视觉方向、内部重构、破坏性数据操作、少量技术权衡以及意图替代。候选解释不是选定需求；不为导出发明默认格式，不用无关偏好消除视觉问题。

决策归属和对齐门槛：歧义本身不意味着打断用户。

| 情况 | 是否要求确认 |
| --- | --- |
| USER：用户可见行为、范围、视觉方向、破坏性行为；MEDIUM/HIGH | 是 |
| JIA_AGENT：私有命名、内部组织、普通重构；LOW/MEDIUM | 通常否；涉及不可逆或高影响假设时要求确认 |
| SHARED：影响成本、安全、性能等技术权衡；HIGH | 是 |
| SHARED + MEDIUM | 无安全假设时要求确认 |
| LOW 且可逆的普通问题 | 不因缺信息自动提问 |

只采用低于门槛、LOW、可逆、ACTIVE 的显式假设。普通内部重构可假设“自行选择私有命名和组织方式，保持可观察行为”，并说明理由；明确要求改变行为时不套用该假设。假设仍是 ACTIVE，不是用户确认。领域枚举预留 SUPERSEDED/DEFERRED 等状态，不实现完整决策历史或自动延后机制。

对齐状态为 DRAFT / ALIGNING / CONFIRMED。无阻塞问题并不自动成为 CONFIRMED。展示 CurrentIntent 后，调用 `conversation.request_confirmation(current_intent)` 记录绑定 revision 的 JIA 确认请求，再追加用户回复。

- 只识别完整受控回复：yes、correct、confirmed、continue、that's right、对、是、没问题、确认、继续；拒绝为 no、not correct、不对、不是、不要。首尾空白和简单句末句号/感叹号可忽略，不解释情绪。
- 无绑定请求、旧版本请求、普通继续发言都不能确认当前意图。含糊回复保持 ALIGNING，使待确认请求失效；需要重新展示和请求确认。
- “yes”只能确认已展示且已明确的理解；不能替用户选择未知导出格式。破坏性操作和方向替代需显式确认，确认仅改变对齐状态，不执行、不授权操作。
- 拒绝使理解继续 ALIGNING，相关假设标记 REJECTED；新增实质内容使旧确认失效。新目标或明确更正可替代旧解释，双方来源保留，方向变化要求确认。

会话层不实现 LLM、Prompt、规划、Policy/Approval、Agent 执行、持久化、后台监听或 UI。CLI 仅展示所需问题的结构化 topic/reason/priority，不生成 AI 问句，也不追问输入。

## Intent Specification / Readiness

`build_intent_specification(alignment, previous=None)` 从 AlignmentResult 的 CurrentIntent 建立不可变规格，`evaluate_readiness(specification)` 独立返回 READY / NOT_READY、阻塞原因、非阻塞未知项及生效假设。两者均为无文件、命令或网络操作的纯领域逻辑。

- `IntentSpecification` 保留目标、预期结果、范围、行为要求、约束、偏好、未来考虑、用户决策、工作假设、问题、阻塞项、来源、版本和状态；可信级别为 `Derived Intent Specification / Interpretation`。未知字段保持空，不填充技术方案。
- 用户决策保存原 IntentStatement（包含声明 ID、原话轮来源及解释标识）和单独的确认话轮 ID。工作假设保留 Assumption ID、理由、可逆性、影响与状态；即使已确认也保留假设来源，不冒充原始用户声明。未确认的候选决策不声称已获确认。
- `source_intent_version` 引用 CurrentIntent.revision；阻塞原因关联声明、话轮、歧义或假设 ID。构建器直接消费现有领域结果，不重新理解对话，也不接收 Task 或 ProjectContext 来制造意图。
- 有意义目标且无实质阻塞即可 READY，无须所有字段完整或所有意图都是 CONFIRMED；不以 confidence 数值决定就绪。空文本、纯标点及少量明确无意义短语会被阻塞，这不是通用语义判断。
- 未解决的必要问题、重要用户选择、高影响共享决策、未确认破坏性操作、未解决方向冲突均阻塞。HIGH 问题不能仅靠 DEFERRED 绕过。低影响内部未知项保留但不阻塞；只有门槛以下 LOW、可逆的工作假设可以生效。
- 额外矛盾检查刻意有限：活动认证行为保留约束与认证替换要求冲突、相同范围项同时包含/排除。已有 Phase 3 supersedes/resolution 会被保留；不会无条件采用最新声明覆盖其他仍生效约束，不声称理解任意自然语言矛盾。
- Builder 返回 BLOCKED 或 READY 快照；DRAFT 表示尚未评估的规格。冻结 dataclass 和 tuple 防止 CurrentIntent 后续修改影响快照。同一输入的 ID/序列化稳定；显式传入 previous 时建立下一版本并记录 supersedes，不自动判断语义变化。
- `supersede_specification(old, new)` 返回标记 SUPERSEDED、保留原含义的历史副本，并关联新 ID；不原地改变旧对象，不删除历史。调用方保留这些内存快照；本阶段无持久化或自动监听。就绪评估拒绝已被替代的历史副本。
- READY 仅表示可进入后续工程分解，不是执行授权。有效且绑定当前意图版本的确认可解除破坏性请求的 Phase 4 阻塞，但未来执行时仍可能需要审批。规格层不进行分解、规划或执行。

真实 CLI 的代表性结果：

| 输入 | 规格 / 就绪结果 |
| --- | --- |
| I want to add export functionality. | BLOCKED / NOT_READY；格式待定，不选择 CSV |
| Refactor the internal authentication helper without changing behavior. | READY；保留行为和显式工作假设，不追问内部命名 |
| Delete all user data and reset the database. | BLOCKED / NOT_READY；MISSING_REQUIRED_CONFIRMATION |

## Planning

v5.1 原则：JIA 管理意图、阶段和边界，Coding Agent 管理普通实现决策。轻量意味着少打断、少重复，复杂度与任务相称。

- `Planner.plan(specification, project_context, previous=None)` 返回独立 `PlanningResult`。规格必须为 READY，且重新进行 Phase 4 就绪评估；BLOCKED、DRAFT、SUPERSEDED 或残留阻塞返回结构化失败，不修复需求、不猜导出格式、不生成可委派包。
- 保守规则将当前已约定范围保持为一个有意义工作单元，不拆成文件、函数、字段或命令。无明确未来考虑时 FAST_PATH；有明确 future_considerations 时 ROLLING。不做通用语义规划，也不假装能自动分离任意多能力请求；需要更细阶段时应先明确规格。
- `PlanningHorizon` 保留总目标、版本、当前阶段和未来方向。未来最多三个粗略方向；超过三个时将第三项起合并展示，保留全部来源并发出提示。不是固定产生三个阶段，没有未来考虑就不生成未来阶段。
- `PlanStage` 保留目标、范围摘要、选择理由和来源。未来方向标为 FUTURE、committed=false，无文件清单、命令或实施步骤。未来考虑同时明确排除于当前工作，不把 scope_out 自动提升为未来方向。
- `CurrentWorkUnit` 包含目标、why_now、范围内外、约束、行为要求、验收条件、验证期待、实现自由度、假设和规格/阶段来源。验收条件由当前目标、预期结果、范围和约束生成符合性检查，标注 planning_rule；不发明数值指标、架构或产品能力。
- 普通私有命名、内部组织、重构细节及实施顺序交给 Agent，在当前范围和约束内自主决定。保留行为的要求可推导“不新增可见行为或超范围重设计”边界，明确标注规划规则和原声明来源。
- `AgentTaskPackage` 是与 Agent 无关的结构化工作条件，不是提示词。它复制当前工作单元的条件，分别保留 user_decisions 与 working_assumptions，以及规格、阶段、工作单元和证据来源。READY_FOR_DELEGATION 仅表示包已备妥，不代表委派、执行或审批已经发生。
- ProjectContext 仅提供单独的派生证据摘要（技术、入口、现有测试方式等）与可用来源哈希；测试命令是未验证证据，不是待执行指令。上下文技术不会变成用户偏好或需求。
- `StageBriefing` 仅含阶段标题、当前目标、理由、范围内外和完成条件，供用户预览，不混入内部 ID，不是审批系统。
- 规划与包是 frozen dataclass/tuple 快照，输入和序列化相同则 ID 稳定。显式 superseding 规格可通过 previous 建立下一版本；`supersede_plan(old, new)` 返回保留原内容、标记 SUPERSEDED 的历史副本，不修改旧对象、不自动推进阶段、不持久化。
- CLI 保留原部分，追加 `Planning:` 紧凑 JSON，包括 horizon、一个 work unit、briefing 和 package；仍为一次输入。作业场景使用测试中的 READY fixture，未扩大既有自然语言提取规则。

| 场景 | 结果 |
| --- | --- |
| 认证内部重构，保持行为 | FAST_PATH；一个工作单元，无未来阶段 |
| 作业创建/查看/课程关联，未来提交和评分 | ROLLING；提交/评分不进入当前范围，不新增通知方向 |
| 导出格式未定 | success=false；没有工作包 |
| 内部 parser 改名 | FAST_PATH；无人工路线图 |

Phase 6 仍为 Codex Integration，尚未实现。本阶段无执行、Agent 调用、监控、LLM、Prompt、Policy/Approval、Verification/Recovery、UI 或数据库。

## Semantic Interpretation

`SemanticInterpreter.interpret(turns) -> SemanticResult` 是可注入的供应商无关接口。`interpret_conversation(conversation, interpreter=None)` 是唯一运行时解释入口：未注入时选用 DeterministicInterpreter，注入时使用调用方实现，两者都经过相同证据验证，再生成 AlignmentResult / CurrentIntent，继续沿原 Specification → Readiness → Planning → Package 流转。CLI 不直接调用旧提取器或旧 analyze_conversation。`cli.main(interpreter=...)` 是测试及未来实现的注入点；默认 `python -m mr_moneybags` 同样经过这个边界。本阶段没有模型 SDK、网络调用、句子查表或新增语言规则库。

DeterministicInterpreter 仅将既有 IntentExtractor 的单轮结果转换为 SemanticClaim，用完整输入话轮作为粗粒度原文证据；不声称自动定位了最小语义片段。空输入结果保留为空；多用户话轮返回明确不支持错误，不悄悄丢弃历史。旧 analyze_conversation 仍保留供既有领域测试/独立 API 使用，但不再是 CLI 的旁路。

无效语义结果显示 `Interpretation Failure` 结构化输出（success=false、错误码、原始 conversation），退出码为 1，不生成规格或计划、不回退到旧路径。解释器意外异常转换为 interpreter_failed，不输出内部异常内容。Task 原始输入始终保留。

- `SemanticClaim` 分开表达 goal、expected_outcome、behavior_requirement、constraint、scope_in/out、preference 和 future_consideration；concept_id 关联同一语义对象，禁止同一对象同时标为未来和当前目标/范围/行为/结果。未来与 scope_out 可以并存。
- 每条声明和语义歧义必须引用 user 话轮的非空原文片段：turn_id、按 Python 字符索引计的 start/end（左闭右开）、quote。验证话轮角色、精确切片、边界、类型、唯一 ID、单一目标/预期结果及最新用户话轮；拒绝伪造引用和过期结果。
- 验证上限为 64 条声明、32 条歧义、每项 8 个证据片段。验证失败抛出 SemanticValidationError；CLI 显示错误码并停止，不回退成可执行规格。
- IntentStatement 兼容扩展 evidence、protected_target 和 implementation_delegation；Ambiguity 增加 evidence。旧调用的默认值保持空。受保护目标只能附在 constraint/scope_out，委派只能附在 constraint，唯一支持值是 ordinary_implementation_within_scope_and_constraints。
- protected_target 表示显式受保护对象；约束内容及证据保留到规格，完整声明通过工作包 user_decisions 传递。普通实现委派不包含删除、发布、push、扩大范围或忽略约束的授权。
- 语义歧义复用既有归属、影响程度和对齐门槛；保留原歧义检测，普通委派不会消除实质导出选择或高影响用户问题。语义解释不创建 CONFIRMED；结果版本取决于完整语义结果，同一话轮的新解释也会改变 revision。
- 声明仍标记 Derived Intent / Interpretation、CANDIDATE；confidence=0.5 仅为兼容标记，不是模型概率，也不决定就绪。接口不接受模型生成的执行授权或隐式工作假设；原检测器的安全假设仍独立保留。
- 测试替身仅在测试内注入结构化结果，不按输入句子查表。原句和改写案例验证 README/认证保护、普通实现委派、作业当前与未来分离、导出阻塞、重构和固定目标改名。

**限制：**运行时现已经过语义契约，但默认确定性解释器仍有限。引用匹配只证明证据存在，不证明语义蕴含，也无法识别被错误赋予不同 concept_id 的同义内容。未接入真实语义模型，复杂中文理解没有因此自动提升；fixture 和运行时集成测试通过不等于真实 Shadow Evaluation 已通过。语义入口只生成候选快照，不实现语义确认对话或决策历史管理。模型驱动理解仍为未来工作，Phase 6 保持暂停。

成功路径不增加输出段落，不展示供应商/模型内部信息；失败路径单独显示结构化解释错误。隐藏新增元数据的空值。现有 CLI JSON 仍偏多，后续人类可读输出设计见 TODO，本阶段不实现 Reporter。

## 测试

```powershell
python -m unittest discover -s tests -v
```

测试保留 Task 与 CLI 生命周期验证，并在隔离临时目录中覆盖 Git 仓库、无提交、非仓库、干净与脏状态、无 Git、超时、过滤与扫描边界，以及观察前后文件和 Git 索引不变。Git fixtures 只在临时目录创建仓库与提交，不依赖当前项目仓库或用户的提交身份；需要本机安装 Git，无 Git 时相关真实仓库测试会跳过，异常路径测试仍可运行。

Context 测试覆盖规则与来源、冲突、缺失文件、模型分离、文件数量及字节预算、敏感/二进制过滤、链接和文件替换、无写入与不执行命令。

Conversation 测试覆盖多轮原文、解释来源、决策归属、门槛、安全假设、版本绑定确认、拒绝与含糊回复、历史替代、项目/意图分离以及不对实现细节过度提问。

Specification 测试覆盖来源与字段保留、决策/假设分离、实质阻塞、非阻塞未知项、确认有效性、有限矛盾检测、不可变快照、版本替代及无 IO；保留已有 84 项回归测试。

Planning 测试覆盖 READY 门槛、FAST_PATH/ROLLING、当前范围与未来方向分离、实现自由度、工作包/简报、来源、历史替代及无 IO；保留 Phase 0–4 的 115 项回归测试。

## 目录

```text
mr_moneybags/
  __init__.py
  __main__.py
  cli.py          # 单次输入与 JSON 展示
  task.py         # 独立 Task 数据模型
  observation.py  # 只读工作区直接证据
  conversation/
    __init__.py
    models.py     # 会话、解释、歧义、假设与状态
    extractor.py  # 有限规则提取与受控确认信号
    ambiguity.py  # 有限歧义检测与归属
    alignment.py  # 门槛、替代关系与对齐状态
  adapters/       # Agent Adapter，预留
  planning/
    __init__.py
    models.py     # 滚动计划、当前工作单元、工作包与简报
    planner.py    # 有限确定性规划与历史替代
    package.py    # 项目证据摘要与结构化工作包
    briefing.py   # 简洁派发预览
  semantic/
    __init__.py
    models.py     # 语义声明与歧义契约
    interpreter.py # 解释器接口、证据验证与既有管线适配
    default.py    # 原确定性提取器的语义契约适配
  specification/
    __init__.py
    models.py     # 不可变规格、决策、阻塞原因和就绪结果
    builder.py    # 来源保留、快照与版本替代
    readiness.py  # 确定性就绪规则
  context/
    __init__.py
    models.py     # Derived Claim、Source Artifact、Project Context
    sources.py    # 允许清单与有界只读读取
    builder.py    # 确定性规则与来源、冲突记录
  policy/         # Policy，预留
  verification/   # Evaluator / Verification，预留
  reporter/       # Reporter，预留
tests/
  test_startup.py
  test_task.py
  test_observation.py
  test_project_context.py
  test_conversation.py
  test_specification.py
  test_planning.py
  test_semantic.py
  test_semantic_runtime.py
pyproject.toml
PROJECT.md
TODO.md
AGENTS.md
.gitignore
```

adapters、policy、verification、reporter 仍只含空的 `.gitkeep`，没有业务实现。`pyproject.toml` 声明项目元数据及可选打包所需的 setuptools；源码运行和测试均只使用标准库。

项目定位与边界见 [PROJECT.md](PROJECT.md)，后续阶段见 [TODO.md](TODO.md)。
