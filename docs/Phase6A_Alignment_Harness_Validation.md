# Phase 6A Alignment Harness Validation

## Document Status

- Scope: validation goals and comparison design
- Product position: Human-to-Agent Alignment Harness
- Implementation status: Phase 6 development has not started

本文档定义 Phase 6A 需要验证的问题、比较方式和成功条件。它不是实现方案，不授权新增运行能力，也不预设 Horizon、State、Decision 或 Navigation Core 的具体设计。

# 1. Validation Hypothesis

Phase 6A 的核心假设是：用户通过 JIA 与 Coding Agent 协作时，相比直接使用 Coding Agent，可以提高 Human-Agent 协作质量。

验证关注以下问题：

- 是否减少错误方向执行？
- 是否减少需求返工？
- 是否提高下一步决策质量？

Phase 6A 不验证：

- JIA 是否替代 Codex。
- JIA 是否自动完成项目。
- JIA 是否生成完整项目规划。

验证结论应来自相同或可比任务下的实际对照结果，不从模块存在、测试通过或输出结构完整直接推断产品价值。

# 2. Comparison Model

## Baseline

```text
User
↓
Coding Agent
↓
Result
```

Baseline 组由用户直接向 Coding Agent 提交原始请求，不经过 JIA 的意图整理、就绪判断或交互路径选择。

## JIA Assisted

```text
User
↓
JIA
↓
Coding Agent
↓
Result
```

JIA Assisted 组使用相同的原始请求。JIA 可以识别关键未知因素、判断是否适合执行，并在请求明确时形成有边界的任务交付。

比较重点不是代码能力，而是 Human-Agent Alignment Quality。两组应尽量保持 Coding Agent、项目基线和任务证据一致，避免把模型能力、代码库差异或额外人工提示误认为 JIA 的效果。

# 3. Test Scenarios

## Scenario A: Ambiguous Product Idea

Example:

> 我想做一个AI帮助大学生学习的软件。

观察 Baseline 是否过早进入产品设计、技术选型或实现，并记录其是否在关键目标未知时形成了具体工程行动。

观察 JIA 是否识别：

- 缺少目标用户。
- 缺少核心问题。
- 缺少第一阶段范围。

该场景验证 JIA 能否避免错误启动，而不是要求 JIA 自动完成产品发现。

## Scenario B: Concrete Feature Request

Example:

> 课程管理系统增加作业功能，老师可以创建作业，学生可以查看。

观察 JIA 是否：

- 保持执行效率。
- 不产生不必要阻碍。

该场景同时检查 Alignment Harness 的成本。明确任务不应因额外协调层而被反复询问、扩大范围或延迟交付。

## Scenario C: Mid-project Change

前置条件：项目已有明确目标、当前范围和阶段证据，用户在推进过程中提出新的功能方向。

观察 JIA 是否帮助判断：

- 新方向是否符合当前目标。
- 是否需要重新对齐。

该场景不要求自动决定接受或拒绝变更。JIA 应暴露目标关系和关键决策点，由用户保留方向决策权。

# 4. Evaluation Criteria

## Alignment Quality

评估是否正确理解用户真实目标，是否区分原始表达、解释和尚未确认的假设。

## Scope Control

评估是否避免无意义范围扩大，是否保留明确包含、排除和未来考虑。

## Decision Quality

评估是否帮助用户识别关键未知因素并选择合理下一步，而不是直接生成未经确认的完整方案。

## Execution Efficiency

评估是否避免过度阻碍明确任务，包括无必要确认、重复信息收集和与结果无关的流程开销。

每项评价应同时记录 Baseline 与 JIA Assisted 的可观察行为、结果和返工情况。评价不能只依据 JIA 自己生成的状态标签。

# 5. Success Criteria

Phase 6A 的成功条件是：

- JIA 在模糊任务中明显减少错误启动。
- JIA 在明确任务中不过度干预。
- JIA 能帮助用户识别关键未知因素。

成功需要在多类场景中表现一致，并且没有以显著降低明确任务执行效率为代价。单个演示、单次正确分类或现有单元测试通过不足以证明假设成立。

# 6. Non Goals

Phase 6A 不实现：

- Navigation Engine。
- Memory System。
- Autonomous Planning。
- Multi-Agent System。
- Workflow Engine。

Phase 6A 也不扩展 Coding Agent 执行能力，不改变当前语义、证据、安全、就绪、路由、规划或报告逻辑。

# 7. Next Step After Validation

只有在对照验证表明 Alignment Harness 具有实际价值后，才考虑后续能力：

- Horizon。
- State。
- Decision。
- Navigation Core。

后续设计应由验证中观察到的具体问题驱动。Phase 6A 不预先承诺这些模块的接口、数据模型、持久化方式或实现顺序。
