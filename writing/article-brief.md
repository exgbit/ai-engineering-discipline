# Article Brief

## Working Title

AI 编程的下一站，不是更强的工具，而是更硬的工程纪律

## Core Thesis

2026 年的 AI 编程讨论正在从工具论转向工程纪律论。真正可规模化的 AI 编程，不是让工程师更会写 prompt，而是让团队建立三件套：`Spec`、`Verify`、`Memory`。

## Target Audience

- CTO / 技术负责人
- 研发效能负责人
- 一线 Tech Lead
- 已经大量使用 Cursor、Claude Code、Copilot、Replit、Warp 等工具的工程团队

## Key Claims

1. Vibe coding 适合探索，不适合没有约束的生产交付。
2. AI 编程失败通常不是模型不会写代码，而是团队没有提供清晰规格、验证门和长期上下文。
3. 多个新方法论都在收敛到同一件事：把 AI 放回工程系统里。
4. 公司落地 AI 编程，应优先建设 Spec / Verify / Memory，而不是先采购更多工具。

## Data To Use

- Replit 事故作为反例：无约束 agent + 生产环境 + 验证缺失。
- Axios / RedAccess 报道作为安全风险信号：vibe coding 应用可能导致敏感数据暴露。
- 仓库内 `data/sample-adoption-metrics.csv` 只能作为 synthetic 示例。
- 公司试点后应替换为真实 4 周数据。

## Article Structure

1. 开场：AI 编程进入纪律化拐点。
2. 问题：vibe coding 为什么在团队生产中失效。
3. 框架：Spec / Verify / Memory 三件套。
4. 落地：4 周试点方案。
5. 数据：如何衡量 AI 编程是否真的提高工程质量。
6. 结尾：AI 不会消灭工程纪律，只会惩罚没有纪律的团队。

## Publication Checklist

- [ ] 补齐 Trellis / ai-devkit / Warp SDD / Addy Osmani 原始链接。
- [ ] 决定是否使用 Replit 事故作为公开案例。
- [ ] 将 synthetic metrics 替换为真实试点数据，或明确不使用数据结论。
- [ ] 给出 GitHub 仓库链接。
