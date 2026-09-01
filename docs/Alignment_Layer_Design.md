# Alignment Layer Design

## Document Status

- Scope: JIA v6.x architecture design
- Current implementation: Semantic, Evidence Contract, Readiness, Router and Reporter
- Future direction: Alignment Layer
- Implementation status: Alignment Layer has not been implemented

本文档定义 Alignment Layer 的职责和架构位置。它与 JIA Alignment Model v6.1 一致，只记录设计，不修改当前运行逻辑，也不实现 Alignment Layer。

# 1. Motivation

当前 Semantic Interpreter 解决的是用户表达理解：从用户输入中提取 intent、claims，并将它们映射到证据。

复杂项目还需要回答：

- 当前阶段是什么？
- 哪些决策已经确定？
- 哪些问题仍未解决？
- 下一步应该是什么？

这些问题属于项目推进中的决策协调，不应塞入 Semantic Interpreter。Phase 6B 的方向是引入 Alignment Layer，在 Human Intent 与 Agent Execution 之间提供明确的决策协调边界。

# 2. Responsibility Boundary

## Semantic Interpreter

Semantic Interpreter 负责：

> What did the user say?

包括：

- intent extraction
- claim extraction
- evidence mapping

它不负责决定项目下一步，也不负责替用户确认尚未确定的方向。

## Alignment Layer

Alignment Layer 负责：

> What should happen next?

包括：

- Decision Context construction
- Alignment check
- Stage awareness
- Next decision recommendation

Alignment Layer 应以已验证的语义和当前项目状态为输入，显式呈现决策依据和未解决问题，不把推荐伪装成用户决定。

## Codex

Codex 负责：

> How to implement?

包括技术实现、代码修改、工程执行、测试和调试。Codex 不承担 JIA 的目标对齐职责。

# 3. Architecture

目标架构为：

```text
User
↓
Semantic Interpreter
↓
Alignment Layer
↓
Decision Context
↓
Specification
↓
Codex Brief
```

Semantic Interpreter 产生对用户表达的结构化理解；Alignment Layer 根据该理解和当前状态形成决策上下文；Specification 和 Codex Brief 再把已对齐的范围整理为任务接口。

该流程是 Future Direction。当前运行时仍使用已有 Semantic、Readiness、Router、Specification、Planning 和 Reporter 边界，没有新增 Alignment Layer 调用链。

# 4. Decision Context Ownership

Alignment Layer 负责生成或更新 Decision Context 中与当前决策有关的字段：

- goal
- scope_in
- scope_out
- confirmed_decisions
- open_decisions
- stage
- next_action

这些字段描述当前项目决策状态。Alignment Layer 不拥有用户的最终产品决策权；confirmed_decisions 必须有明确来源，open_decisions 必须保持开放，next_action 是基于当前状态的建议而不是自动授权。

# 5. Relationship With Existing Modules

- Evidence Contract：保证输入可靠，使 Alignment Layer 不能脱离真实用户证据任意解释。
- Readiness：提供执行准备状态，帮助判断是否具备推进条件。
- Router：根据 Alignment 结果选择交互路径。
- Reporter：展示 Alignment 状态、边界和待决策事项。

当前这些模块已经各自保持边界。未来 Alignment Layer 应组合它们提供的信息，不替换 Semantic Interpreter 的证据职责，也不绕过 Readiness 或 Router。

# 6. Migration Strategy

Alignment Layer 不一次性重构现有流程，采用渐进迁移：

## Phase A：设计

明确 Alignment Layer、Decision Context、Alignment Check 和 Stage Awareness 的边界、输入和输出。当前文档属于此阶段。

## Phase B：新增旁路 Alignment Context

在不改变旧流程结果的前提下，新增旁路 Decision Context，用于观察和比较 Alignment 结果。旁路输出不得自动获得执行权限。

## Phase C：逐步接管决策生成

在旁路结果经过验证后，再让 Alignment Layer 逐步承担决策上下文和下一步建议的生成。每一步都应保持旧流程可回退，并通过既有测试和对照验证检查行为变化。

以上是 Future Direction，不是当前实施计划，也不授权开始 Phase 6 功能开发。

# 7. Non Goals

Alignment Layer 不包含：

- Long Memory
- Autonomous Planner
- PM System
- Multi Agent

它也不替代 Coding Agent，不负责执行代码，不自动生成完整项目路线图。

# 8. Future Implementation

未来可能新增以下模块：

```text
mr_moneybags/alignment/
├── models.py
├── context.py
└── checker.py
```

可能的职责分别是状态模型、Decision Context 构造和 Alignment 检查。当前只定义架构，不创建目录、不实现接口、不接入运行时。
