# Adoption Roadmap

## Goal

用 4 周在一个真实项目中验证 Spec / Verify / Memory 框架是否能降低 AI 编程的返工率、缺陷率和 review 成本。

## Week 1: Baseline and Structure

交付物：

- 创建 `docs/specs/`、`docs/verify/`、`docs/memory/`。
- 创建 `docs/loops/`，先记录人工 checklist loop。
- 引入 `spec-template.md`、`pr-template.md`、`verify-checklist.md`。
- 为一个核心业务流程建立 `test-matrix.md`。
- 记录试点前基线数据：PR 数、返工率、缺陷数、review 轮次、构建失败率。

验收：

- 新需求必须有验收标准。
- AI 生成 PR 必须在描述中声明 AI 参与范围。

## Week 2: Verify Gate

交付物：

- 接入或强化 CI：lint、test、typecheck、security scan。
- 对核心模块补最小回归测试。
- PR 模板加入验证证据区。

验收：

- 无验证证据的 PR 不允许合并。
- 主干构建失败必须复盘并记录到 memory。

## Week 3: Memory System

交付物：

- 建立 `project-rules.md`、`module-map.md`、`pitfalls.md`。
- 汇总最近 10 个 bug / 返工案例，提炼反模式。
- 建立高频任务 prompt 或 agent instruction。
- 选择 1 个重复任务，写成 loop runbook。

验收：

- 新人或 AI Agent 能通过 memory 文件理解项目边界。
- 重复类 review 评论数量开始下降。

## Week 4: Evaluation and Rollout

交付物：

- 复盘试点指标。
- 输出公司级《AI 编程 PR 准入规则》。
- 决定推广范围：单项目、单团队或全研发。

验收：

- AI 生成代码的回滚率不高于人工代码。
- 需求到测试的可追溯率达到 80% 以上。
- Review 从基础问题转向设计和边界问题。

## Rollout Criteria

满足以下条件后再推广：

- 模板稳定，团队能独立使用。
- Verify gate 不显著拖慢小需求交付。
- Memory 文件每周有人维护。
- 至少一个常用任务已经从 prompt 升级为 loop。
- 指标显示返工率或缺陷率下降。
