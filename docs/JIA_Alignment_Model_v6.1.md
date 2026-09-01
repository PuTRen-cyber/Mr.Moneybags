# JIA Alignment Model v6.1

## Document Status

- Scope: positioning and design model calibration
- Baseline: JIA v6.0 Human-to-Agent Alignment Harness
- Evidence: Phase 6A Case A experiment insight
- Implementation status: Phase 6 functionality has not started

本文档根据 Phase 6A Case A 的实验结果校准 JIA 定位。它记录设计方向，不修改当前运行逻辑，也不代表未来数据对象或模块已经实现。

JIA 不应定位为 Long Memory 系统、Prompt Generator、Coding Agent 替代品或 AI Project Manager。JIA 应定位为 Intent Alignment Harness：在人类与 Agent 协作过程中，通过阶段化理解、关键决策检查和持续对齐，降低 Human Intent 与 Agent Action 之间的偏差。

# 1. Core Problem Reframing

JIA 解决的问题不是“Agent 不会理解用户一句话”。强 Agent 已经具备：

- Discovery
- Question Asking
- Solution Exploration

JIA 解决的是复杂项目推进过程中的对齐问题：

- 用户目标逐渐变化。
- 阶段目标不清晰。
- 决策未经确认。
- Agent 行动可能偏离真实意图。

结果可能是项目完成了任务，但没有得到用户真正想要的结果。JIA 的作用是让目标变化、阶段判断和关键决策在继续行动前保持可见、可检查和可重新对齐。

# 2. JIA vs Memory

Memory、Context 和 JIA Alignment 的职责不同：

| 概念 | 目标 |
| --- | --- |
| Memory | 保存过去的信息 |
| Context | 提供当前已知信息 |
| JIA Alignment | 辅助判断当前决策是否符合目标 |

JIA 可能需要有限状态记忆，包括当前阶段、已确认决策、未解决问题和下一步行动。但这些信息的目的不是建立长期记忆，而是支持更好的 Alignment Decision。

当前实现保留有限的任务、意图、证据、就绪状态和规划快照；它们不是 Long Memory 系统。更完整的 Decision Context 属于 Future Direction。

# 3. Core Alignment Loop

JIA 的核心循环重新定义为：

```text
Human Idea
↓
Discovery（需求获取）
↓
Intent Alignment（目标确认）
↓
Stage Decision（阶段判断）
↓
Codex Execution
↓
Verification
↓
Next Alignment
```

JIA 的价值不是生成更长 Prompt，而是保证项目推进过程中的关键决策保持一致。当前实现覆盖其中的意图理解、证据约束、就绪判断、任务路由、任务准备和报告基础；完整的跨阶段循环仍属于 Future Direction。

# 4. Decision Context

未来方向中的核心数据对象可以抽象为 Decision Context：

```json
{
  "current_goal": "构建课程资料AI助手",
  "stage": "MVP_DEFINITION",
  "confirmed_decisions": [
    "目标用户为大学生"
  ],
  "open_questions": [
    "是否需要移动端"
  ],
  "next_decision": "确定第一版功能"
}
```

Decision Context 不等于 Memory。它服务于下一次正确决策：把当前目标、阶段、已经确认的边界、仍然开放的问题和待作出的决定放在同一个决策上下文中。它不要求保存所有历史，也不自动替用户作出产品选择。

Decision Context 当前尚未作为完整运行时对象实现。

# 5. JIA Responsibility Boundary

JIA 负责 Why、What、Whether、When：

- Why：为什么做。
- What：做什么范围。
- Whether：是否应该执行。
- When：什么时候推进下一步。

Codex 负责 How：

- 技术方案。
- 代码。
- 测试。
- 调试。

JIA 提供经过对齐的方向和边界，Codex 在这些边界内进行工程实现。JIA 的协调结果不等于执行授权，也不替代 Codex 的技术判断。

# 6. Phase 6 Direction Adjustment

原方向：

> Phase 6 Navigation Core

调整方向：

> Phase 6 Alignment Context Core

重点是：

- Decision Context
- Stage Awareness
- Alignment Check

该方向不是 Long Memory，不是自动规划器，也不是 PM 系统。调整只记录设计重点，相关能力当前尚未实现，不启动 Phase 6 开发。

# 7. Case A Experiment Insight

Case A 表明，直接使用 Codex 已经能够：

- 识别模糊需求。
- 主动询问方向。

因此，JIA 不与模型能力竞争。JIA 关注把正确行为变成稳定、可验证、跨阶段的协作机制：明确什么时候需要对齐、哪些决策已经确认、哪些问题仍开放，以及下一步行动是否仍服务于目标。

该结论是对实验行为的定位判断，不宣称已证明 JIA 在所有项目或模型上都能改善结果。

# 8. Non Goals

JIA 不做：

- 替代 Codex。
- 存储所有历史。
- 自动决定产品方向。
- 自动生成完整项目蓝图。
- 管理所有项目任务。

# 9. Core Statement

中文：

> 小江不是帮用户写更长的指令，而是在强大 Agent 时代帮助人类持续对齐目标、阶段和行动路径。

English:

> JIA is an Intent Alignment Harness that helps humans continuously align goals, decisions, and actions while working with powerful agents.
