# 项目定位

- 中文名称：土老板。
- English：Mr.Moneybags。
- AI Secretary：小江 / JIA（Jiang Intelligent Assistant）。
- 类型：个人 Agent Harness。
- 核心关系：土老板负责目标，小江负责管理，Agent 负责执行。

## 当前阶段

Phase 0 只建立干净、可运行、可测试、适合长期迭代的 Python 工程骨架，不实现完整产品。

采用 Python 3.11+、标准库命令行入口和 unittest。选择普通 Python 包布局，直接在根目录运行；不引入应用框架或运行依赖。五个模块仅预留位置，职责和接口待后续阶段明确。

## 核心原则

- Keep it simple.
- One task → One verification → One checkpoint.
- 目标由用户决定，管理与执行职责保持清晰。
- 每次变更保持小范围、可运行、可验证。
- 不为假设中的未来需求增加依赖、抽象或假实现。
- 不提交 API Key、Token、Password 或其他 Secret。
- 外部操作必须有明确授权；不自动执行生产环境操作。

## Phase 0 边界

不实现 Multi-Agent、A2A、MCP 集成、RAG、Vector Database、Cloud Deployment、完整 Web UI、复杂 Memory System、自动化生产环境操作或大规模框架设计。不提前实现 Phase 1 及之后的功能。

## 验收与检查点

运行程序、运行测试、检查 Git 状态及差异，并检查意外敏感内容。验证失败必须先修复并重新验证。全部通过后只创建一次本地 Git commit，不 push，停止 Phase 0。
