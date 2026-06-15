# AI 编程的下一站：从 Prompt Engineering 到 Loop Engineering

过去一年，AI 编程的主线一直是工具：更强的模型、更快的补全、更聪明的 Agent、更自然语言化的 IDE。很多团队的第一反应也是采购工具、训练 prompt、鼓励工程师提高个人效率。

但 2026 年 Q2 末，一个更重要的判断开始变得清晰：AI 编程真正的分水岭，不是工具能力，而是工程纪律。

我把这个判断总结成四层：`Spec / Verify / Memory / Loop`。

前三层是纪律底座，第四层是执行范式。Spec 规定目标，Verify 规定证据，Memory 沉淀上下文，Loop 把 agent 放进一个可控制、可停止、可复盘的运行系统里。

## Vibe Coding 的边界已经出现

Vibe coding 的价值不能否认。它非常适合原型、demo、一次性脚本、低风险内部工具。它让想法到代码的距离变短，让非传统开发者也能参与软件创造。

但它一旦进入公司级生产项目，问题就会迅速暴露：

- 需求没有写清，AI 会高速实现错误理解。
- 没有验证门，AI 的解释会替代真实证据。
- 没有项目记忆，每次任务都要重新解释模块边界和历史坑点。
- 没有人类责任边界，Agent 的自主行为会变成生产风险。

Replit 相关事故和后续安全报道已经给出过警示：当 AI 编程工具拥有真实环境写权限，而团队缺少隔离、验证、审查和回滚机制时，风险不是理论上的。

所以问题不是“要不要用 AI 编程”，而是“用什么工程系统约束 AI 编程”。

## 从 Prompt Agent 到 Design Loop

Prompt Engineering 的默认动作是：我写一段更好的提示词，让 agent 跑得更准。

Loop Engineering 的默认动作是：我设计一个 loop，让 loop 自动 prompt agent、检查结果、决定是否重试、何时停止、何时升级给人、最后把经验写回 memory。

这两者的差异很大。

在 prompt 层，工程师优化的是一次对话。在 loop 层，工程师设计的是一个控制系统：

- 状态机：现在处于读 spec、写测试、实现、验证、修复还是退出？
- 策略：哪些文件可以动，哪些命令可以跑，哪些动作必须审批？
- 验证：什么证据允许 loop 继续？
- 退出条件：什么时候成功停止，什么时候失败停止？
- 预算：最多消耗多少 token、wall-time、重试次数和成本？
- 记忆：本次成功或失败后，什么要写入项目 memory？

这也是为什么单纯“会写 prompt”不够。真正的产品形态不是 prompt 接口，而是 loop 接口。

## 四条路径，指向同一个答案

最近一组 AI 编程方法论信号很有意思：Trellis 强调 spec git 化，ai-devkit 强调工程门户，Warp SDD 强调规格驱动，Addy Osmani 强调 verify gate 和 anti-rationalization。另一组 Claude Code 社区工具则开始把注意力放到 loop：夜间跑 agent、多层 safety、parent-worker、tmux/worktree 并行、hook 可视化、常驻 daemon、prompt improver 等。

这些项目和文章的具体实现不同，但底层判断非常一致：AI 编程不能只靠即时对话，必须进入工程流程。

发布本文前，这些来源需要补齐原始链接；但就方法论方向而言，它们共同指向同一个答案：

> AI 编程要规模化，必须具备 Spec、Verify、Memory，并把重复任务升级为 Loop。

## Spec：先有规格，再有代码

Spec 是 AI 编程的输入边界。

没有 spec，AI 得到的其实不是任务，而是一段模糊愿望。它会补全缺失信息，也会补全错误假设。人类看起来是在“指挥 AI”，实际是在让 AI 猜业务。

公司项目中，至少要做到三层：

- 小需求：issue 里必须有验收标准。
- 中型需求：必须有需求、非目标、边界条件、测试计划。
- 跨模块需求：必须有设计文档或 ADR。

AI 可以参与写 spec，但不能绕过 spec。

## Verify：不要相信解释，只相信证据

AI 最大的风险之一，不是写错代码，而是能把错误解释得很合理。

所以团队必须建立 verify gate：

- 编译、lint、typecheck、单元测试是最低门槛。
- 核心链路必须有集成测试或手工验收记录。
- PR 必须说明 AI 参与范围、验证证据、风险和回滚方式。
- Reviewer 不能只看 diff，还要看需求是否被测试覆盖。

一句话：AI 生成内容进入主干之前，必须先从“看起来合理”变成“证据上成立”。

## Memory：让项目上下文变成资产

很多团队使用 AI 编程时，会反复遇到同一个问题：每次都要重新告诉 AI 项目架构、模块边界、命名规则、历史坑点、哪些代码不能碰。

这说明团队没有 memory。

Memory 不是聊天记录，而是项目长期上下文：

- `project-rules.md`：项目规则和禁止事项。
- `module-map.md`：模块边界和负责人。
- `pitfalls.md`：历史事故、返工原因、反模式。
- `test-matrix.md`：需求到测试的映射。
- `AGENTS.md`：AI Agent 进入项目时必须读取的说明。

没有 memory，AI 编程效率会停留在个人技巧；有 memory，AI 才能变成团队能力。

## Loop：让 Agent 工作流变成产品接口

Loop 是前三件事的执行层。

一个合格的 AI coding loop 至少要定义：

- 输入：spec、issue、memory、允许访问的目录。
- 范围：可以动什么，不能动什么，什么要审批。
- 状态：读上下文、计划、实现、验证、升级、完成。
- 验证门：哪些测试、lint、review 或人工验收必须通过。
- 重试策略：失败后能重试几次，每次允许改变什么。
- 退出条件：成功怎么停，失败怎么停。
- 预算：token、时间、成本和失败率上限。
- 记忆写回：哪些坑点和规则要沉淀。

这就是“agent loop 架构师”和“prompt 工程师”的区别。前者设计控制系统，后者优化单次输入。

## 公司应该怎么落地

我建议用 4 周试点，而不是一上来全公司强推。

第 1 周：建立目录和模板，补齐一个核心流程的 spec 和 test matrix。

第 2 周：接入 verify gate，让无测试、无证据、无风险说明的 PR 不能合并。

第 3 周：建立 memory，把最近的 bug、返工和 review 重复问题沉淀下来，并选择一个重复任务写成 loop runbook。

第 4 周：复盘数据，看 AI 编程是否真的降低返工率、构建失败率和 review 成本，并评估 loop 的成功率、重试率、升级率和预算超限率。

衡量指标也要从“写了多少代码”转向“交付是否更可控”：

- AI-assisted PR 数量；
- spec coverage rate；
- test traceability rate；
- review rounds per PR；
- main branch failure rate；
- escaped defects；
- memory update rate。
- loop success rate；
- loop retry / escalation / budget overrun rate。

## 结论

AI 编程不会消灭工程纪律。相反，它会放大纪律的价值，也会惩罚没有纪律的团队。

未来的高效团队，不是让每个人都成为 prompt 大师，而是让 AI 在清晰规格、严格验证、长期记忆和可控 loop 中工作。

工具会继续变化，模型会继续升级，IDE 会继续重构。

但 Spec / Verify / Memory / Loop 会留下来。
