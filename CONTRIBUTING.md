# Contributing

## Scope

This project accepts contributions that improve the Spec / Verify / Memory framework, including:

- clearer templates;
- adoption playbooks;
- measurable engineering metrics;
- examples from real teams with sensitive details removed;
- verification gates for specific stacks.

## Contribution Rules

- Do not add unverifiable public claims without source links.
- Mark synthetic or example data clearly.
- Keep templates tool-neutral unless the file is explicitly about one stack.
- Prefer actionable checklists over abstract principles.
- Do not include company secrets, private repository names, credentials, or customer data.

## Source of Truth for Skill Copies

The top-level `scripts/`, `presets/`, `templates/`, `examples/`, `claude-code-commands/`, `CLAUDE.md`, and `adapters/default-stack.json` are the single source of truth. The `claude-code-skills/` and `skills/` directories ship copies (installed into a target project's `.claude/` and `.codex/`), so never edit those copies by hand.

After changing any source file, run:

```bash
python scripts/sync_skills.py        # regenerate skill copies
python scripts/sync_skills.py --check # verify no drift (also enforced in CI)
```

`SKILL.md` is the only file allowed to differ per platform (`.claude` vs `.codex`); `sync_skills.py --check` lints it for cross-platform path leaks.

## Recommended PR Format

- What changed?
- Why is it useful for AI-assisted development?
- Which pillar does it improve: Spec, Verify, or Memory?
- How should teams adopt it?
- What risks or limitations remain?

## Data Contributions

When adding data, include:

- source;
- collection method;
- time range;
- whether the data is synthetic, anonymized, or public;
- known bias or limitation.
