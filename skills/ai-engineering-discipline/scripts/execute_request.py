#!/usr/bin/env python3
"""Execute safe setup steps from docs/ai-engineering/current-request.md."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATED = "<!-- ai-engineering:generated -->"
DEFAULT_TIMEOUT_SECONDS = 600
OUTPUT_LIMIT = 12000


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


@dataclass
class CommandResult:
    name: str
    command: list[str]
    status: str
    exit_code: int | None
    duration_seconds: float
    stdout: str
    stderr: str
    output_path: str | None = None


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


def target_project_path(target: Path, raw: str, label: str) -> Path:
    target_root = target.resolve()
    path = Path(raw).expanduser()
    candidate = path if path.is_absolute() else target_root / path
    candidate = candidate.resolve()
    if candidate != target_root and not candidate.is_relative_to(target_root):
        raise SystemExit(f"{label} must stay inside target project: {candidate}")
    return candidate


def parse_bullet_paths(section: str, target: Path) -> list[Path]:
    paths: list[Path] = []
    for match in re.finditer(r"^- `([^`]+)`\s*$", section, flags=re.MULTILINE):
        raw = match.group(1)
        if raw == "None":
            continue
        paths.append(target_project_path(target, raw, "Requirement source"))
    return paths


def target_artifact_path(target: Path, raw: str, label: str) -> Path:
    return target_project_path(target, raw, f"{label} artifact")


def parse_request(target: Path, request_path: Path) -> ManagedRequest:
    if not request_path.exists():
        raise SystemExit(f"Managed request not found: {request_path}")
    text = request_path.read_text(encoding="utf-8")
    task_section = extract_section(text, "Task")
    requirements_section = extract_section(text, "Requirement Sources")
    artifacts_section = extract_section(text, "Target Artifacts")

    def artifact(label: str, default: str) -> Path:
        raw = parse_bullet_value(artifacts_section, label) or default
        return target_artifact_path(target, raw, label)

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


def write_json_artifact(path: Path, payload: dict[str, object], actions: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"generated_by": "ai-engineering-discipline", **payload}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
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
- Optional structured results: `docs/verify/verification-results.json`
- Optional readable results: `docs/verify/verification-results.md`
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


def truncate_output(value: str, limit: int = OUTPUT_LIMIT) -> str:
    if len(value) <= limit:
        return value
    return value[:limit].rstrip() + "\n[truncated]"


def command_to_text(command: list[str]) -> str:
    return " ".join(command) if command else "none"


def command_available(command: list[str], target: Path) -> bool:
    if not command:
        return False
    executable = command[0]
    if executable.startswith("./"):
        return (target / executable[2:]).exists()
    return shutil.which(executable) is not None


def run_command(name: str, command: list[str], target: Path, timeout: int) -> CommandResult:
    started = dt.datetime.now()
    if not command_available(command, target):
        return CommandResult(
            name=name,
            command=command,
            status="skipped",
            exit_code=None,
            duration_seconds=0.0,
            stdout="",
            stderr=f"Command not available: {command[0] if command else '<empty>'}",
        )
    try:
        result = subprocess.run(
            command,
            cwd=target,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        duration = (dt.datetime.now() - started).total_seconds()
        return CommandResult(
            name=name,
            command=command,
            status="passed" if result.returncode == 0 else "failed",
            exit_code=result.returncode,
            duration_seconds=round(duration, 3),
            stdout=truncate_output(result.stdout),
            stderr=truncate_output(result.stderr),
        )
    except subprocess.TimeoutExpired as exc:
        duration = (dt.datetime.now() - started).total_seconds()
        return CommandResult(
            name=name,
            command=command,
            status="timeout",
            exit_code=None,
            duration_seconds=round(duration, 3),
            stdout=truncate_output(exc.stdout or ""),
            stderr=truncate_output(exc.stderr or f"Timed out after {timeout} seconds."),
        )


def detect_native_commands(target: Path, request: ManagedRequest) -> list[tuple[str, list[str]]]:
    commands: list[tuple[str, list[str]]] = []
    package_json = target / "package.json"
    if package_json.exists():
        try:
            data = json.loads(package_json.read_text(encoding="utf-8"))
            scripts = data.get("scripts", {})
            if isinstance(scripts, dict):
                for name in ["lint", "typecheck", "test"]:
                    if name in scripts:
                        commands.append((f"npm:{name}", ["npm", "run", name]))
                if request.verify_params.get("require_build") and "build" in scripts:
                    commands.append(("npm:build", ["npm", "run", "build"]))
        except json.JSONDecodeError:
            commands.append(("npm:test", ["npm", "test"]))

    if (target / "go.mod").exists():
        commands.append(("go:test", ["go", "test", "./..."]))

    if (target / "pyproject.toml").exists() or (target / "requirements.txt").exists() or (target / "pytest.ini").exists():
        commands.append(("python:pytest", ["pytest"]))

    if (target / "Cargo.toml").exists():
        commands.append(("rust:cargo-test", ["cargo", "test"]))

    if (target / "pom.xml").exists():
        commands.append(("java:mvn-test", ["mvn", "test"]))

    if (target / "build.gradle").exists() or (target / "build.gradle.kts").exists():
        if (target / "gradlew").exists():
            commands.append(("java:gradle-test", ["./gradlew", "test"]))
        else:
            commands.append(("java:gradle-test", ["gradle", "test"]))

    return commands


def semgrep_command(request: ManagedRequest) -> list[str]:
    config = request.verify_params.get("semgrep_config", "auto")
    if not isinstance(config, str) or not config:
        config = "auto"
    return ["semgrep", "scan", "--config", config, "--json", "."]


def parse_semgrep_summary(raw_output: str) -> dict[str, object]:
    try:
        data = json.loads(raw_output) if raw_output.strip() else {}
    except json.JSONDecodeError:
        return {"parse_error": True, "findings": 0, "errors": 0, "severity_counts": {}}
    results = data.get("results", []) if isinstance(data, dict) else []
    errors = data.get("errors", []) if isinstance(data, dict) else []
    severity_counts: dict[str, int] = {}
    if isinstance(results, list):
        for item in results:
            if not isinstance(item, dict):
                continue
            extra = item.get("extra", {})
            severity = "unknown"
            if isinstance(extra, dict):
                severity = str(extra.get("severity", "unknown")).lower()
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
    return {
        "parse_error": False,
        "findings": len(results) if isinstance(results, list) else 0,
        "errors": len(errors) if isinstance(errors, list) else 0,
        "severity_counts": severity_counts,
    }


def run_semgrep(target: Path, request: ManagedRequest, timeout: int, actions: list[str]) -> CommandResult:
    result = run_command("semgrep", semgrep_command(request), target, timeout)
    output_file = target / "docs" / "verify" / "semgrep-results.json"
    if result.status in {"passed", "failed"} and result.stdout.strip():
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(result.stdout, encoding="utf-8")
        result.output_path = rel(output_file, target)
        actions.append(f"write: {output_file}")
    return result


def result_to_dict(result: CommandResult) -> dict[str, object]:
    return {
        "name": result.name,
        "command": result.command,
        "status": result.status,
        "exit_code": result.exit_code,
        "duration_seconds": result.duration_seconds,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "output_path": result.output_path,
    }


def write_verification_results(
    target: Path,
    request: ManagedRequest,
    semgrep: CommandResult | None,
    native: list[CommandResult],
    actions: list[str],
) -> None:
    if semgrep is None and not native:
        return
    verify_dir = target / "docs" / "verify"
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    semgrep_summary = parse_semgrep_summary(semgrep.stdout) if semgrep else None
    payload: dict[str, object] = {
        "created": now,
        "request": {
            "name": request.name,
            "task": request.task,
            "preset": request.preset,
            "risk": request.risk,
        },
        "semgrep": result_to_dict(semgrep) if semgrep else None,
        "semgrep_summary": semgrep_summary,
        "native_checks": [result_to_dict(item) for item in native],
    }
    write_json_artifact(verify_dir / "verification-results.json", payload, actions)

    lines = [
        f"# Verification Results: {request.name}",
        "",
        f"Created: {now}",
        "",
        "## Summary",
        "",
        "| Check | Status | Exit | Duration |",
        "|---|---|---|---|",
    ]
    if semgrep:
        lines.append(f"| semgrep | {semgrep.status} | {semgrep.exit_code if semgrep.exit_code is not None else ''} | {semgrep.duration_seconds}s |")
    for item in native:
        lines.append(f"| {item.name} | {item.status} | {item.exit_code if item.exit_code is not None else ''} | {item.duration_seconds}s |")
    if semgrep_summary:
        lines.extend([
            "",
            "## Semgrep Summary",
            "",
            f"- Command: `{command_to_text(semgrep.command) if semgrep else ''}`",
            f"- Status: `{semgrep.status if semgrep else ''}`",
            f"- Findings: `{semgrep_summary.get('findings')}`",
            f"- Errors: `{semgrep_summary.get('errors')}`",
            f"- Severity counts: `{json.dumps(semgrep_summary.get('severity_counts', {}), ensure_ascii=False)}`",
        ])
        if semgrep and semgrep.output_path:
            lines.append(f"- Raw JSON: `{semgrep.output_path}`")
        if semgrep and semgrep.stderr:
            lines.extend([
                "",
                "```text",
                semgrep.stderr.strip(),
                "```",
            ])
    lines.extend(["", "## Native Check Commands", ""])
    if native:
        for item in native:
            lines.extend([
                f"### {item.name}",
                "",
                f"- Command: `{command_to_text(item.command)}`",
                f"- Status: `{item.status}`",
                f"- Exit code: `{item.exit_code if item.exit_code is not None else ''}`",
                "",
                "Stdout:",
                "",
                "```text",
                (item.stdout or "No stdout.").strip(),
                "```",
                "",
                "Stderr:",
                "",
                "```text",
                (item.stderr or "No stderr.").strip(),
                "```",
                "",
            ])
    else:
        lines.append("- None run.")
    safe_write(verify_dir / "verification-results.md", "\n".join(lines), force=True, actions=actions)

    plan = verify_dir / "current-request-verify.md"
    if plan.exists():
        plan_text = plan.read_text(encoding="utf-8")
        summary_line = f"- Structured results written at `{now}`: `docs/verify/verification-results.json`, `docs/verify/verification-results.md`"
        if summary_line not in plan_text:
            plan.write_text(plan_text.rstrip() + "\n" + summary_line + "\n", encoding="utf-8")
            actions.append(f"update: {plan}")


def verification_rollup(semgrep: CommandResult | None, native: list[CommandResult]) -> tuple[str, str]:
    results = ([semgrep] if semgrep else []) + native
    if not results:
        return "pending", "No verification command was run."
    if any(item.status in {"failed", "timeout"} for item in results):
        return "blocked", "At least one verification command failed or timed out."
    if any(item.status == "skipped" for item in results):
        return "pending", "At least one requested verification command was skipped or unavailable."
    if semgrep:
        summary = parse_semgrep_summary(semgrep.stdout)
        if summary.get("findings", 0) or summary.get("errors", 0):
            return "blocked", "Semgrep reported findings or scan errors."
    if any(item.status == "passed" for item in results):
        return "verified", "All executed verification commands passed."
    return "pending", "Verification commands were skipped or unavailable."


def update_test_matrix_with_results(
    target: Path,
    request: ManagedRequest,
    semgrep: CommandResult | None,
    native: list[CommandResult],
    actions: list[str],
) -> None:
    if semgrep is None and not native:
        return
    matrix_path = request.verify_matrix_path
    if matrix_path.exists():
        existing = matrix_path.read_text(encoding="utf-8")
        if GENERATED not in existing:
            actions.append(f"skip human file: {matrix_path}")
            return

    status, reason = verification_rollup(semgrep, native)
    rows = []
    for idx, source in enumerate(request.requirements or [Path("none")], start=1):
        requirement = requirement_title(source) if source != Path("none") else request.name
        rows.append(f"| R{idx} | {requirement} | TBD | TBD | See verification evidence below | {status} |")

    evidence_rows = []
    if semgrep:
        evidence_rows.append(
            f"| semgrep | `{command_to_text(semgrep.command)}` | {semgrep.status} | {semgrep.exit_code if semgrep.exit_code is not None else ''} |"
        )
    for item in native:
        evidence_rows.append(
            f"| {item.name} | `{command_to_text(item.command)}` | {item.status} | {item.exit_code if item.exit_code is not None else ''} |"
        )

    content = f"""# Test Matrix

Request: `{request.name}`
Spec: `{rel(request.spec_path, target)}`

| Requirement ID | Requirement | Unit Test | Integration Test | Manual / Release Check | Status |
|---|---|---|---|---|---|
{chr(10).join(rows)}

## Verification Evidence

Status: `{status}`

Reason: {reason}

| Check | Command | Status | Exit |
|---|---|---|---|
{chr(10).join(evidence_rows) if evidence_rows else "| None |  | pending |  |"}

Structured results:

- `docs/verify/verification-results.json`
- `docs/verify/verification-results.md`
"""
    safe_write(matrix_path, content, force=True, actions=actions)


def has_verify_failure(semgrep: CommandResult | None, native: list[CommandResult]) -> bool:
    results = ([semgrep] if semgrep else []) + native
    return any(item.status in {"failed", "timeout"} for item in results)


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
        "Review the generated spec, loop, verify plan, and any structured verification results. Implementation may start only after the spec and loop are accepted.",
    ])
    safe_write(report, "\n".join(content), force=True if force else True, actions=[])
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", help="Target project path.")
    parser.add_argument("--request", help="Managed request path. Defaults to docs/ai-engineering/current-request.md.")
    parser.add_argument("--force", action="store_true", help="Overwrite generated artifacts.")
    parser.add_argument("--skip-init", action="store_true", help="Do not run init_project.py or inspect_project.py.")
    parser.add_argument("--run-semgrep", action="store_true", help="Run Semgrep and write structured results to docs/verify/.")
    parser.add_argument("--run-native-checks", action="store_true", help="Run detected native test/lint/typecheck/build commands.")
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS, help="Timeout per verification command.")
    parser.add_argument("--fail-on-verify-failure", action="store_true", help="Exit non-zero after writing results if any verification command fails or times out.")
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

    semgrep_result = None
    native_results: list[CommandResult] = []
    if args.run_semgrep:
        semgrep_result = run_semgrep(target, request, args.timeout_seconds, actions)
        actions.append(f"verify semgrep: {semgrep_result.status}")
    if args.run_native_checks:
        native_commands = detect_native_commands(target, request)
        if native_commands:
            for name, command in native_commands:
                result = run_command(name, command, target, args.timeout_seconds)
                native_results.append(result)
                actions.append(f"verify {name}: {result.status}")
        else:
            native_results.append(
                CommandResult(
                    name="native:detect",
                    command=[],
                    status="skipped",
                    exit_code=None,
                    duration_seconds=0.0,
                    stdout="",
                    stderr="No recognized native verification commands.",
                )
            )
            actions.append("verify native: skipped no recognized commands")
    write_verification_results(target, request, semgrep_result, native_results, actions)
    update_test_matrix_with_results(target, request, semgrep_result, native_results, actions)

    report = write_execution_report(target, request, actions, args.force)
    print(f"executed safe request setup: {request.name}")
    print(f"report: {report}")
    for action in actions:
        print(action)
    if args.fail_on_verify_failure and has_verify_failure(semgrep_result, native_results):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
