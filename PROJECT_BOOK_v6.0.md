# Mr.Moneybags · JIA Project Book v6.0

## 文档状态

- 项目：Mr.Moneybags / 土老板
- 协调层：JIA / 小江（Jiang Intelligent Assistant）
- 文档版本：v6.0
- 当前状态：Phase 6 尚未开始

本文档记录当前项目定位、已有可靠性基础和后续演进方向。Current Implementation 表示仓库中已经存在的能力；Future Direction 表示尚未实现的设计方向。

## 1. 项目定位

Mr.Moneybags · JIA 是 Personal Agent Alignment Harness。

JIA 不属于：

- Prompt 优化器。
- Coding Agent。
- 自动项目经理。
- Agent 替代品。

JIA 是人类意图与 Agent 执行之间的协调层。它负责降低目标表达、任务准备和 Agent 行动之间的偏差，不替代人类决策，也不承担具体工程实现。

## 2. 核心愿景变化

项目最初目标是成为最大化 Codex 潜能的放大器。实践表明，Agent 能力并不直接等于有效结果：当用户目标模糊、范围不稳定或当前阶段不清楚时，更强的执行能力也可能放大偏差。

因此，项目目标重新定义为：通过降低人类意图与 Agent 行动之间的偏差，实现能力放大。

Alignment 是 Amplification 的基础。JIA 先确保目标、边界和下一步行动能够对齐，再把明确任务交给 Agent 执行。

## 3. 核心问题

当前 Agent 协作常见问题包括：

- 用户目标模糊。
- 意图理解偏差。
- 项目范围漂移。
- 项目阶段判断困难。

JIA 处理的是 Human-Agent Alignment。它不通过替代 Agent 来解决这些问题，而是在执行之前建立可检查的意图、证据、就绪状态和交互路径。

## 4. Current Implementation：可靠性基础

当前实现包含以下模块：

- Semantic Interpreter：理解用户表达，并产生结构化语义结果。
- Evidence Contract：保证理解结果基于真实用户输入，保留可验证的原文证据。
- Readiness Gate：判断当前信息是否足以进入下一阶段。
- Safety Gate：检查任务边界并识别需要确认或阻止的风险；它不授予执行权限。
- Router：决定请求应进入快速任务、标准任务或探索路径。
- Reporter：把内部状态转换为面向用户和未来 Agent 的简洁结果。

这些模块构成 JIA 当前的可靠性基础。它们不代表完整的项目导航系统，也不提供 Coding Agent 执行能力。

## 5. Future Direction：Navigation Layer

未来 Navigation Layer 的目标不是自动生成完整项目计划，而是在不确定环境下持续推进项目。其设计方向包括：

- Horizon Layer：维护长期目标、探索假设和关键未知因素。它提供方向边界，不生成详细路线图。
- State Layer：维护当前项目阶段和与阶段相关的已知状态。
- Decision Layer：根据当前状态选择最有价值的下一步行动。

JIA 不追求一次性生成完整方案。目标是在保持长期方向的同时，通过连续、可检查的决策逐步推进。Horizon、State 和 Decision 当前尚未形成完整实现。

## 6. JIA 与 Codex 的职责边界

JIA 负责：

- 为什么做。
- 做什么范围。
- 当前是否应该行动。
- 下一步是什么。

Codex 负责：

- 如何实现。
- 代码修改。
- 工程执行。
- 测试和调试。

JIA 向 Codex 交付经过整理的目标和边界。Codex 在这些边界内做技术判断和工程实现。JIA 的协调结果不等于执行授权。

## 7. Non-Goals

JIA 不做：

- 自动生成巨大路线图。
- 自动替用户做产品决策。
- 自动开发完整项目。
- 替代 Coding Agent。

项目不以制造完整感为目标，也不通过提前加入未验证的规划、记忆或执行能力扩展范围。

## 8. Phase 6 方向

Phase 6 将探索 Alignment & Navigation Harness，重点方向包括：

- Alignment Loop。
- Horizon。
- State。
- Decision。

以上内容属于 Future Direction，当前尚未实现。本文档不启动 Phase 6 开发，也不构成对具体 Phase 6 架构或功能范围的实现承诺。
