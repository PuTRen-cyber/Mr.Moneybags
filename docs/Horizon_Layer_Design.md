# Horizon Layer Design

## Document Status

- Scope: long-term direction model design
- Position: JIA Intent Alignment Harness
- Current implementation: no Horizon Layer
- Future direction: Horizon Layer alongside Decision Context

本文档补充 JIA v6.0 定位调整后的双层决策结构。JIA 不负责替用户创造项目方向，而是假设用户拥有初始意图，帮助用户逐步明确方向。本文档只定义模型，不修改当前运行逻辑或实现 Horizon Layer。

核心模型：

```text
Horizon Layer       → 维护长期方向和目标空间
Decision Context    → 维护当前阶段决策状态
```

# 1. Motivation

复杂项目中存在两个风险。

第一，一次性生成完整蓝图会引入过多假设，并把尚未确认的决策提前固化。

第二，只优化当前一步会形成局部最优，并逐渐失去整体方向。

双层结构用于平衡方向稳定性与执行灵活性：Horizon 保持项目方向，Decision Context 随当前阶段变化。两者共同降低 Big Design Up Front 和 Local Optimization 的风险。

# 2. Horizon Layer Definition

Horizon Layer 是 JIA 用于表示项目长期方向、目标空间和关键未知的抽象层。

Horizon 不是：

- Roadmap。
- Task List。
- Project Management。
- Full Plan。

它不承诺完整路线、不列出所有任务，也不替用户决定最终产品方向。Horizon 只保留足以指导后续探索和对齐的方向信息。

# 3. Horizon Layer Responsibilities

Horizon Layer 负责：

- 当前目标方向。
- 可能探索方向。
- 已确认方向。
- 核心未知问题。

Horizon Layer 不负责：

- 技术实现。
- 具体任务拆解。
- 自动规划。

方向信息应区分已确认内容、探索中的可能性和仍未知的问题，不能把假设伪装成用户决定。

# 4. Decision Context Relationship

Horizon 回答：

> 为什么以及往哪里？

Decision Context 回答：

> 当前阶段如何推进？

两者关系为：

```text
Horizon
↓
Decision Context
↓
Execution
```

Horizon 提供长期方向和目标空间；Decision Context 在该方向内维护当前阶段、范围、已确认决定、开放问题和下一步行动。Decision Context 不应扩大 Horizon，也不应脱离 Horizon 形成无关的局部目标。

# 5. Two-Level Model

## Level 1：Horizon

Horizon 低频变化，用于保持方向。只有当用户目标、已确认方向或核心问题发生实质变化时，才需要更新它。

## Level 2：Decision Context

Decision Context 高频变化，用于支持当前决策。阶段推进、范围确认、问题解决和下一步选择都可以更新当前状态，而不必改变长期方向。

两层共同避免：

- Big Design Up Front：不提前固化完整蓝图。
- Local Optimization：不为了当前一步而丢失整体方向。

该模型要求方向和行动分离，但不要求预先生成完整计划。

# 6. Example

初始案例：AI 帮助大学生学习软件。

初始 Horizon：

```json
{
  "goal": "探索AI辅助大学生学习方向",
  "possible_directions": [
    "课程资料整理",
    "AI答疑",
    "学习规划"
  ],
  "unknowns": [
    "目标用户",
    "核心痛点"
  ]
}
```

此时 Horizon 表示方向空间，不生成具体实现任务。

经过用户确认后，Horizon 可以收敛为：

```json
{
  "goal": "帮助大学生整理课程资料"
}
```

然后在该方向内形成当前 Decision Context：

```json
{
  "stage": "MVP_DEFINITION",
  "next_action": "确定第一版功能"
}
```

示例中的收敛来自用户确认，不来自 JIA 自动选择。Decision Context 负责下一步，Horizon 继续提供方向边界。

# 7. Relationship With Codex

Horizon 不限制 Codex 的技术探索。Codex 可以提出多个实现方案，并在工程层面比较取舍；这些方案必须符合当前 Horizon 及已确认的 Decision Context 边界。

Codex 负责如何实现，Horizon 负责提供方向约束。技术方案的数量不等于产品方向的数量，Codex 不能通过实现选择替用户改变 Horizon。

# 8. Implementation Direction

未来可能新增：

```text
mr_moneybags/horizon/
├── models.py
└── state.py
```

可能的职责是定义 Horizon 数据模型及其状态变化。当前只定义模型方向，不创建目录、不实现接口、不接入运行时，也不改变 Decision Context、Specification 或 Codex Brief。

# 9. Non Goals

Horizon 不做：

- 自动生成完整项目蓝图。
- 自动制定半年计划。
- 替用户决定方向。
- 替代产品经理。

Horizon 也不是 Long Memory、Task List 或 Autonomous Planner。它只为持续对齐提供长期方向和未知问题的最小表示。
