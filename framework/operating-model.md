# Operating Model

## Roles

| Role | Responsibility |
|---|---|
| Product Owner | 定义业务目标、非目标和验收标准 |
| Tech Lead | 审查 spec、模块边界、技术风险和 verify gate |
| Developer | 使用 AI 实现、补测试、提交验证证据、更新 memory |
| Reviewer | 审查代码、验证证据、需求一致性和反合理化风险 |
| AI Agent | 生成初稿、补测试、做检查、整理文档；不承担最终责任 |

## Required Project Files

```text
docs/specs/requirements/
docs/specs/design/
docs/specs/adr/
docs/verify/test-matrix.md
docs/verify/release-checklist.md
docs/memory/project-rules.md
docs/memory/module-map.md
docs/memory/pitfalls.md
AGENTS.md
```

## PR Flow

1. Product Owner or Developer creates a spec.
2. Tech Lead approves scope for medium or high-risk changes.
3. Developer uses AI to plan and implement.
4. Developer runs verify checklist.
5. Reviewer checks both diff and evidence.
6. Developer updates memory if the change adds new rules or lessons.
7. PR merges only after all required gates pass.

## Governance Rules

- AI output is treated as untrusted until verified.
- A PR cannot use “AI generated” as a reason to reduce review depth.
- Any repeated issue must become a memory entry.
- Any cross-module change must update design docs or ADR.
- Any skipped test must include owner, reason, risk, and follow-up date.
