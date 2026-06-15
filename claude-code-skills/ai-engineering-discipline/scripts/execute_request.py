#!/usr/bin/env python3
"""Execute safe setup steps from docs/ai-engineering/current-request.md."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATED = "<!-- ai-engineering:generated -->"


@dataclass
class ManagedRequest:
    path: Path
    task: str
    name: str
    execute: bool
    preset: str
    risk: str
    requirements: list[Path]
    spec_path: Path
    loop_path: Path
    verify_matrix_path: Path
    memory_path: Path
    spec_params: dict[str, object]
    loop_params: dict[str, object]
    verify_params: dict[str, object]
    memory_params: dict[str, object]


def skill_script(name: str) -> Path | None:
    candidates = [
        Path(__file__).resolve().parent / name,
        ROOT / "skills" / "ai-engineering-discipline" / "scripts" / name,
        ROOT / "scripts" / name,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def slugify(value: str) -> str:
    result = []
    previous_dash = False
    for char in value.lower():
        if char.isalnum():
            result.append(char)
            previous_dash = False
        elif not previous_dash:
            result.append("-")
            previous_dash = True
    return "".join(result).strip("-") or "request"


def extract_section(text: str, heading: str) -> str:
    pattern = rf"^## {re.escape(heading)}\s*$([\s\S]*?)(?=^## |\Z)"
    match = re.search(pattern, text, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def extract_json_block(text: str, heading: str) -> dict[str, object]:
    pattern = rf"^### {re.escape(heading)}\s*```json\s*([\s\S]*?)\s*```"
    match = re.search(pattern, text, flags=re.MULTILINE)
    if not match:
        return {}
    try:
        value = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON block for {heading}: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"JSON block for {heading} must be an object.")
    return value


def parse_bullet_value(section: str, label: str) -> str:
    pattern = rf"^- {re.escape(label)}:\s*`?([^`\n]+)`?\s*$"
    match = re.search(pattern, section, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def parse_bullet_paths(section: str, target: Path) -> list[Path]:
    paths: list[Path] = []
    for match in re.finditer(r"^- `([^`]+)`\s*$", section, flags=re.MULTILINE):
        raw = match.group(1)
        if raw == "None":
            continue
        path = Path(raw)
        paths.append(path if path.is_absolute() else target / path)
    return paths


def parse_request(target: Path, request_path: Path) -> ManagedRequest:
    if not request_path.exists():
        raise SystemExit(f"Managed request not found: {request_path}")
    text = request_path.read_text(encoding="utf-8")
    task_section = extract_section(text, "Task")
    requirements_section = extract_section(text, "Requirement Sources")
    artifacts_section = extract_section(text, "Target Artifacts")

    def artifact(label: str, default: str) -> Path:
        raw = parse_bullet_value(artifacts_section, label) or default
        path = Path(raw)
        return path if path.is_absolute() else target / path

    task = parse_bullet_value(task_section, "Type")
    name = parse_bullet_value(task_section, "Name")
    execute = parse_bullet_value(task_section, "Execute implementation now") == "true"
    preset = parse_bullet_value(task_section, "Preset")
    risk = parse_bullet_value(task_section, "Risk")
    if not task or not name:
        raise SystemExit(f"Request is missing required Task fields: {request_path}")

    return ManagedRequest(
        path=request_path,
        task=task,
        name=name,
        execute=execute,
        preset=preset,
        risk=risk,
        requirements=parse_bullet_paths(requirements_section, target),
        spec_path=artifact("Spec", f"docs/specs/{slugify(name)}.md"),
        loop_path=artifact("Loop", "docs/loops/loop-template.md"),
        verify_matrix_path=artifact("Verify matrix", "docs/verify/test-matrix.md"),
        memory_path=artifact("Memory", "docs/memory"),
        spec_params=extract_json_block(text, "Spec"),
        loop_params=extract_json_block(text, "Loop"),
        verify_params=extract_json_block(text, "Verify"),
        memory_params=extract_json_block(text, "Memory"),
    )


def is_framework_placeholder(path: Path, content: str) -> bool:
    rel_path = "/".join(path.parts[-3:])
    if rel_path == "docs/verify/test-matrix.md":
        return "| Requirement ID | Requirement | Unit Test | Integration Test | Manual / Release Check | Status |" in content
    if "/docs/loops/" in "/" + "/".join(path.parts):
        return ("## Loop Name" in content and "Example:" in content) or (
            "# Bugfix Loop" in content and "Fix one well-scoped bug with reproduction" in content
        ) or (
            "# Loop Runbook Example: Bugfix Loop" in content and "Fix one well-scoped bug with test evidence" in content
        )
    return False


def safe_write(path: Path, content: str, force: bool, actions: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = GENERATED + "\n" + content.rstrip() + "\n"
    if path.exists() and not force:
        existing = path.read_text(encoding="utf-8")
        if GENERATED not in existing and not is_framework_placeholder(path, existing):
            actions.append(f"skip human file: {path}")
            return
    path.write_text(body, encoding="utf-8")
    actions.append(f"write: {path}")


def requirement_title(path: Path) -> str:
    if not path.exists():
        return path.name
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        clean = line.strip().lstrip("#").strip()
        if clean:
            return clean[:120]
    return path.name


def requirement_excerpt(path: Path, max_chars: int = 1200) -> str:
    if not path.exists():
        return f"Missing requirement source: `{path}`"
    text = path.read_text(encoding="utf-8", errors="ignore").strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "\n\n[truncated by execute_request.py]"


def rel(path: Path, target: Path) -> str:
    try:
        return str(path.relative_to(target))
    except ValueError:
        return str(path)


def write_requirements_index(target: Path, request: ManagedRequest, force: bool, actions: list[str]) -> Path:
    index = target / "docs" / "specs" / "requirements-index.md"
    lines = [
        "# Requirements Index",
        "",
        f"Request: `{request.name}`",
        f"Preset: `{request.preset}`",
        "",
        "| Source | Imported Title | Status |",
        "|---|---|---|",
    ]
    if request.requirements:
        for source in request.requirements:
            status = "found" if source.exists() else "missing"
            lines.append(f"| `{rel(source, target)}` | {requirement_title(source)} | {status} |")
    else:
        lines.append("| None | No external requirement source was provided. | open |")
    safe_write(index, "\n".join(lines), force, actions)
    return index


def write_spec(target: Path, request: ManagedRequest, force: bool, actions: list[str]) -> None:
    req_rows = []
    excerpts = []
    if request.requirements:
        for idx, source in enumerate(request.requirements, start=1):
            req_id = f"R{idx}"
            title = requirement_title(source)
            req_rows.append(f"| {req_id} | Import `{rel(source, target)}`: {title} | P0 | Source reviewed and mapped to tests |")
            excerpts.extend([
                f"### {req_id}: `{rel(source, target)}`",
                "",
                "```text",
                requirement_excerpt(source),
                "```",
                "",
            ])
    else:
        req_rows.append("| R1 | Define requirement before implementation | P0 | Requirement is explicit and testable |")
        excerpts.append("No external requirement source was provided.")

    content = f"""# Spec: {request.name}

## Problem

Define the problem from the imported requirement sources. Do not implement until open questions are resolved.

## Goal

Complete `{request.task}` work for `{request.name}` within `{request.risk or "unknown"}` risk policy.

## Non-Goals

- Do not expand scope beyond the managed request.
- Do not perform destructive operations without human approval.
- Do not treat AI explanation as verification evidence.

## Requirement Sources

{chr(10).join(f"- `{rel(source, target)}`" for source in request.requirements) if request.requirements else "- None"}

## Imported Requirement Excerpts

{chr(10).join(excerpts)}

## Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|---|---|---|---|
{chr(10).join(req_rows)}

## Design Notes

- Spec framework: `{request.spec_params.get("framework", "unknown")}`
- Spec mode: `{request.spec_params.get("mode", request.task)}`
- Implementation should be planned in small, reviewable steps.

## Edge Cases

- Empty or malformed input:
- Permission denied:
- Timeout / retry:
- Concurrency:
- Rollback:

## Test Plan

| Requirement ID | Test Type | Test File / Case | Status |
|---|---|---|---|
{chr(10).join(f"| R{idx} | pending | TBD | todo |" for idx, _ in enumerate(request.requirements or [Path('none')], start=1))}

## Open Questions

- [ ] Confirm the imported requirements are complete.
"""
    safe_write(request.spec_path, content, force, actions)


def write_loop(target: Path, request: ManagedRequest, force: bool, actions: list[str]) -> None:
    loop = request.loop_params
    content = f"""# Loop: {loop.get("runbook", request.task + "-loop")}

## Goal

Execute `{request.name}` through a bounded `{request.task}` loop.

## Inputs

- Spec: `{rel(request.spec_path, target)}`
- Request: `{rel(request.path, target)}`
- Requirement sources: {", ".join(f"`{rel(p, target)}`" for p in request.requirements) if request.requirements else "None"}
- Memory: `{rel(request.memory_path, target)}`

## Scope

Allowed:

- Update generated spec, loop, verify, and memory planning artifacts.
- Implement code only after spec and loop are accepted.

Forbidden:

- Destructive operations.
- Credential, billing, permission, or production changes.
- Unverified claims of success.

Requires approval:

- Architecture changes across module boundaries.
- Retrying beyond `{loop.get("max_retries", "preset")}` attempts.
- Human gate: `{loop.get("human_gate", "on_conflict")}`.

## State Model

| State | Description | Next States |
|---|---|---|
| load_context | Read request, spec, requirements, and memory | plan, stop |
| plan | Produce small implementation plan | implement, stop |
| implement | Make one scoped change | verify, stop |
| verify | Run required gates and collect evidence | implement, escalate, done |
| escalate | Ask for human review | implement, stop |
| done | Produce PR evidence and memory update |  |

## Verify Gates

- [ ] Spec exists and maps requirements.
- [ ] Test matrix exists.
- [ ] Native checks run when enabled by preset.
- [ ] Semgrep runs when enabled and available.
- [ ] Memory update is evidence-backed.

## Exit Conditions

Success:

- Acceptance criteria are verified with evidence.
- No unresolved P0 risk remains.

Failure:

- Requirements conflict.
- Verification cannot run.
- Work exceeds retry or approval policy.

## Retry Policy

- Max retries: `{loop.get("max_retries", "preset")}`
- Checkpoint: `{loop.get("checkpoint", "preset")}`
- What may change between retries: plan, tests, implementation details.
- What requires escalation: scope expansion, destructive work, unresolved verification.
"""
    safe_write(request.loop_path, content, force, actions)


def write_verify_artifacts(target: Path, request: ManagedRequest, force: bool, actions: list[str]) -> None:
    rows = []
    for idx, source in enumerate(request.requirements or [Path("none")], start=1):
        requirement = requirement_title(source) if source != Path("none") else request.name
        rows.append(f"| R{idx} | {requirement} | TBD | TBD | TBD | todo |")

    matrix = f"""# Test Matrix

Request: `{request.name}`
Spec: `{rel(request.spec_path, target)}`

| Requirement ID | Requirement | Unit Test | Integration Test | Manual / Release Check | Status |
|---|---|---|---|---|---|
{chr(10).join(rows)}
"""
    safe_write(request.verify_matrix_path, matrix, force, actions)

    plan = target / "docs" / "verify" / "current-request-verify.md"
    verify = request.verify_params
    content = f"""# Verify Plan: {request.name}

## Preset Policy

```json
{json.dumps(verify, ensure_ascii=False, indent=2)}
```

## Required Evidence

- Native tests: `{verify.get("native_tests", False)}`
- Build required: `{verify.get("require_build", False)}`
- Security scan: `{verify.get("require_security_scan", False)}`
- Link/source consistency: `{verify.get("require_link_check", verify.get("require_source_consistency", False))}`

## Evidence Log

- Pending. Run implementation checks after code changes.
"""
    safe_write(plan, content, force, actions)


def write_memory_plan(target: Path, request: ManagedRequest, force: bool, actions: list[str]) -> None:
    memory_dir = request.memory_path if request.memory_path.suffix == "" else request.memory_path.parent
    path = memory_dir / "current-request-memory.md"
    content = f"""# Memory Plan: {request.name}

## Policy

```json
{json.dumps(request.memory_params, ensure_ascii=False, indent=2)}
```

## Candidate Writes

- Project rule: only if this request reveals a durable rule.
- Module map: only if ownership or dependency boundaries are confirmed.
- Pitfall: only if a real failure pattern is observed.

## Evidence Required

Do not write memory from assumptions. Link to spec, PR, logs, tests, or review notes.
"""
    safe_write(path, content, force, actions)


def run_script_if_available(name: str, target: Path, actions: list[str]) -> None:
    script = skill_script(name)
    if not script:
        actions.append(f"skip missing script: {name}")
        return
    result = subprocess.run([sys.executable, str(script), str(target)], text=True, capture_output=True)
    if result.returncode == 0:
        actions.append(f"ok: {name}")
    else:
        actions.append(f"failed: {name}: {result.stderr.strip() or result.stdout.strip()}")


def write_execution_report(target: Path, request: ManagedRequest, actions: list[str], force: bool) -> Path:
    report = target / "docs" / "ai-engineering" / "execution-report.md"
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content = [
        f"# Execution Report: {request.name}",
        "",
        f"Created: {now}",
        "",
        "## Request",
        "",
        f"- Request: `{rel(request.path, target)}`",
        f"- Task: `{request.task}`",
        f"- Preset: `{request.preset}`",
        f"- Risk: `{request.risk}`",
        f"- Execute implementation now: `{str(request.execute).lower()}`",
        "",
        "## Safe Actions",
        "",
    ]
    content.extend(f"- {action}" for action in actions)
    content.extend([
        "",
        "## Next Human/Agent Step",
        "",
        "Review the generated spec, loop, and verify plan. Implementation may start only after the spec and loop are accepted.",
    ])
    safe_write(report, "\n".join(content), force=True if force else True, actions=[])
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", help="Target project path.")
    parser.add_argument("--request", help="Managed request path. Defaults to docs/ai-engineering/current-request.md.")
    parser.add_argument("--force", action="store_true", help="Overwrite generated artifacts.")
    parser.add_argument("--skip-init", action="store_true", help="Do not run init_project.py or inspect_project.py.")
    parser.add_argument(
        "--run-tools",
        action="store_true",
        help="Reserved for future safe tool execution. Current version only writes setup artifacts.",
    )
    args = parser.parse_args()

    target = Path(args.target).expanduser().resolve()
    if not target.exists() or not target.is_dir():
        raise SystemExit(f"Target project does not exist: {target}")

    request_path = Path(args.request).expanduser().resolve() if args.request else target / "docs" / "ai-engineering" / "current-request.md"
    request = parse_request(target, request_path)

    actions: list[str] = []
    if not args.skip_init:
        run_script_if_available("init_project.py", target, actions)
        run_script_if_available("inspect_project.py", target, actions)

    write_requirements_index(target, request, args.force, actions)
    write_spec(target, request, args.force, actions)
    write_loop(target, request, args.force, actions)
    write_verify_artifacts(target, request, args.force, actions)
    write_memory_plan(target, request, args.force, actions)

    if args.run_tools:
        actions.append("skip tools: no external safe tool runner is enabled in this version")

    report = write_execution_report(target, request, actions, args.force)
    print(f"executed safe request setup: {request.name}")
    print(f"report: {report}")
    for action in actions:
        print(action)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
