# Intent Evolution and Alignment Loop

## Document Status

- Scope: intent evolution and alignment design
- Position: JIA Intent Alignment Harness
- Related models: Alignment Model v6.1, Decision Context Model, Horizon Layer Design, Alignment Layer Design
- Current implementation: existing semantic, evidence, readiness, router, planning and reporting boundaries
- Future direction: controlled intent evolution across project stages

本文档定义用户意图在复杂项目中的受控演化模型。它只记录设计，不修改当前运行逻辑，也不实现相关功能。

# 1. Problem Statement

传统 Agent 协作存在两个问题。

## 意图漂移

用户最初目标是 A，执行过程中 Agent 逐渐转向 B，最后完成的不是用户想要的结果。变化可能发生在范围、阶段重点或实现方向中，但没有被显式识别和重新对齐。

## 意图僵化

系统强行保持最初目标，忽略用户经过探索、原型反馈、技术限制或新认知后产生的更好方向。

因此，JIA 需要支持 Controlled Intent Evolution：既不让目标在执行中无意漂移，也不冻结已经被用户重新认识和确认的目标。

# 2. Core Principle

JIA 不负责保存固定目标，也不替用户决定目标应该如何变化。JIA 负责让目标变化被识别、解释和确认。

核心原则是：

> Intent Evolution + Alignment

每次重要变化都应说明变化内容、影响范围和变化原因，并在进入下一阶段前重新确认。未确认的建议仍是开放问题，不应被当作新的用户意图。

# 3. Alignment Loop

JIA 的循环过程为：

```text
Human Intent
↓
Horizon
↓
Decision Context
↓
Execution
↓
Feedback
↓
Intent Update
↓
Horizon Revision
```

这是循环过程，而不是一次完成的单向流程。Horizon 提供长期方向，Decision Context 表示当前决策状态；执行和反馈可能带来新的认知，经过确认后才更新意图和 Horizon。

当前实现覆盖意图解释、证据约束、就绪判断、任务准备和报告基础；反馈驱动的跨阶段 Intent Update 与 Horizon Revision 尚未实现。

# 4. Intent Change Types

意图变化至少分为三类。变化类型决定需要的 Checkpoint 程度，但不自动决定是否接受变化。

## Refinement

目标细化，长期方向保持不变。

示例：

```text
AI学习软件
↓
AI课程资料整理助手
```

通常需要确认新目标的表达和当前范围是否足够明确。

## Expansion

在已有方向上扩大范围。

示例：

```text
增加考试复习功能
```

需要检查新增范围是否影响当前阶段、资源和已确认边界。

## Direction Change

项目方向发生改变。

示例：

```text
从资料整理转向AI答疑
```

需要较强的 Checkpoint，确认旧方向是否仍然有效、Horizon 是否需要更新，以及当前工作是否需要重新定义。

# 5. Alignment Checkpoint Role

Checkpoint 不是审批，也不是阻止变化。它是关键阶段的重新确认点。

Checkpoint 用于确认：

- 变化是否被正确理解。
- 变化是否影响 Horizon。
- 是否需要更新或重置 Decision Context。

Checkpoint 保留用户对方向的决定权。它可以暴露冲突、影响和开放问题，但不把 JIA 的建议伪装成用户确认，也不自动授予执行权限。

# 6. Horizon Update Model

Horizon 更新不是覆盖历史，而是维护当前有效方向。旧方向和新方向的关系、变化原因和确认来源应保持可追踪。

示例：

```text
旧目标：AI学习助手
新目标：AI课程资料整理助手
变化原因：经过用户探索确认
```

新方向成为当前有效 Horizon，旧方向作为变化背景保留。未经确认的候选方向不能直接替换当前 Horizon。

# 7. Decision Context Relationship

Horizon 负责长期方向变化，Decision Context 负责当前阶段决策。

关系为：

```text
Horizon change
↓
Decision Context reset/update
```

Horizon 变化可能使当前阶段、范围、开放问题或下一步行动失效，因此 Decision Context 需要被更新或重置。反过来，单次当前决策变化不必然改变 Horizon。

# 8. Difference From Memory

Memory 记录过去信息；Intent Evolution 记录重要决策变化。

JIA 不需要保存所有对话，只需要保留支持当前对齐的变化摘要：

- 关键目标变化。
- 重要决策变化。
- 变化原因。

这些记录服务于下一次 Alignment Decision，不构成无限历史系统，也不要求保存与决策无关的聊天内容。

# 9. Example

以 AI 大学生学习软件为例：

1. 初始方向：Horizon 为“AI 辅助学习”。
2. 探索阶段：发现课程资料整理是主要痛点。
3. 更新方向：Horizon 收敛为“AI 课程资料助手”。
4. 开发之后：反馈显示用户还需要考试复习。
5. 触发 Alignment Checkpoint：检查考试复习是否属于当前方向，是否会改变当前阶段和范围。
6. 用户确认：决定是否扩展方向。

只有第 6 步完成确认后，Expansion 才能进入新的 Decision Context；在此之前，考试复习只是开放的变化候选。

# 10. Non Goals

JIA 不做：

- 自动预测用户需求。
- 自动决定方向变化。
- 无限历史记录。
- 自动产品战略。

JIA 也不替代 Codex、产品决策者或项目执行系统，不因支持 Intent Evolution 而变成 Long Memory 或 Autonomous Planner。

# 11. Future Implementation

未来可能增加：

- Intent Change Detector。
- Alignment Checkpoint Engine。
- Horizon Update Logic。

这些属于 Future Direction。当前只定义模型，不实现变化检测、Checkpoint 执行、Horizon 持久化或 Decision Context 自动更新。
