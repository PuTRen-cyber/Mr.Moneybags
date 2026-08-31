# 土老板 / Mr.Moneybags

个人 Agent Harness 项目。AI Secretary 为小江 / JIA（Jiang Intelligent Assistant）。

**土老板负责目标，小江负责管理，Agent 负责执行。**

当前为 Phase 1：JIA 接收一条自然语言任务，按明确规则创建结构化 Task，以 JSON 展示后退出。不调用 LLM、Codex 或其他 Agent，不执行任务、不保存任务、不操作生产环境。

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

## 测试

```powershell
python -m unittest discover -s tests -v
```

测试覆盖 Task 创建、UUID4、初始状态、原始输入保留、待补充字段和空白输入；CLI 测试以独立进程传入文本，无需人工输入，并验证单次接收、JSON 输出及退出行为。

## 目录

```text
mr_moneybags/
  __init__.py
  __main__.py
  cli.py          # 单次输入与 JSON 展示
  task.py         # 独立 Task 数据模型
  adapters/       # Agent Adapter，预留
  context/        # Context Engine，预留
  policy/         # Policy，预留
  verification/   # Evaluator / Verification，预留
  reporter/       # Reporter，预留
tests/
  test_startup.py
  test_task.py
pyproject.toml
PROJECT.md
TODO.md
AGENTS.md
.gitignore
```

预留目录仅含空的 `.gitkeep`，没有业务实现。`pyproject.toml` 声明项目元数据及可选打包所需的 setuptools；源码运行和测试均只使用标准库。

项目定位与边界见 [PROJECT.md](PROJECT.md)，后续阶段见 [TODO.md](TODO.md)。
