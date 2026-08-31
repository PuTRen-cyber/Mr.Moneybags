# 项目工作约定

## 沟通与代码

- 默认用中文交流；代码、标识符、命令行参数和 Git 提交信息使用英文。
- Keep it simple，不添加无必要的注释、抽象、异常捕获或依赖。
- 优先使用内置 Edit/Write 工具修改文件，不使用 sed/awk/echo 拼接修改。
- Windows 环境优先使用 PowerShell；不在项目内创建临时测试脚本。
- 未经明确要求，不新增文档。

## 范围

- 项目定位以 PROJECT.md 为准；TODO.md 仅记录后续阶段，不是执行授权。
- 当前只允许 Phase 0 骨架，不提前实现后续功能。
- 禁止 Multi-Agent、A2A、MCP 集成、RAG、Vector Database、Cloud Deployment、完整 Web UI、复杂 Memory System、自动化生产环境操作和大规模框架设计。
- adapters、context、policy、verification、reporter 仅预留目录，不编写假实现。

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
- 本次 Bootstrap 请求仅授权验证通过后的一个本地提交，完成后停止；不构成后续提交授权。
