#!/usr/bin/env python3
"""Unified CLI for the AI Engineering Discipline workflow."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATED = "<!-- ai-engineering:generated -->"


def path_is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


def rel(path: Path, target: Path) -> str:
    try:
        return str(path.relative_to(target))
    except ValueError:
        return str(path)


def script_path(name: str) -> Path:
    candidates = [
        Path(__file__).resolve().parent / name,
        ROOT / "scripts" / name,
        ROOT / "skills" / "ai-engineering-discipline" / "scripts" / name,
        ROOT / ".claude" / "skills" / "ai-engineering-discipline" / "scripts" / name,
        ROOT / ".codex" / "skills" / "ai-engineering-discipline" / "scripts" / name,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise SystemExit(f"Cannot locate required script: {name}")


def run_python(script: Path, args: list[str]) -> int:
    command = [sys.executable, str(script), *args]
    print("run:", " ".join(command))
    return subprocess.run(command).returncode


def ensure_target(raw: str | None) -> Path:
    target = Path(raw or ".").expanduser().resolve()
    if not target.exists() or not target.is_dir():
        raise SystemExit(f"Target project does not exist: {target}")
    return target


def target_from_args(args: argparse.Namespace) -> Path:
    return ensure_target(getattr(args, "target", None) or getattr(args, "project", None))


def read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"parse_error": True}
    return data if isinstance(data, dict) else {}


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def extract_bullet_value(text: str, label: str) -> str:
    pattern = rf"^- {re.escape(label)}:\s*`?([^`\n]+)`?\s*$"
    match = re.search(pattern, text, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def current_request_summary(target: Path) -> dict[str, object]:
    path = target / "docs" / "ai-engineering" / "current-request.md"
    text = read_text(path)
    if not text:
        return {"exists": False, "path": rel(path, target)}
    return {
        "exists": True,
        "path": rel(path, target),
        "task": extract_bullet_value(text, "Type"),
        "name": extract_bullet_value(text, "Name"),
        "preset": extract_bullet_value(text, "Preset"),
        "risk": extract_bullet_value(text, "Risk"),
        "execute": extract_bullet_value(text, "Execute implementation now"),
    }


def count_generated_actions(target: Path) -> int:
    report = read_text(target / "docs" / "ai-engineering" / "execution-report.md")
    if not report:
        return 0
    return sum(1 for line in report.splitlines() if line.startswith("- write:") or line.startswith("- update:"))


def git_changed_files(target: Path) -> int | None:
    if not (target / ".git").exists():
        return None
    try:
        result = subprocess.run(
            ["git", "-C", str(target), "status", "--short"],
            text=True,
            capture_output=True,
        )
    except FileNotFoundError:
        return None
    if result.returncode != 0:
        return None
    return len([line for line in result.stdout.splitlines() if line.strip()])


def artifact_exists(target: Path, rel_path: str) -> bool:
    return (target / rel_path).exists()


def build_report_payload(target: Path) -> dict[str, object]:
    request = current_request_summary(target)
    verify = read_json(target / "docs" / "verify" / "verification-results.json")
    changed_files = git_changed_files(target)
    required_checks = verify.get("required_checks", [])
    skipped_checks = verify.get("skipped_required_checks", [])
    blocking_reasons = verify.get("blocking_reasons", [])
    native_checks = verify.get("native_checks", [])
    executed_checks = verify.get("executed_checks", [])
    memory_candidates = read_text(target / "docs" / "memory" / "memory-candidates.md")
    loop_run = read_text(target / "docs" / "loops" / "current-loop-run.md")

    artifacts = {
        "current_request": artifact_exists(target, "docs/ai-engineering/current-request.md"),
        "execution_report": artifact_exists(target, "docs/ai-engineering/execution-report.md"),
        "loop_run": artifact_exists(target, "docs/loops/current-loop-run.md"),
        "memory_candidates": artifact_exists(target, "docs/memory/memory-candidates.md"),
        "verification_json": artifact_exists(target, "docs/verify/verification-results.json"),
        "verification_markdown": artifact_exists(target, "docs/verify/verification-results.md"),
        "test_matrix": artifact_exists(target, "docs/verify/test-matrix.md"),
    }
    return {
        "created": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "target": str(target),
        "request": request,
        "artifacts": artifacts,
        "metrics": {
            "generated_or_updated_artifacts": count_generated_actions(target),
            "git_changed_files": changed_files,
            "required_check_count": len(required_checks) if isinstance(required_checks, list) else 0,
            "executed_check_count": len(executed_checks) if isinstance(executed_checks, list) else 0,
            "native_check_count": len(native_checks) if isinstance(native_checks, list) else 0,
            "skipped_required_check_count": len(skipped_checks) if isinstance(skipped_checks, list) else 0,
            "blocking_reason_count": len(blocking_reasons) if isinstance(blocking_reasons, list) else 0,
            "memory_candidate_sections": memory_candidates.count("## Candidate"),
            "loop_states_recorded": sum(1 for state in ["load_context", "plan", "implement", "verify", "memory", "done"] if state in loop_run),
        },
        "verification": {
            "overall_status": verify.get("overall_status", "missing"),
            "overall_reason": verify.get("overall_reason", "No structured verification result found."),
            "can_merge": verify.get("can_merge", False),
            "required_checks": required_checks,
            "skipped_required_checks": skipped_checks,
            "blocking_reasons": blocking_reasons,
        },
    }


def write_pilot_report(target: Path) -> Path:
    payload = build_report_payload(target)
    report_dir = target / "docs" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / "pilot-report.json"
    md_path = report_dir / "pilot-report.md"
    json_path.write_text(json.dumps({"generated_by": "ai-engineering-discipline", **payload}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    metrics = payload["metrics"]
    verification = payload["verification"]
    request = payload["request"]
    artifacts = payload["artifacts"]
    lines = [
        "# Pilot Report",
        "",
        f"Created: {payload['created']}",
        f"Target: `{payload['target']}`",
        "",
        "## Request",
        "",
        f"- Exists: `{str(request.get('exists', False)).lower()}`",
        f"- Name: `{request.get('name', '') or 'unknown'}`",
        f"- Task: `{request.get('task', '') or 'unknown'}`",
        f"- Preset: `{request.get('preset', '') or 'unknown'}`",
        f"- Risk: `{request.get('risk', '') or 'unknown'}`",
        "",
        "## Outcome",
        "",
        f"- Verification status: `{verification['overall_status']}`",
        f"- Can merge: `{str(verification['can_merge']).lower()}`",
        f"- Reason: {verification['overall_reason']}",
        f"- Skipped required checks: `{', '.join(verification['skipped_required_checks']) if verification['skipped_required_checks'] else 'none'}`",
        f"- Blocking reasons: `{', '.join(verification['blocking_reasons']) if verification['blocking_reasons'] else 'none'}`",
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    for key, value in metrics.items():
        lines.append(f"| {key} | {value if value is not None else 'n/a'} |")
    lines.extend([
        "",
        "## Artifact Coverage",
        "",
        "| Artifact | Present |",
        "|---|---|",
    ])
    for key, value in artifacts.items():
        lines.append(f"| {key} | `{str(value).lower()}` |")
    lines.extend([
        "",
        "## Interpretation",
        "",
        "- This report measures whether the workflow produced inspectable engineering evidence.",
        "- `can_merge=true` requires passing verification and no skipped required checks.",
        "- Missing verification means the framework prepared the workflow, but did not prove implementation readiness.",
        "",
        f"Structured data: `{rel(json_path, target)}`",
    ])
    md_path.write_text(GENERATED + "\n" + "\n".join(lines) + "\n", encoding="utf-8")
    return md_path


def command_start(args: argparse.Namespace) -> int:
    target = target_from_args(args)
    init_args = [str(target)]
    inspect_args = [str(target)]
    if args.force:
        init_args.append("--force")
    code = run_python(script_path("init_project.py"), init_args)
    if code != 0:
        return code
    code = run_python(script_path("inspect_project.py"), inspect_args)
    if code != 0:
        return code
    return run_python(script_path("doctor.py"), [str(target)])


def command_request(args: argparse.Namespace) -> int:
    target = target_from_args(args)
    command_args = [str(target), "--task", args.task, "--name", args.name]
    if args.risk:
        command_args.extend(["--risk", args.risk])
    if args.preset:
        command_args.extend(["--preset", args.preset])
    for requirement in args.requirements or []:
        command_args.extend(["--requirements", requirement])
    if args.notes:
        command_args.extend(["--notes", args.notes])
    if args.execute:
        command_args.append("--execute")
    if args.skip_init:
        command_args.append("--skip-init")
    return run_python(script_path("run_request.py"), command_args)


def build_execute_args(args: argparse.Namespace, target: Path) -> list[str]:
    command_args = [str(target)]
    if getattr(args, "request", None):
        command_args.extend(["--request", args.request])
    if getattr(args, "force", False):
        command_args.append("--force")
    if getattr(args, "skip_init", False):
        command_args.append("--skip-init")
    run_semgrep = getattr(args, "run_semgrep", False) or getattr(args, "verify", False)
    run_native_checks = getattr(args, "run_native_checks", False) or getattr(args, "verify", False)
    if run_semgrep:
        command_args.append("--run-semgrep")
    if run_native_checks:
        command_args.append("--run-native-checks")
    if getattr(args, "fail_on_verify_failure", False):
        command_args.append("--fail-on-verify-failure")
    command_args.extend(["--timeout-seconds", str(getattr(args, "timeout_seconds", 600))])
    return command_args


def command_execute(args: argparse.Namespace) -> int:
    target = target_from_args(args)
    return run_python(script_path("execute_request.py"), build_execute_args(args, target))


def command_verify(args: argparse.Namespace) -> int:
    args.run_semgrep = True
    args.run_native_checks = True
    return command_execute(args)


def command_run(args: argparse.Namespace) -> int:
    target = target_from_args(args)
    request_code = command_request(args)
    if request_code != 0:
        return request_code
    execute_args = argparse.Namespace(**vars(args))
    execute_args.request = None
    execute_args.skip_init = True
    execute_code = run_python(script_path("execute_request.py"), build_execute_args(execute_args, target))
    report = write_pilot_report(target)
    print(f"wrote: {report}")
    return execute_code


def command_report(args: argparse.Namespace) -> int:
    target = target_from_args(args)
    report = write_pilot_report(target)
    print(f"wrote: {report}")
    return 0


def command_doctor(args: argparse.Namespace) -> int:
    target = target_from_args(args)
    command_args = [str(target)]
    if args.fail_on_error:
        command_args.append("--fail-on-error")
    return run_python(script_path("doctor.py"), command_args)


def add_common_project(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("target", nargs="?", help="Target project path. Defaults to current directory.")
    parser.add_argument("--project", default=".", help="Target project path. Defaults to current directory.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai-discipline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser("start", help="Initialize, inspect, and diagnose a target project.")
    add_common_project(start)
    start.add_argument("--force", action="store_true", help="Overwrite generated framework files during initialization.")
    start.set_defaults(func=command_start)

    request = subparsers.add_parser("request", help="Create a managed request from task, risk, and requirement files.")
    add_common_project(request)
    request.add_argument("--task", choices=["feature", "bugfix", "refactor", "migration", "docs", "verify", "memory"], required=True)
    request.add_argument("--name", required=True)
    request.add_argument("--risk", choices=["low", "medium", "high"])
    request.add_argument("--preset")
    request.add_argument("--requirements", action="append", default=[])
    request.add_argument("--notes", default="")
    request.add_argument("--execute", action="store_true")
    request.add_argument("--skip-init", action="store_true")
    request.set_defaults(func=command_request)

    run = subparsers.add_parser("run", help="Create a request, execute it, and write a pilot report.")
    add_common_project(run)
    run.add_argument("--task", choices=["feature", "bugfix", "refactor", "migration", "docs", "verify", "memory"], required=True)
    run.add_argument("--name", required=True)
    run.add_argument("--risk", choices=["low", "medium", "high"])
    run.add_argument("--preset")
    run.add_argument("--requirements", action="append", default=[])
    run.add_argument("--notes", default="")
    run.add_argument("--execute", action="store_true")
    run.add_argument("--skip-init", action="store_true")
    run.add_argument("--force", action="store_true")
    run.add_argument("--verify", action="store_true", help="Run Semgrep and native checks before writing the report.")
    run.add_argument("--run-semgrep", action="store_true")
    run.add_argument("--run-native-checks", action="store_true")
    run.add_argument("--timeout-seconds", type=int, default=600)
    run.add_argument("--fail-on-verify-failure", action="store_true")
    run.set_defaults(func=command_run)

    execute = subparsers.add_parser("execute", help="Generate workflow artifacts and optionally run checks.")
    add_common_project(execute)
    execute.add_argument("--request")
    execute.add_argument("--force", action="store_true")
    execute.add_argument("--skip-init", action="store_true")
    execute.add_argument("--run-semgrep", action="store_true")
    execute.add_argument("--run-native-checks", action="store_true")
    execute.add_argument("--timeout-seconds", type=int, default=600)
    execute.add_argument("--fail-on-verify-failure", action="store_true")
    execute.set_defaults(func=command_execute)

    verify = subparsers.add_parser("verify", help="Run native checks and Semgrep for the current request.")
    add_common_project(verify)
    verify.add_argument("--request")
    verify.add_argument("--force", action="store_true")
    verify.add_argument("--skip-init", action="store_true")
    verify.add_argument("--timeout-seconds", type=int, default=600)
    verify.add_argument("--fail-on-verify-failure", action="store_true")
    verify.set_defaults(func=command_verify)

    report = subparsers.add_parser("report", help="Write docs/reports/pilot-report.md and .json.")
    add_common_project(report)
    report.set_defaults(func=command_report)

    doctor = subparsers.add_parser("doctor", help="Diagnose framework installation.")
    add_common_project(doctor)
    doctor.add_argument("--fail-on-error", action="store_true")
    doctor.set_defaults(func=command_doctor)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
