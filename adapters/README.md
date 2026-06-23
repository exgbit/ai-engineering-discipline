# Adapters

The framework's generated artifacts need no external template framework. Development-task verification uses external gates: **codebase-memory** is required for impact analysis, and **Semgrep** is the optional security-scan gate.

| Layer | External tool | Called by the framework? | Need to install? |
|---|---|---|---|
| Spec | GitHub Spec Kit | No — style reference only | No |
| Loop | LangGraph | No — style reference only | No |
| Verify / Impact | codebase-memory | Yes — impact-analysis gate | Required for development tasks (opt out only with `AI_DISCIPLINE_GRAPH_OPTIONAL=1`) |
| Verify / Security | Semgrep | Yes — security-scan gate | Optional (skipped/uncovered if absent) |
| Memory | Mem0 | No — style reference only | No |

Spec / Loop / Memory are implemented by the framework's own Markdown templates plus the AI agent — the named tools are only stylistic references and are never called. The control plane is:

```text
Spec -> Loop -> Verify -> Memory
```

Verify calls codebase-memory through `scripts/code_graph.py` to compute the change blast radius, then crosses that with the test index. Semgrep remains optional and is used only for security scanning — see `default-stack.json`.
