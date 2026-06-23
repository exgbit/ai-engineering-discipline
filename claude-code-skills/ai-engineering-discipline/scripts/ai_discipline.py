#!/usr/bin/env python3
"""Unified CLI for the AI Engineering Discipline workflow."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import re
import subprocess
import sys
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATED = "<!-- ai-engineering:generated -->"
CONFIG_NAME = ".ai-discipline.json"
DEFAULT_CONFIG: dict[str, object] = {
    "version": 1,
    "defaults": {
        "verify": False,
        "run_semgrep": False,
        "run_native_checks": False,
        "fail_on_verify_failure": False,
        "timeout_seconds": 600,
    },
    "reports": {
        "write_pilot_report": True,
        "archive_runs": True,
    },
}


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


def parse_bool(value: object, fallback: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "no", "n", "off"}:
            return False
        return fallback
    if value is None:
        return fallback
    return bool(value)


def safe_int(value: object, fallback: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(str(value)))
        except (TypeError, ValueError):
            return fallback


def safe_float(value: object, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def safe_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def md_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def merge_dicts(base: dict[str, object], override: dict[str, object]) -> dict[str, object]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_dicts(merged[key], value)  # type: ignore[arg-type]
        else:
            merged[key] = deepcopy(value)
    return merged


SKIP_SCAN_DIRS = {
    "node_modules", "vendor", "dist", "build", "target",
    ".git", ".venv", "venv", "__pycache__", ".tox",
}


def discover_report_dirs(path: Path) -> list[Path]:
    report_dirs: set[Path] = set()
    if path.is_dir():
        if path.name == "reports":
            report_dirs.add(path.resolve())
        direct = path / "docs" / "reports"
        if direct.is_dir():
            report_dirs.add(direct.resolve())
        # 只扫一层子项目(monorepo),不递归整棵树:避免命中 node_modules 等依赖里残留的
        # docs/reports 把无关数据当作 pilot 证据,也避免大仓全量递归变慢
        for child in sorted(path.iterdir()):
            if child.is_dir() and not child.name.startswith(".") and child.name not in SKIP_SCAN_DIRS:
                sub = child / "docs" / "reports"
                if sub.is_dir():
                    report_dirs.add(sub.resolve())
    return sorted(report_dirs)


def load_config(target: Path) -> dict[str, object]:
    path = target / CONFIG_NAME
    if not path.exists():
        return deepcopy(DEFAULT_CONFIG)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid {CONFIG_NAME}: {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise SystemExit(f"Invalid {CONFIG_NAME}: {path}: root value must be a JSON object.")
    return merge_dicts(DEFAULT_CONFIG, raw)


def config_defaults(target: Path) -> dict[str, object]:
    defaults = load_config(target).get("defaults", {})
    return defaults if isinstance(defaults, dict) else {}


def config_reports(target: Path) -> dict[str, object]:
    reports = load_config(target).get("reports", {})
    return reports if isinstance(reports, dict) else {}


def default_value(target: Path, key: str, fallback: object) -> object:
    return config_defaults(target).get(key, fallback)


def report_value(target: Path, key: str, fallback: object) -> object:
    return config_reports(target).get(key, fallback)


def resolved_bool(args: argparse.Namespace, target: Path, key: str, fallback: bool = False) -> bool:
    value = getattr(args, key, None)
    if value is None:
        return parse_bool(default_value(target, key, fallback), fallback)
    return parse_bool(value, fallback)


def resolved_timeout(args: argparse.Namespace, target: Path) -> int:
    value = getattr(args, "timeout_seconds", None)
    if value is None:
        value = default_value(target, "timeout_seconds", 600)
    try:
        return int(value)
    except (TypeError, ValueError):
        return 600


def resolved_report_archive(args: argparse.Namespace, target: Path) -> bool:
    value = getattr(args, "archive_runs", None)
    if value is None:
        return parse_bool(report_value(target, "archive_runs", True), True)
    return parse_bool(value, True)


def should_write_pilot_report(target: Path) -> bool:
    return parse_bool(report_value(target, "write_pilot_report", True), True)


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def extract_bullet_value(text: str, label: str) -> str:
    pattern = rf"^- {re.escape(label)}:\s*`?([^`\n]+)`?\s*$"
    match = re.search(pattern, text, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


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
    return "".join(result).strip("-") or "report"


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
    required_checks = safe_list(verify.get("required_checks", []))
    skipped_checks = safe_list(verify.get("skipped_required_checks", []))
    blocking_reasons = safe_list(verify.get("blocking_reasons", []))
    native_checks = safe_list(verify.get("native_checks", []))
    executed_checks = safe_list(verify.get("executed_checks", []))
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
            "executed_check_count": (
                sum(1 for c in executed_checks if not (isinstance(c, dict) and c.get("status") == "skipped"))
                if isinstance(executed_checks, list) else 0
            ),
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
            "coverage_complete": verify.get("coverage_complete", False),
            "required_checks": required_checks,
            "skipped_required_checks": skipped_checks,
            "uncovered_checks": safe_list(verify.get("uncovered_checks")),
            "needs_human_checks": safe_list(verify.get("needs_human_checks")),
            "blocking_reasons": blocking_reasons,
        },
    }


def write_pilot_report(target: Path, archive_runs: bool = True) -> Path:
    payload = build_report_payload(target)
    report_dir = target / "docs" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / "pilot-report.json"
    md_path = report_dir / "pilot-report.md"
    request = payload["request"]
    archive_json_path = None
    archive_md_path = None
    if archive_runs:
        run_dir = report_dir / "runs"
        run_dir.mkdir(parents=True, exist_ok=True)
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        name = slugify(str(request.get("name", "") or "report")) if isinstance(request, dict) else "report"
        archive_json_path = run_dir / f"pilot-report-{stamp}-{name}.json"
        archive_md_path = run_dir / f"pilot-report-{stamp}-{name}.md"
        suffix = 1
        while archive_json_path.exists() or archive_md_path.exists():
            archive_json_path = run_dir / f"pilot-report-{stamp}-{name}-{suffix}.json"
            archive_md_path = run_dir / f"pilot-report-{stamp}-{name}-{suffix}.md"
            suffix += 1

    full_payload = {"generated_by": "ai-engineering-discipline", **payload}
    if archive_json_path and archive_md_path:
        full_payload["archive"] = {
            "json": rel(archive_json_path, target),
            "markdown": rel(archive_md_path, target),
        }
    body = json.dumps(full_payload, ensure_ascii=False, indent=2) + "\n"
    json_path.write_text(body, encoding="utf-8")
    if archive_json_path:
        archive_json_path.write_text(body, encoding="utf-8")

    metrics = payload["metrics"]
    verification = payload["verification"]
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
        f"- Can merge (no blocking issues): `{str(verification['can_merge']).lower()}`",
        f"- Fully verified (all required checks covered): `{str(verification.get('coverage_complete', False)).lower()}`",
        f"- Reason: {verification['overall_reason']}",
        f"- Blocking reasons: `{', '.join(str(item) for item in safe_list(verification.get('blocking_reasons'))) or 'none'}`",
        f"- Uncovered required checks (tool missing / not run): `{', '.join(str(item) for item in safe_list(verification.get('uncovered_checks'))) or 'none'}`",
        f"- Needs human verification: `{', '.join(str(item) for item in safe_list(verification.get('needs_human_checks'))) or 'none'}`",
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
        "- This report is a snapshot from when it was written; the latest verification is in verification-results.json.",
        "- `can_merge=true` means no blocking issues (tests passed, no security findings, required docs filled).",
        "- `coverage_complete=true` means every required check actually ran and passed; if false, see the uncovered checks above.",
        "- Missing verification means the framework prepared the workflow, but did not prove implementation readiness.",
        "",
        f"Structured data: `{rel(json_path, target)}`",
    ])
    if archive_md_path:
        lines.append(f"- Archived copy: `{rel(archive_md_path, target)}`")
    markdown = GENERATED + "\n" + "\n".join(lines) + "\n"
    md_path.write_text(markdown, encoding="utf-8")
    if archive_md_path:
        archive_md_path.write_text(markdown, encoding="utf-8")
    return md_path


def find_pilot_reports(inputs: list[str], default_target: Path) -> list[Path]:
    raw_inputs = inputs or [str(default_target)]
    reports: list[Path] = []
    seen: set[Path] = set()
    for raw in raw_inputs:
        path = Path(raw).expanduser().resolve()
        candidates: list[Path] = []
        if path.is_file():
            candidates = [path]
        elif path.is_dir():
            report_dirs = discover_report_dirs(path)
            for report_dir in report_dirs:
                run_reports = sorted((report_dir / "runs").glob("pilot-report-*.json"))
                if run_reports:
                    candidates.extend(run_reports)
                    continue
                latest_report = report_dir / "pilot-report.json"
                if latest_report.is_file():
                    candidates.append(latest_report)
        for candidate in candidates:
            resolved = candidate.resolve()
            valid_report = resolved.name == "pilot-report.json" or (
                resolved.name.startswith("pilot-report-") and resolved.name.endswith(".json")
            )
            if resolved not in seen and valid_report:
                seen.add(resolved)
                reports.append(resolved)
    return sorted(reports)


def row_from_report(path: Path) -> dict[str, object]:
    data = read_json(path)
    request = data.get("request", {})
    metrics = data.get("metrics", {})
    verification = data.get("verification", {})
    artifacts = data.get("artifacts", {})
    if not isinstance(request, dict):
        request = {}
    if not isinstance(metrics, dict):
        metrics = {}
    if not isinstance(verification, dict):
        verification = {}
    if not isinstance(artifacts, dict):
        artifacts = {}
    artifact_count = len(artifacts)
    artifact_passed = sum(1 for value in artifacts.values() if parse_bool(value, False))
    return {
        "report": str(path),
        "created": data.get("created", ""),
        "target": data.get("target", ""),
        "task": request.get("task", ""),
        "name": request.get("name", ""),
        "risk": request.get("risk", ""),
        "verification_status": verification.get("overall_status", "missing"),
        "can_merge": parse_bool(verification.get("can_merge", False), False),
        "required_check_count": safe_int(metrics.get("required_check_count")),
        "executed_check_count": safe_int(metrics.get("executed_check_count")),
        "skipped_required_check_count": safe_int(metrics.get("skipped_required_check_count")),
        "blocking_reason_count": safe_int(metrics.get("blocking_reason_count")),
        "loop_states_recorded": safe_int(metrics.get("loop_states_recorded")),
        "memory_candidate_sections": safe_int(metrics.get("memory_candidate_sections")),
        "artifact_coverage": artifact_passed / artifact_count if artifact_count else 0.0,
    }


def pct(count: int, total: int) -> str:
    if total == 0:
        return "0.0%"
    return f"{(count / total) * 100:.1f}%"


def avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def write_metrics_summary(paths: list[Path], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = [row_from_report(path) for path in paths]
    total = len(rows)
    status_counts: dict[str, int] = {}
    for row in rows:
        status = str(row["verification_status"])
        status_counts[status] = status_counts.get(status, 0) + 1
    can_merge_count = sum(1 for row in rows if row["can_merge"])

    summary = {
        "generated_by": "ai-engineering-discipline",
        "created": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "report_count": total,
        "can_merge_count": can_merge_count,
        "can_merge_rate": can_merge_count / total if total else 0.0,
        "status_counts": status_counts,
        "averages": {
            "required_check_count": avg([float(row["required_check_count"]) for row in rows]),
            "executed_check_count": avg([float(row["executed_check_count"]) for row in rows]),
            "skipped_required_check_count": avg([float(row["skipped_required_check_count"]) for row in rows]),
            "blocking_reason_count": avg([float(row["blocking_reason_count"]) for row in rows]),
            "loop_states_recorded": avg([float(row["loop_states_recorded"]) for row in rows]),
            "artifact_coverage": avg([float(row["artifact_coverage"]) for row in rows]),
        },
        "reports": rows,
    }

    json_path = output_dir / "pilot-summary.json"
    csv_path = output_dir / "pilot-summary.csv"
    md_path = output_dir / "pilot-summary.md"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    fieldnames = [
        "report",
        "created",
        "target",
        "task",
        "name",
        "risk",
        "verification_status",
        "can_merge",
        "required_check_count",
        "executed_check_count",
        "skipped_required_check_count",
        "blocking_reason_count",
        "loop_states_recorded",
        "memory_candidate_sections",
        "artifact_coverage",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    lines = [
        "# Pilot Metrics Summary",
        "",
        f"Created: {summary['created']}",
        "",
        "## Summary",
        "",
        f"- Reports: `{total}`",
        f"- Can merge: `{can_merge_count}` ({pct(can_merge_count, total)})",
        "",
        "| Status | Count | Rate |",
        "|---|---:|---:|",
    ]
    for status, count in sorted(status_counts.items()):
        lines.append(f"| {status} | {count} | {pct(count, total)} |")
    lines.extend([
        "",
        "## Averages",
        "",
        "| Metric | Average |",
        "|---|---:|",
    ])
    for key, value in summary["averages"].items():
        numeric = safe_float(value)
        display = f"{numeric * 100:.1f}%" if key == "artifact_coverage" else f"{numeric:.2f}"
        lines.append(f"| {key} | {display} |")
    lines.extend([
        "",
        "## Reports",
        "",
        "| Request | Task | Risk | Status | Can Merge | Executed Checks | Skipped Required | Blocking Reasons |",
        "|---|---|---|---|---|---:|---:|---:|",
    ])
    for row in rows:
        lines.append(
            f"| {md_cell(row['name'] or 'unknown')} | {md_cell(row['task'] or 'unknown')} | "
            f"{md_cell(row['risk'] or 'unknown')} | {md_cell(row['verification_status'])} | `{str(row['can_merge']).lower()}` | "
            f"{row['executed_check_count']} | {row['skipped_required_check_count']} | {row['blocking_reason_count']} |"
        )
    lines.extend([
        "",
        "## Files",
        "",
        f"- JSON: `{json_path.name}`",
        f"- CSV: `{csv_path.name}`",
        "",
        "Use this as pilot evidence for workflow behavior. It does not measure product quality by itself.",
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
    # 新项目从头建知识图谱:装了就建初始图(best-effort,没装/失败不挡 start);后续每次 execute 增量刷新
    if not os.environ.get("AI_DISCIPLINE_GRAPH_OPTIONAL"):
        run_python(script_path("code_graph.py"), ["index", str(target)])
    return run_python(script_path("doctor.py"), [str(target)])


def command_request(args: argparse.Namespace) -> int:
    target = target_from_args(args)
    command_args = [str(target), "--task", args.task, "--name", args.name]
    risk = args.risk or str(default_value(target, "risk", "") or "")
    if risk:
        command_args.extend(["--risk", risk])
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
    verify_all = resolved_bool(args, target, "verify", False)

    def resolve_check(key: str) -> bool:
        # 显式 --run-x / --no-run-x 优先;未指定时才由 --verify 或 config 默认开启
        explicit = getattr(args, key, None)
        if explicit is not None:
            return parse_bool(explicit, False)
        return verify_all or resolved_bool(args, target, key, False)

    run_semgrep = resolve_check("run_semgrep")
    run_native_checks = resolve_check("run_native_checks")
    if run_semgrep:
        command_args.append("--run-semgrep")
    if run_native_checks:
        command_args.append("--run-native-checks")
    if getattr(args, "run_diff_coverage", False):
        command_args.append("--run-diff-coverage")
    if resolved_bool(args, target, "fail_on_verify_failure", False):
        command_args.append("--fail-on-verify-failure")
    command_args.extend(["--timeout-seconds", str(resolved_timeout(args, target))])
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
    if should_write_pilot_report(target):
        report = write_pilot_report(target, archive_runs=resolved_report_archive(args, target))
        print(f"wrote: {report}")
    else:
        print(f"skip report: {target / 'docs' / 'reports' / 'pilot-report.md'} (reports.write_pilot_report=false)")
    return execute_code


def command_report(args: argparse.Namespace) -> int:
    target = target_from_args(args)
    report = write_pilot_report(target, archive_runs=resolved_report_archive(args, target))
    print(f"wrote: {report}")
    return 0


def command_doctor(args: argparse.Namespace) -> int:
    target = target_from_args(args)
    command_args = [str(target)]
    if args.fail_on_error:
        command_args.append("--fail-on-error")
    return run_python(script_path("doctor.py"), command_args)


def write_default_config(target: Path, force: bool) -> tuple[Path, bool]:
    path = target / CONFIG_NAME
    if path.exists() and not force:
        return path, False
    path.write_text(json.dumps(DEFAULT_CONFIG, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path, True


def command_config(args: argparse.Namespace) -> int:
    target = target_from_args(args)
    if args.init:
        path, wrote = write_default_config(target, args.force)
        print(f"{'wrote' if wrote else 'exists'}: {path}")
        return 0
    config = load_config(target)
    print(json.dumps(config, ensure_ascii=False, indent=2))
    return 0


def command_metrics(args: argparse.Namespace) -> int:
    target = target_from_args(args)
    reports = find_pilot_reports(args.inputs, target)
    if not reports:
        raise SystemExit("No pilot-report.json files found.")
    output_dir = Path(args.output_dir).expanduser()
    if not output_dir.is_absolute():
        output_dir = target / output_dir
    path = write_metrics_summary(reports, output_dir.resolve())
    print(f"wrote: {path}")
    print(f"reports: {len(reports)}")
    return 0


def command_index(args: argparse.Namespace) -> int:
    target = target_from_args(args)
    return run_python(script_path("build_test_index.py"), [str(target)])


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
    run.add_argument("--verify", dest="verify", action="store_true", default=None, help="Run Semgrep and native checks before writing the report.")
    run.add_argument("--no-verify", dest="verify", action="store_false", help="Disable verification even if configured by default.")
    run.add_argument("--run-semgrep", dest="run_semgrep", action="store_true", default=None)
    run.add_argument("--no-run-semgrep", dest="run_semgrep", action="store_false")
    run.add_argument("--run-native-checks", dest="run_native_checks", action="store_true", default=None)
    run.add_argument("--no-run-native-checks", dest="run_native_checks", action="store_false")
    run.add_argument("--run-diff-coverage", dest="run_diff_coverage", action="store_true", default=False, help="diff-coverage: check changed lines are executed by tests (needs a coverage tool).")
    run.add_argument("--timeout-seconds", type=int)
    run.add_argument("--fail-on-verify-failure", dest="fail_on_verify_failure", action="store_true", default=None)
    run.add_argument("--no-fail-on-verify-failure", dest="fail_on_verify_failure", action="store_false")
    run.add_argument("--archive-runs", dest="archive_runs", action="store_true", default=None)
    run.add_argument("--no-archive-runs", dest="archive_runs", action="store_false")
    run.set_defaults(func=command_run)

    execute = subparsers.add_parser("execute", help="Generate workflow artifacts and optionally run checks.")
    add_common_project(execute)
    execute.add_argument("--request")
    execute.add_argument("--force", action="store_true")
    execute.add_argument("--skip-init", action="store_true")
    execute.add_argument("--verify", dest="verify", action="store_true", default=None, help="Run Semgrep and native checks.")
    execute.add_argument("--no-verify", dest="verify", action="store_false")
    execute.add_argument("--run-semgrep", dest="run_semgrep", action="store_true", default=None)
    execute.add_argument("--no-run-semgrep", dest="run_semgrep", action="store_false")
    execute.add_argument("--run-native-checks", dest="run_native_checks", action="store_true", default=None)
    execute.add_argument("--no-run-native-checks", dest="run_native_checks", action="store_false")
    execute.add_argument("--run-diff-coverage", dest="run_diff_coverage", action="store_true", default=False, help="diff-coverage: check changed lines are executed by tests (needs a coverage tool).")
    execute.add_argument("--timeout-seconds", type=int)
    execute.add_argument("--fail-on-verify-failure", dest="fail_on_verify_failure", action="store_true", default=None)
    execute.add_argument("--no-fail-on-verify-failure", dest="fail_on_verify_failure", action="store_false")
    execute.set_defaults(func=command_execute)

    verify = subparsers.add_parser("verify", help="Run native checks and Semgrep for the current request.")
    add_common_project(verify)
    verify.add_argument("--request")
    verify.add_argument("--force", action="store_true")
    verify.add_argument("--skip-init", action="store_true")
    verify.add_argument("--timeout-seconds", type=int)
    verify.add_argument("--fail-on-verify-failure", dest="fail_on_verify_failure", action="store_true", default=None)
    verify.add_argument("--no-fail-on-verify-failure", dest="fail_on_verify_failure", action="store_false")
    verify.set_defaults(func=command_verify)

    report = subparsers.add_parser("report", help="Write docs/reports/pilot-report.md and .json.")
    add_common_project(report)
    report.add_argument("--archive-runs", dest="archive_runs", action="store_true", default=None)
    report.add_argument("--no-archive-runs", dest="archive_runs", action="store_false")
    report.set_defaults(func=command_report)

    doctor = subparsers.add_parser("doctor", help="Diagnose framework installation.")
    add_common_project(doctor)
    doctor.add_argument("--fail-on-error", action="store_true")
    doctor.set_defaults(func=command_doctor)

    config = subparsers.add_parser("config", help="Show or initialize .ai-discipline.json.")
    add_common_project(config)
    config.add_argument("--init", action="store_true", help="Write default .ai-discipline.json.")
    config.add_argument("--force", action="store_true", help="Overwrite existing config when used with --init.")
    config.set_defaults(func=command_config)

    metrics = subparsers.add_parser("metrics", help="Aggregate pilot-report.json files into summary Markdown/JSON/CSV.")
    add_common_project(metrics)
    metrics.add_argument("--input", dest="inputs", action="append", default=[], help="Project directory or pilot-report.json. Can be passed multiple times.")
    metrics.add_argument("--output-dir", default="docs/reports", help="Directory for pilot-summary.md/.json/.csv. Relative paths resolve inside the target project.")
    metrics.set_defaults(func=command_metrics)

    index = subparsers.add_parser("index", help="Build/refresh docs/verify/test-index.{md,json}: code symbol -> guarding tests + untested blind spots.")
    add_common_project(index)
    index.set_defaults(func=command_index)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
