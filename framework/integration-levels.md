# Tool Names and What They Mean

This project is an independent AI coding workflow framework. It is not affiliated with, endorsed by, or officially maintained by GitHub Spec Kit, LangGraph, Semgrep, or Mem0. Project names and trademarks belong to their respective owners.

The Spec / Loop / Memory steps are implemented entirely by the framework's own Markdown templates plus the AI agent. The named open-source tools are only stylistic references — the framework does not call them. Runtime verification calls codebase-memory for required impact analysis and may call Semgrep for optional security scanning.

| Layer | Tool name | Called at runtime? | Need to install? |
|---|---|---|---|
| Spec | GitHub Spec Kit | No — style reference only | No |
| Loop | LangGraph | No — style reference only | No |
| Verify / Impact | codebase-memory | Yes — runs `index_repository` + `detect_changes` through `scripts/code_graph.py` | Required for development tasks (opt out only with `AI_DISCIPLINE_GRAPH_OPTIONAL=1`) |
| Verify / Security | Semgrep | Yes — runs `semgrep scan` as the security gate | Optional (skipped/uncovered if absent) |
| Memory | Mem0 | No — style reference only | No |

## Verification Policy

- Core workflow artifacts stay usable even if runtime tools are not installed, but development-task verification will block without codebase-memory unless explicitly opted out.
- Runtime tools fail closed: missing codebase-memory blocks the impact gate; missing Semgrep is reported as `uncovered` when the preset requires it, never silently successful.

## Release Wording

Recommended wording for public release:

> AI Engineering Discipline is an independent workflow framework that organizes AI coding around four engineering controls: Spec, Loop, Verify, and Memory. It runs on its own Markdown templates plus your AI agent; verification calls codebase-memory for required impact analysis and can call Semgrep as an optional security-scan gate. It is not affiliated with GitHub Spec Kit, LangGraph, or Mem0, and it does not call or require them.
