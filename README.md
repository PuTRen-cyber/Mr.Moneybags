# 土老板 / Mr.Moneybags

个人 Agent Harness 项目。AI Secretary 为小江 / JIA（Jiang Intelligent Assistant）。

**土老板负责目标，小江负责管理，Agent 负责执行。**

当前仅完成 Phase 0 工程骨架：命令行启动、基础测试和未来模块目录。程序只输出启动信息，不连接模型、不执行任务、不操作生产环境。

## 运行

需要 Python 3.11 或更高版本。在仓库根目录执行，无需安装第三方依赖：

```powershell
python -m mr_moneybags
```

预期输出：

```text
Mr.Moneybags | JIA | Phase 0: project skeleton ready.
```

## 测试

```powershell
python -m unittest discover -s tests -v
```

测试以独立进程启动真实入口，检查退出码、启动信息和标准错误。

## 目录

```text
mr_moneybags/
  __init__.py
  __main__.py
  adapters/       # Agent Adapter，预留
  context/        # Context Engine，预留
  policy/         # Policy，预留
  verification/   # Evaluator / Verification，预留
  reporter/       # Reporter，预留
tests/
  test_startup.py
pyproject.toml
PROJECT.md
TODO.md
AGENTS.md
.gitignore
```

预留目录仅含空的 `.gitkeep`，没有业务实现。`pyproject.toml` 声明项目元数据及可选打包所需的 setuptools；源码运行和测试均只使用标准库。

项目定位与边界见 [PROJECT.md](PROJECT.md)，后续阶段见 [TODO.md](TODO.md)。
