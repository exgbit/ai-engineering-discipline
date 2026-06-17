#!/usr/bin/env python3
"""跨平台端到端冒烟测试:在临时项目里跑完整链路并断言关键产物。

纯 Python、无 shell 依赖,可在 macOS / Linux / Windows 上一致运行——CI 用三平台矩阵
跑它,把"应该跨平台"变成"每个平台都验证过"。

用法:python scripts/smoke_test.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "ai_discipline.py"


def run_cli(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        [sys.executable, str(CLI), *args],
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd else None,
    )
    return proc


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"SMOKE FAIL: {msg}")


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        target = Path(td) / "proj"
        target.mkdir()
        # 模拟一个带 node 子项目的 monorepo:根 + 一层子目录
        (target / "package.json").write_text(
            '{"name":"root","scripts":{"test":"echo ok"}}', encoding="utf-8"
        )
        (target / "service").mkdir()
        (target / "service" / "go.mod").write_text("module svc\n", encoding="utf-8")

        # 1) start:init + inspect + doctor
        r = run_cli("start", str(target))
        check(r.returncode == 0, f"start exit={r.returncode}\n{r.stderr}")
        check(
            (target / ".claude" / "skills" / "ai-engineering-discipline" / "SKILL.md").exists(),
            "Claude skill not installed",
        )
        check(
            (target / ".codex" / "skills" / "ai-engineering-discipline" / "SKILL.md").exists(),
            "Codex skill not installed",
        )

        # monorepo 子项目应被扫描进 project-scan
        scan = (target / "docs" / "memory" / "project-scan.md").read_text(encoding="utf-8")
        check("Subprojects" in scan and "service/" in scan, "subproject 'service' not scanned")

        # 2) run feature(不依赖 semgrep)
        r = run_cli(
            "run", str(target),
            "--task", "feature", "--name", "smoke",
            "--skip-init", "--no-run-semgrep", "--run-native-checks",
        )
        check(r.returncode == 0, f"run exit={r.returncode}\n{r.stderr}")

        # 3) 关键产物存在
        for rel in [
            "docs/specs/smoke.md",
            "docs/loops/feature-slice-loop.md",
            "docs/verify/verification-results.json",
            "docs/reports/pilot-report.json",
        ]:
            check((target / rel).exists(), f"missing artifact: {rel}")

        # 4) verify 结果可解析且口径完整
        vr = json.loads((target / "docs" / "verify" / "verification-results.json").read_text(encoding="utf-8"))
        for key in ("can_merge", "required_checks", "blocking_reasons"):
            check(key in vr, f"verification-results.json missing key: {key}")

    print(f"SMOKE OK on {sys.platform}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
