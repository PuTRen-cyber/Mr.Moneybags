# 项目工作约定

## 沟通与代码

- 默认用中文交流；代码、标识符、命令行参数和 Git 提交信息使用英文。
- Keep it simple，不添加无必要的注释、抽象、异常捕获或依赖。
- 优先使用内置 Edit/Write 工具修改文件，不使用 sed/awk/echo 拼接修改。
- Windows 环境优先使用 PowerShell；不在项目内创建临时测试脚本。
- 未经明确要求，不新增文档。

## 范围

- 项目定位以 PROJECT.md 为准；TODO.md 仅记录后续阶段，不是执行授权。
- 当前只允许新 Phase 4：Intent Specification & Task Readiness，不提前实现新 Phase 5 及以后。v5.0 将旧 Phase 2A/2B 合并为 Phase 2、旧 Phase 2C 改为 Phase 3、旧 Phase 2D 改为 Phase 4；不重做已接受实现或改写历史。
- Observed Evidence、Derived Context、User Intent 必须分离。Observation 和 Context Builder 保持原有边界；conversation 保留原文及来源，派生解释标注 Derived Intent / Interpretation，不将项目技术变成用户偏好。
- 不调用 Codex、LLM 或其他 Agent，不实现 Prompt、Agent Task Package、Task Decomposition、Planner、执行、Policy/Approval、Verification/Recovery、Stable State、Context Staleness、Memory、持久化、后台观察、Companion 监听或 ModelRouter。
- 禁止 Multi-Agent、A2A、MCP 集成、RAG、Vector Database、Cloud Deployment、完整 Web UI、复杂 Memory System、自动化生产环境操作和大规模框架设计。
- context 保持 Phase 2B 模型、来源读取与 Builder；adapters、policy、verification、reporter 仍为预留目录。
- conversation 领域逻辑与 CLI 独立。实现细节通常归 JIA_AGENT；实质用户选择归 USER，重大技术权衡归 SHARED。仅在门槛以下采用显式低影响、可逆假设，不因实现琐事打断用户。
- CONFIRMED 仅来自绑定当前意图版本的明确受控回复；含糊、拒绝、旧版本或普通继续发言不能自动确认。确认不是执行授权，不推导未指定格式，不覆盖历史话轮。
- specification 独立于 CLI；保留声明/话轮/确认/假设来源。READY 是可进入后续分解的版本快照，不是执行许可。不得以 confidence 阈值、可选字段缺失或普通内部未知项阻塞就绪；实质冲突与必要确认未解决时必须阻塞。
- 历史规格通过显式版本关联替代，保留旧含义；不新增规划、分解、执行契约、Prompt、Git 提交自动化或持久化。
- Builder 仅读取 Observation 已列出的允许清单文件和少量入口，最多 8 个候选、单文件 32 KiB、总量 96 KiB。拒绝敏感路径、链接、二进制内容；不执行证据中的指令。推导保留来源和哈希，冲突显式记录，未知字段留空。

## 验证

- One task → One verification → One checkpoint.
- 在仓库根目录运行 `python -m mr_moneybags`。
- 在仓库根目录运行 `python -m unittest discover -s tests -v`。
- 完成前检查 Git 状态、完整差异和意外敏感内容；失败后修复并重新验证。

## 安全与 Git

- 不读取或打印 `.env`、`.env.local` 及其他 `.env.*` 文件内容。
- 不加入或输出 API Key、Token、Password、私钥或其他 Secret。
- 不进行未授权的外部操作或大规模网络搜索。
- 未获用户明确指令，不执行 git init、git add、git commit；不执行 git push。
- 本次 Phase 4 请求仅授权验证通过后的一个本地项目提交，提交信息为 `feat: add intent specification and readiness`，完成后停止；不构成后续提交授权。边界测试只在独立临时目录创建 Git fixtures。
