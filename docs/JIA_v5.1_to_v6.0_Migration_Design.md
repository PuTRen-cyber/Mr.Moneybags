# JIA v5.1 → v6.0 Migration Design

## Document Status

- Scope: product positioning and roadmap design
- Current implementation baseline: v5.1 Human-to-Agent Orchestration
- Target positioning: v6.0 Human-to-Agent Alignment Harness
- Implementation status: Phase 6 has not started

v6.0 不推翻 v5.1。它在已有 Human-to-Agent Orchestration 基础上，将 Alignment Harness 明确为核心定位。本文档描述定位演进和未来方向，不修改当前运行逻辑，也不表示相关未来模块已经实现。

# 1. Migration Purpose

v5.1 已建立以下基础：

- Intent Understanding
- Alignment
- Readiness
- Rolling Horizon
- Agent Task Package
- Verification
- Reporting

这些能力形成了从人类目标到 Agent 任务准备的基本结构。v6.0 的目标是在此基础上进一步明确：JIA 是 Human-Agent Alignment Harness。

本次迁移是定位校准，不是架构重写。已有语义理解、证据、就绪判断、规划、验证和报告边界继续保留。

# 2. Positioning Evolution

v5.1 定位：

> Human-to-Agent Orchestrator

v6.0 定位：

> Human-to-Agent Alignment Harness

Orchestration 是能力表现，Alignment 是核心机制。任务整理、路径选择和工作包交付体现了 orchestration；这些行为的共同目的，是让 Human Intent、Project Reality 和 Agent Execution 保持一致。

# 3. Preserved Principles

## Human Understanding

用户一句话不是 Specification，而是 Goal Draft。JIA 需要保留原始表达，区分目标、约束、范围、未知因素和待确认决策，再判断是否可以进入任务准备。

## Alignment Threshold

JIA 只在关键、不易逆转、影响结果的决策点进行对齐。普通实现细节由 Coding Agent 判断，避免对用户进行无必要的重复确认。

## Rolling Horizon

JIA 避免：

- 一次生成完整项目蓝图。
- 只进行局部贪心执行。

JIA 采用长期方向与当前决策相结合的方式。长期方向用于保持连续性，当前决策用于形成可执行、可验证的下一步。

# 4. Alignment Loop

JIA 的核心循环定义为：

```text
Human Intent
↓
Understanding
↓
Alignment
↓
Current Decision
↓
Agent Execution
↓
Verification
↓
Reality Feedback
↓
Intent Update
```

JIA 的价值不是生成更长 Prompt，而是维护 Human Intent、Project Reality 和 Agent Execution 一致。

当前实现覆盖循环中的意图理解、证据约束、就绪判断、任务准备和结果展示基础。持续执行、现实反馈和完整意图更新闭环仍属于后续方向。

# 5. Navigation Layer Direction

Navigation Layer 不是自动规划器。它的目标是在信息不完整、方向可能变化的项目中提供持续导航能力。

## Horizon Layer

维护：

- Goal
- Exploration Hypotheses
- Unknowns

Horizon 提供长期方向和待验证问题，不生成详细完整路线图。

## State Layer

维护：

- 当前项目阶段
- 当前状态

State 描述当前所处位置，不自动宣称阶段完成。

## Decision Layer

维护：

- 下一步最有价值行动
- 决策原因

Decision 选择当前行动，不替用户决定产品方向。

Horizon、State 和 Decision 都属于 Future Direction，不代表当前已经实现。

# 6. JIA and Codex Responsibility Boundary

JIA 负责 Why、What、When、Whether，包括：

- 为什么做。
- 做什么范围。
- 是否应该执行。
- 下一步是什么。

Codex 负责 How，包括：

- 技术实现。
- 代码修改。
- 测试。
- 调试。

JIA 负责形成清晰且有边界的行动方向。Codex 在该边界内完成工程工作。JIA 的任务准备结果不等于执行授权。

# 7. Roadmap Adjustment

原方向：

> Phase 6: Codex Integration

调整方向：

> Phase 6: Alignment Navigation Core
>
> Phase 7: Codex Managed Integration

调整原因：没有 Navigation 时，Codex Integration 主要是任务传递；建立 Navigation 后，系统才具备围绕目标、状态、决策、执行结果和现实反馈形成持续协作闭环的基础。

该调整是 v6.0 路线图方向，不表示 Phase 6 或 Phase 7 已经实现或开始开发。

# 8. Non Goals

JIA 不做：

- 自动生成完整项目路线图。
- 自动替用户决定产品方向。
- 替代 Coding Agent。
- 成为复杂 PM 系统。
- 成为另一个 Agent。

# 9. Core Statement

中文：

> 小江不是帮用户写更长的指令，而是在强大 Agent 时代帮助人类持续对齐目标、阶段和行动路径。

English:

> JIA is not a better prompt generator. JIA is an alignment layer that helps humans continuously navigate complex projects with powerful agents.
