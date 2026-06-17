# AGENTS.md

This project uses the Spec / Loop / Verify / Memory operating protocol.

## Default Workflow

Use a managed request before implementation. In Claude Code, prefer:

```text
/ai-request --task feature --name "<name>" --requirements docs/requirements/<name>.md
/ai-execute
```

In Codex or a shell, use the installed `.codex` skill scripts when present:

```bash
python .codex/skills/ai-engineering-discipline/scripts/run_request.py . --task feature --name "<name>" --requirements docs/requirements/<name>.md
python .codex/skills/ai-engineering-discipline/scripts/execute_request.py .
```

If `.claude/skills` or `.codex/skills` are missing, run the framework bootstrap script before starting work.

## Operating Rules

- Create or update a spec before coding.
- Select a loop before implementation.
- Run verification before claiming completion.
- Update memory only with evidence-backed rules, boundaries, or pitfalls.
- Stop before destructive operations, credentials, production data, or unclear architecture changes.

Generated explanations are not verification evidence.
