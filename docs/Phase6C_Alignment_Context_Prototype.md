# Phase 6C Alignment Context Prototype

## Document Status

- Scope: prototype design and validation plan
- Current implementation: Semantic Interpreter, Evidence Contract, Readiness Gate, Router and Reporter
- Design inputs: Decision Context Model and Alignment Layer Design
- Implementation status: prototype not implemented; Phase 6 development has not started

本文档设计一个最小 Alignment Context Prototype，用于验证 Decision Context 是否能够提升 Human-Agent 协作质量。它只记录设计，不修改当前运行逻辑或创建实现代码。

Alignment Context 不是 Long Memory、Project Database、Autonomous Planner 或 Task Generator，而是当前项目关键决策状态的结构化表示。

# 1. Prototype Goal

Prototype 的目标是验证：Decision Context 是否能够在 Semantic Interpretation 和 Codex Brief 之间提供有效的决策对齐层。

Prototype 不验证：

- 自动开发能力。
- 自动规划整个项目。
- 长期记忆能力。

验证重点是目标、范围、关键未知因素和下一步行动是否更清晰，而不是增加模型生成内容的数量。

# 2. Architecture Position

当前流程：

```text
User
↓
Semantic Interpreter
↓
Codex Brief
```

未来 Prototype 流程：

```text
User
↓
Semantic Interpreter
↓
Alignment Context Builder
↓
Decision Context
↓
Specification
↓
Codex Brief
```

Prototype 不替代已有 Semantic Interpreter，而是在其后增加决策层。Semantic Interpreter 继续负责理解用户表达和提供证据，Alignment Context Builder 只负责把已验证信息整理成当前决策状态。

# 3. Decision Context v0.1 Schema

v0.1 定义以下最小字段：

## goal

当前目标。

## scope_in

明确包含在当前目标中的内容。

## scope_out

明确排除或暂不处理的内容。

## confirmed_decisions

已经确认的决策。

## open_decisions

尚未解决但会影响推进的问题。

## stage

当前阶段。

## next_action

当前最有价值的下一步行动。

v0.1 不包含：

- Memory。
- History Timeline。
- Autonomous Plan。

字段应保留未知和开放状态，不用默认值伪造用户确认或项目进度。

# 4. Data Source Strategy

Prototype 比较两种 Decision Context 数据来源。

## 方案 A：Model Generated Decision Context

优点：

- 灵活。

缺点：

- 需要大量验证。
- 可能把推断、假设或未确认方向写成决策状态。

## 方案 B：Deterministic Builder

来源：

- Semantic Result
- Rules

优点：

- 可靠。
- 可测试。

缺点：

- 覆盖范围有限。
- 复杂项目状态需要更多显式规则和输入。

第一版推荐 Deterministic Builder 优先。JIA 的核心是可靠 Harness，而不是增强模型自由生成；先用可追踪、可复现的来源验证 Decision Context 的价值，再评估是否需要模型辅助。

# 5. Relationship With Existing Modules

- Semantic Interpreter：提供用户意图和 claims。
- Readiness：提供是否具备推进条件的判断。
- Router：读取 stage 和状态，选择交互路径。
- Reporter：展示 Decision Context。
- Evidence Contract：继续保证输入来源可靠。

Prototype 应复用这些模块的结果，不改变它们的职责。Decision Context Builder 不能绕过 Evidence Contract、Readiness 或 Router，也不能把 Reporter 的展示结果当作新的用户决策。

# 6. Example

场景：课程管理系统增加作业功能。

用户输入：

> 老师创建作业，学生查看。提交和评分以后再考虑。

理想 Decision Context：

```yaml
goal: 增加课程作业功能
scope_in:
  - 老师创建作业
  - 学生查看作业
scope_out:
  - 提交
  - 评分
confirmed_decisions: []
open_decisions:
  - 是否需要草稿/发布状态
stage: FEATURE_DEFINITION
next_action: 确认发布流程
```

该输出区分当前范围、未来考虑和仍待确认的发布流程。它是验证用的目标形态，不代表当前运行时已经能够自动生成该对象。

# 7. Implementation Boundary

如果 Prototype 获得批准，第一阶段只实现：

- 数据模型。
- 构建逻辑。
- 测试。

第一阶段不实现：

- 自动规划。
- Agent Memory。
- 多轮项目管理。
- 全自动决策。

任何实现都应保持现有 Semantic、Specification、Planning、Router 和 Reporter 行为可比较、可回退。本文档本身不实现上述内容，也不启动 Phase 6。

# 8. Validation Plan

比较两条路径：

```text
Current:   Semantic → Brief
Prototype:  Semantic → Decision Context → Brief
```

在相同输入、项目基线和 Codex 条件下观察：

- 是否更准确表达范围。
- 是否减少遗漏关键决策。
- 是否提高后续 Codex 任务质量。

验证应记录可观察的范围偏差、未决问题处理和返工情况。单次示例、字段齐全或输出更长不足以证明 Prototype 有效；Prototype 也不能把 Codex 的代码能力变化直接归因于 Decision Context。

# 9. Future Evolution

Prototype 验证后，可能继续探索：

- Alignment Check。
- Stage Transition。
- Decision History。

这些属于 Future Direction，不属于 v0.1 Prototype。它们的设计应由验证中发现的具体问题驱动，不预先引入 Long Memory、Autonomous Planner 或完整项目管理能力。
