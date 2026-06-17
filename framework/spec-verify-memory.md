# Spec / Verify / Memory Framework

## 1. Why This Framework Exists

AI 编程放大了工程师的产出，也放大了需求不清、验证不足、上下文缺失带来的风险。传统的“边聊边写、跑通就合并”的 vibe coding 在团队级项目中不可控，尤其容易产生以下问题：

- 需求口径漂移，AI 按错误理解快速生成大量代码。
- Review 只看 diff，不看需求、测试和风险证据。
- 同样的项目背景、架构边界、历史坑点反复解释。
- AI 为错误实现生成看似合理的解释，团队误判质量。

因此，AI 编程的核心不是“更会提示词”，而是建立 **Spec / Verify / Memory 三件套 + Loop** 的闭环。三件套是支柱清单;按执行顺序展开即 `Spec -> Loop -> Verify -> Memory`（与 CLAUDE.md、编排 skill、integrated-workflow 一致）。

## 2. The Three Pillars and the Loop Layer

### Spec: 规格先行

Spec 是 AI 编程的输入边界。它回答：

- 为什么要做？
- 做到什么程度算完成？
- 哪些范围明确不做？
- 涉及哪些模块、接口、数据和权限？
- 边界条件和失败路径是什么？

最低要求：

- 小改动：issue 中必须有验收标准。
- 中型需求：必须有 `spec-template.md`。
- 跨模块改动：必须有 ADR 或设计文档。

### Verify: 验证准入

Verify 是 AI 编程的输出约束。它回答：

- 代码是否编译和测试通过？
- 是否覆盖正常、异常、边界和回归路径？
- 是否有安全、性能、兼容性风险？
- 人类 reviewer 审查了哪些关键点？

最低要求：

- 编译、lint、单元测试必须通过。
- PR 必须说明测试证据和风险。
- 核心链路必须有集成测试或手工验收记录。

### Memory: 记忆沉淀

Memory 是 AI 编程的长期上下文。它回答：

- 项目有哪些不可违反的架构规则？
- 哪些模块归谁负责，边界是什么？
- 历史上踩过哪些坑？
- 哪些 prompt、检查清单、测试套路可复用？

最低要求：

- 每个项目维护 `docs/memory/project-rules.md`。
- 每次线上事故、返工、重大 review 问题都沉淀到 `pitfalls.md`。
- 每次跨模块设计变化更新 `module-map.md` 或 ADR。

### Loop: 循环编排

Loop 是 AI 编程的执行层。它回答：

- agent 每一步该读什么、做什么、验证什么？
- 哪些失败可以自动重试，哪些必须升级给人？
- token、wall-time、成本和失败率预算是多少？
- 完成或失败后，哪些信息要写入 memory？

最低要求：

- 重复任务必须有 loop runbook。
- loop 必须有成功和失败两类退出条件。
- loop 继续执行必须依赖验证证据，而不是生成解释。

## 3. Development Loop

```text
Idea / Issue
  -> Spec
  -> Loop Selection
  -> Load Memory
  -> AI-assisted Plan
  -> Implementation
  -> Verify Gate
      -> Retry / Escalate / Exit
  -> Review
  -> Merge
  -> Memory Update
```

关键原则：

- 没有 spec，不进入实现。
- 没有 verify，不进入主干。
- 没有 memory，下次继续付同样的沟通成本。
- 没有 loop，团队只能靠个人 prompt 技巧重复劳动。

## 4. Anti-Rationalization Gate

AI 最危险的失败模式之一，是为错误实现生成合理解释。因此，review 时必须追问证据。

| 常见说法 | 审查问题 |
|---|---|
| “应该没问题” | 哪个测试证明没问题？ |
| “只是小改动” | 影响面和回归范围在哪里？ |
| “AI 写的逻辑很完整” | 是否覆盖异常、并发、权限、回滚？ |
| “先合并，后面补测试” | 为什么不能现在补？风险由谁接受？ |

## 5. Definition of Done

一个 AI 辅助开发任务完成，必须同时满足：

- Spec 中的验收标准全部被验证。
- PR 中列出 AI 参与范围、人类审查点和测试证据。
- 相关测试、文档、配置同步更新。
- 新增规则、坑点或边界变化写入 memory。
- 重复性任务沉淀为 loop，并明确退出条件、重试策略和预算。
