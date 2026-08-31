# 土老板 / Mr.Moneybags

个人 Agent Harness 项目。AI Secretary 为小江 / JIA（Jiang Intelligent Assistant）。

**土老板负责目标，小江负责管理，Agent 负责执行。**

当前为 Phase 2B：JIA 接收一条自然语言任务，创建 Task，观察当前工作区，再依据少量项目证据生成可追溯的 Project Context。三个部分分别展示 JSON 后退出。不调用 LLM、Codex 或其他 Agent，不执行任务或文档命令、不持久化、不解释用户意图。

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

Observed Evidence 是观察到的证据；Derived Context 是规则产生的解释；User Intent 不在 Phase 2B 范围内。

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

## 测试

```powershell
python -m unittest discover -s tests -v
```

测试保留 Task 与 CLI 生命周期验证，并在隔离临时目录中覆盖 Git 仓库、无提交、非仓库、干净与脏状态、无 Git、超时、过滤与扫描边界，以及观察前后文件和 Git 索引不变。Git fixtures 只在临时目录创建仓库与提交，不依赖当前项目仓库或用户的提交身份；需要本机安装 Git，无 Git 时相关真实仓库测试会跳过，异常路径测试仍可运行。

Context 测试覆盖规则与来源、冲突、缺失文件、模型分离、文件数量及字节预算、敏感/二进制过滤、链接和文件替换、无写入与不执行命令。

## 目录

```text
mr_moneybags/
  __init__.py
  __main__.py
  cli.py          # 单次输入与 JSON 展示
  task.py         # 独立 Task 数据模型
  observation.py  # 只读工作区直接证据
  adapters/       # Agent Adapter，预留
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
pyproject.toml
PROJECT.md
TODO.md
AGENTS.md
.gitignore
```

adapters、policy、verification、reporter 仍只含空的 `.gitkeep`，没有业务实现。`pyproject.toml` 声明项目元数据及可选打包所需的 setuptools；源码运行和测试均只使用标准库。

项目定位与边界见 [PROJECT.md](PROJECT.md)，后续阶段见 [TODO.md](TODO.md)。
