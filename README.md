# 土老板 / Mr.Moneybags

个人 Agent Harness 项目。AI Secretary 为小江 / JIA（Jiang Intelligent Assistant）。

**土老板负责目标，小江负责管理，Agent 负责执行。**

当前为 Phase 2A：JIA 接收一条自然语言任务，按明确规则创建结构化 Task，随后只读观察当前工作区，分别展示 JSON 后退出。不调用 LLM、Codex 或其他 Agent，不执行任务、不保存任务、不操作生产环境。

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
- 扫描只读取目录项和文件元信息，不打开文件内容，不解释 README/PROJECT，不修改工作区。多个观察步骤不是原子快照，不保证扫描期间并发改动的一致性；本阶段不实现 Staleness 或 Derived Context。

## 测试

```powershell
python -m unittest discover -s tests -v
```

测试保留 Task 与 CLI 生命周期验证，并在隔离临时目录中覆盖 Git 仓库、无提交、非仓库、干净与脏状态、无 Git、超时、过滤与扫描边界，以及观察前后文件和 Git 索引不变。Git fixtures 只在临时目录创建仓库与提交，不依赖当前项目仓库或用户的提交身份；需要本机安装 Git，无 Git 时相关真实仓库测试会跳过，异常路径测试仍可运行。

## 目录

```text
mr_moneybags/
  __init__.py
  __main__.py
  cli.py          # 单次输入与 JSON 展示
  task.py         # 独立 Task 数据模型
  observation.py  # 只读工作区直接证据
  adapters/       # Agent Adapter，预留
  context/        # Context Engine，预留
  policy/         # Policy，预留
  verification/   # Evaluator / Verification，预留
  reporter/       # Reporter，预留
tests/
  test_startup.py
  test_task.py
  test_observation.py
pyproject.toml
PROJECT.md
TODO.md
AGENTS.md
.gitignore
```

预留目录仅含空的 `.gitkeep`，没有业务实现。`pyproject.toml` 声明项目元数据及可选打包所需的 setuptools；源码运行和测试均只使用标准库。

项目定位与边界见 [PROJECT.md](PROJECT.md)，后续阶段见 [TODO.md](TODO.md)。
