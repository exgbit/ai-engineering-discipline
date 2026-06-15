# Operation Reference

## Four-Layer Runtime

```text
Spec -> Loop -> Verify -> Memory
```

- Spec: task target, scope, acceptance criteria, test plan.
- Loop: state machine, policy, retry, exit, budget.
- Verify: tests, lint, build, CI, manual evidence.
- Memory: durable rules, module boundaries, pitfalls, loop improvements.

## First-Run Sequence

1. Run `scripts/init_project.py <target>`.
2. Run `scripts/inspect_project.py <target>`.
3. Inspect project stack and commands.
4. Seed `docs/memory/project-rules.md` and `docs/memory/module-map.md` only with evidence.
5. Create the first real spec.
6. Select `bugfix-loop.md` or create a feature loop.
7. Implement in small steps.
8. Run verify gates.
9. Update memory.

## Do Not Automate Past These Gates

- destructive operations;
- production infrastructure or data;
- credentials, billing, permission changes;
- missing or failing verification;
- unclear architecture boundary;
- retry budget exceeded.
