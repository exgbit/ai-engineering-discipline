# Presets

Presets hide low-level framework parameters from users.

Users provide:

```text
task + risk + requirement path
```

The framework resolves:

```text
Spec Kit mode and required spec sections
LangGraph loop, retries, checkpoint, human gate
Semgrep config, severity, native checks
Mem0/local memory write behavior and tags
```

Example:

```bash
python scripts/run_request.py /path/to/project \
  --task feature \
  --name "refund approval" \
  --requirements /path/to/refund.md \
  --risk medium
```

This writes `docs/ai-engineering/current-request.md` with the resolved parameters.
