# Decision Context Model

## Document Status

- Scope: conceptual model definition
- Position: JIA Intent Alignment Harness
- Current implementation: documentation only
- Future implementation: Decision Context extraction and lifecycle

本文档定义 JIA v6.0 中 Decision Context 的概念。它描述支持项目推进和关键决策对齐的当前决策状态，不修改现有运行逻辑，也不启动 Phase 6 功能开发。

Decision Context 不是 Long Memory、Chat History、Project Management Database 或 Autonomous Planner。

# 1. Problem Statement

当前强 Agent 已经具备：

- 需求理解。
- 问题澄清。
- 方案探索。

但复杂项目中仍存在：

- 用户真实目标未显式表达。
- 范围边界未确认。
- 关键决策未记录。
- 执行动作与原始意图偏离。

JIA 的目标是在 Agent 执行前和执行过程中，让关键决策显式化，使目标、边界、阶段和下一步行动能够被检查并重新对齐。

# 2. Decision Context Definition

Decision Context 是：

> A structured representation of current project decision state.

它描述当前决策所需的最小状态，而不是保存所有对话或项目历史。

## Goal

当前希望达成的目标。

## Scope In

明确包含在当前目标中的内容。

## Scope Out

明确暂不包含在当前目标中的内容。

## Confirmed Decisions

已经经过用户或明确授权流程确认的决定。

## Open Decisions

尚未确定但会影响项目推进的问题。

## Current Stage

当前项目阶段，例如问题澄清、功能定义或实现准备。

## Next Action

在当前状态下最有价值的下一步行动。

# 3. Example

场景：课程管理系统增加作业功能。

用户输入：

> 老师创建作业，学生查看，提交评分以后考虑。

理想 Decision Context：

```json
{
  "goal": "增加课程作业管理功能",
  "scope_in": [
    "老师创建作业",
    "学生查看作业"
  ],
  "scope_out": [
    "学生提交作业",
    "作业评分"
  ],
  "confirmed_decisions": [],
  "open_decisions": [
    "是否需要草稿/发布状态"
  ],
  "stage": "FEATURE_DEFINITION",
  "next_action": "确认发布流程"
}
```

该示例保留当前范围和未来考虑的区别。它不替用户决定发布流程，也不代表这些字段已经由当前运行时自动生成。

# 4. Difference From Memory

| 概念 | 作用 |
| --- | --- |
| Memory | 保存过去的信息 |
| Decision Context | 描述当前决策状态 |

Memory 可以支持 Decision Context，例如提供先前确认的事实；但 Memory 不是 JIA 的核心。Decision Context 只保留对下一次对齐和行动有用的当前状态，不要求存储完整历史。

# 5. Difference From Task Specification

Task Specification 描述执行什么；Decision Context 描述为什么现在执行，以及执行边界。

两者关系：

```text
Decision Context
↓
Task Specification
↓
Codex Brief
```

Decision Context 为任务规格提供目标、范围、阶段和决策依据。Task Specification 再将这些边界整理为可执行内容。当前实现中的两者仍保持独立，本文档不改变既有规格或简报模型。

# 6. Relationship With Existing Modules

- Semantic Interpreter：负责理解输入。
- Readiness：负责判断是否具备推进条件。
- Router：负责选择路径。
- Decision Context：负责保存当前决策状态。
- Reporter：负责向用户展示状态。

在当前实现中，Semantic、Readiness、Router 和 Reporter 已有明确边界；Decision Context 目前是设计对象，不是完整运行时模块。

# 7. Non Goals

Decision Context 不实现：

- 自动规划整个项目。
- 自动替用户决策。
- 完整项目管理。
- 长期记忆系统。

# 8. Future Implementation Direction

未来可能增加：

- Decision Context extraction。
- Alignment Check。
- Stage Transition。

这些属于 Future Direction。当前阶段只完成模型定义，不实现提取、状态持久化、自动对齐检查或阶段转换。
