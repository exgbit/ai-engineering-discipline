# Repository Guidelines

## Project Structure & Module Organization

This repository defines an AI engineering workflow around Spec, Loop, Verify, and Memory. Framework documentation lives in `framework/`. Reusable templates live in `templates/`. Bootstrap and automation scripts live in `scripts/`. Codex skills are under `skills/`, while Claude Code skills and slash commands are under `claude-code-skills/` and `claude-code-commands/`. Example artifacts are in `examples/`, and adoption metrics live in `data/`.

## Build, Test, and Development Commands

Use the scripts directly from the repository root:

```bash
./scripts/bootstrap.sh /path/to/project
python scripts/run_request.py /path/to/project --task feature --name "example" --requirements /path/to/req.md
python scripts/execute_request.py /path/to/project --run-native-checks
python scripts/summarize_metrics.py data/sample-adoption-metrics.csv
```

Validate changed Python with `python -m py_compile scripts/*.py`. Validate shell wrappers with `bash -n scripts/*.sh`.

## Coding Style & Naming Conventions

Python scripts use standard-library dependencies, type hints where practical, and small functions with explicit inputs. Keep generated framework artifacts marked with `<!-- ai-engineering:generated -->`. Use kebab-case for preset names, loop files, and Claude command files, for example `feature-medium.json` and `ai-request.md`.

## Testing Guidelines

There is no single test framework. Use focused smoke tests against temporary target projects under `/tmp`, then verify generated files in `docs/specs/`, `docs/loops/`, `docs/verify/`, and `docs/memory/`. When changing skills, run the local skill validator for both `skills/` and `claude-code-skills/`.

## Commit & Pull Request Guidelines

Follow the existing commit style: short lowercase scope plus imperative summary, such as `verify: write structured execution results`. PRs should explain which pillar changed, include verification evidence, update relevant docs/templates, and mark synthetic data clearly.
