# JIA v6 Architecture Refactoring Plan

## Document Status

- Scope: architecture assessment and migration design
- Baseline: JIA v6.0 Intent Alignment Harness
- Related models: Alignment Model v6.1, Decision Context Model, Horizon Layer Design, Alignment Layer Design
- Current implementation: existing Semantic, Readiness, Router, Reporter and task preparation flow
- Implementation status: design only; refactoring has not started

本文档评估未来架构迁移，不修改代码、运行逻辑或现有测试，也不启动 Phase 6 开发。

核心目标结构为：

```text
Human Intent
↓
Horizon Layer
↓
Alignment Checkpoint
↓
Decision Context
↓
Specification
↓
Codex Execution
```

# 1. Current Architecture Analysis

当前主要流程可概括为：

```text
User
↓
Semantic
↓
Readiness
↓
Router
↓
Brief
```

已经稳定的职责包括：

- Semantic Interpreter 从用户表达中提取结构化意图，并使用 Evidence Contract 保留可验证来源。
- Readiness Gate 判断信息是否足以进入任务准备。
- Router 根据请求特征选择快速、标准或探索路径。
- Specification、Planning 和 Reporter 将已整理的目标转换为当前任务结果和用户可读输出。

未来可能迁移或扩展的职责包括：

- 长期方向和目标空间的维护，可能由 Horizon Layer 承担。
- 关键阶段的重新确认，可能由 Alignment Checkpoint 承担。
- 当前阶段、已确认决定、开放问题和下一步行动的组合，可能由 Decision Context 承担。
- 下一步决策和交互路径的选择，可能逐步由 Alignment Layer 协调。

这些迁移方向不改变当前模块已经承担的证据验证、任务规格和工程执行边界。

# 2. Target Architecture v6

目标架构为：

```text
User
↓
Semantic Layer
↓
Alignment Layer
↓
Specification Layer
↓
Codex
```

## Semantic Layer

回答：

> What did user say?

负责理解用户表达、提取 intent 和 claims，并将它们映射到真实证据。

## Alignment Layer

回答：

> What should happen next?

包含：

- Horizon：长期方向、目标空间和关键未知。
- Checkpoint：关键阶段的重新确认点。
- Decision Context：当前阶段的决策状态。

Alignment Layer 不替用户创造产品方向，也不替代 Codex 的技术判断。

## Specification Layer

回答：

> What should Codex execute?

负责把已经对齐的目标、范围、约束和验收条件整理为可执行任务接口。

## Codex

负责如何实现，包括技术方案、代码修改、工程执行、测试和调试。

目标架构是 Future Direction。当前运行时尚未按该分层重构。

# 3. Module Responsibility Changes

## Semantic

保持：

- intent extraction
- claim extraction
- evidence mapping

不负责：

- stage decision
- next action selection
- 产品方向决策

## Readiness

当前主要表示 execution readiness。未来可能演化为 alignment readiness：判断目标、边界、阶段和关键决策是否足以支持下一步对齐。

该演化不应削弱当前的安全阻断和证据要求，也不应在没有实现和验证前改变现有判定。

## Router

未来可以根据 Alignment Context 路由，而不只根据原始输入模式选择路径。Router 仍负责路径选择，不拥有用户决策，也不执行任务。

## Reporter

未来可以增强为展示：

- Horizon
- Current Stage
- Open Decisions
- Next Checkpoint

展示增强不应暴露内部推理、证据实现细节或未经确认的决策。

# 4. Refactoring Strategy

采用渐进迁移，保持旧流程可比较、可回退：

## Phase 1：新增旁路 Alignment Context

基于现有 Semantic Result 和规则生成旁路上下文，不改变旧 Brief、Specification 或 Planning 结果。

## Phase 2：Reporter 支持展示

在不改变决策的前提下，向调试或明确的展示入口增加 Horizon、阶段、开放决策和 Checkpoint 信息。

## Phase 3：Router 使用 Alignment 状态

经过旁路验证后，允许 Router 读取 Alignment 状态选择交互路径，同时保留原有路径作为可比较的回退边界。

## Phase 4：逐步减少旧 Brief 直接生成

只有在 Alignment Context 和 Router 行为经过验证后，才逐步让 Specification 和 Brief 使用对齐后的上下文，避免一次性替换现有任务准备路径。

每个阶段都必须保持现有测试通过，并针对行为差异增加回归和对照验证。本文档不执行上述任何阶段。

# 5. Alignment Checkpoint Design

Checkpoint 不是审批，也不是无条件阻止执行。它是关键阶段的重新确认点，用于检查当前目标、范围和下一步行动是否仍然一致。

计划关注以下转换：

```text
Idea → Definition
Definition → Implementation
Implementation → Verification
```

在每个转换处，Checkpoint 应呈现已确认内容、仍开放的问题和拟采取的下一步。用户保留方向和是否继续的决定权；Checkpoint 不自动授予 Codex 执行权限。

# 6. Migration Risks

## 过度复杂化

新增层次可能增加状态、接口和维护成本。如果不能改善关键决策质量，就不应引入额外抽象。

## 与 Codex 功能重复

强 Agent 已经能够澄清需求和探索方案。Alignment Layer 不应复制这些模型能力，而应提供稳定、可验证的协作边界。

## Memory 化风险

Decision Context 或 Horizon 可能逐渐变成保存所有历史的系统。应只保留支持当前对齐和下一步决策的有限状态。

## Planner 化风险

Alignment Layer 可能被误用为自动规划器。它应帮助选择下一步，不应生成未经确认的完整项目路线图或替用户决定产品方向。

# 7. Non Goals

本次架构评估不做：

- 全自动项目经理。
- 自动路线规划。
- Long Memory。
- Multi Agent。

也不替代 Coding Agent，不改变当前 Semantic、Evidence、Readiness、Router、Specification、Planning 或 Reporter 的运行逻辑。

# 8. Implementation Decision

当前阶段只完成架构设计和迁移评估，不实现重构。

下一阶段是否进入代码重构，应根据本设计、Phase 6A/6C 验证结果和现有回归测试决定。任何实现都需要单独的范围、测试和回退方案，不由本文档自动授权。
