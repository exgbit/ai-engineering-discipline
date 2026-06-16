# Company Pilot Playbook

## Purpose

Use this playbook to run a small company pilot before making Spec / Verify / Memory mandatory across all engineering teams.

## Pilot Selection

Choose one project that meets these conditions:

- active weekly development;
- at least three engineers;
- existing CI or a clear path to add CI;
- enough business value that quality matters;
- not a high-pressure emergency project.

Avoid starting with a deeply unstable project. The framework should improve engineering discipline, not hide missing ownership.

## Kickoff Checklist

- [ ] Pick pilot project and owner.
- [ ] Create `docs/specs/`, `docs/verify/`, and `docs/memory/`.
- [ ] Create `docs/loops/` for repeatable agent workflows.
- [ ] Copy templates into the project.
- [ ] Define AI-assisted PR labeling rules.
- [ ] Record baseline metrics for the previous 2-4 weeks.
- [ ] Agree on non-negotiable verify gates.

## Weekly Rituals

### Monday: Spec Review

Review upcoming AI-assisted tasks. Confirm each task has acceptance criteria, non-goals, and risk level.

### Wednesday: Verify Review

Check whether open PRs include validation evidence. Escalate PRs that rely on explanation rather than proof.

### Friday: Memory Update

Add new project rules, module boundary changes, repeated review comments, and incident lessons to memory docs.

## Pilot Data

Track these metrics weekly:

- AI-assisted PR count;
- spec coverage rate;
- test traceability rate;
- average review rounds;
- main branch failure rate;
- escaped defects;
- memory update rate.
- loop success rate;
- loop wall-time and token budget.

Use the framework report commands to produce evidence:

```bash
python .claude/skills/ai-engineering-discipline/scripts/ai_discipline.py report .
python .claude/skills/ai-engineering-discipline/scripts/ai_discipline.py metrics .
```

For multiple pilot projects, aggregate from a summary repository or one selected project:

```bash
python .claude/skills/ai-engineering-discipline/scripts/ai_discipline.py metrics . --input ../project-a --input ../project-b
```

Each `report` call keeps the latest report at `docs/reports/pilot-report.*` and archives a historical copy under `docs/reports/runs/`. Use the archived runs for weekly trend analysis.

## Decision After Four Weeks

Choose one:

- `Adopt`: make the framework standard for the team.
- `Extend`: run two more weeks with adjusted gates.
- `Stop`: document why the framework did not fit the project.

Do not scale until the pilot shows either lower rework, better traceability, or clearer review behavior.
