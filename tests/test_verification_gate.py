"""verification gate 的关键分支单测。

verification_gate_details 是框架的核心门禁(~28 条退出路径),此前只有 smoke 端到端
走一条主路径。这里用真实临时 git 仓库,锁住几条最关键的分支决策,避免改门禁逻辑时
悄悄回归。pure 子函数(native_test_outcome)单独测,无需 git。
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import execute_request as er  # noqa: E402


def make_request(target: Path, task: str = "feature", verify_params=None) -> "er.ManagedRequest":
    """构造一个最小可用的 ManagedRequest(字段无默认值,必须全填)。"""
    return er.ManagedRequest(
        path=target / "docs" / "ai-engineering" / "current-request.md",
        target=target,
        task=task,
        name="t",
        execute=False,
        preset=task,
        risk="medium",
        change_base="",
        requirements=[],
        spec_path=target / "docs" / "specs" / "t.md",
        loop_path=target / "docs" / "loops" / "loop.md",
        verify_matrix_path=target / "docs" / "verify" / "test-matrix.md",
        memory_path=target / "docs" / "memory",
        spec_params={},
        loop_params={},
        verify_params=verify_params or {},
        memory_params={},
    )


def git(target: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(target), "-c", "user.email=t@t", "-c", "user.name=t", *args],
        check=True, capture_output=True, text=True,
    )


def init_repo_with_baseline(target: Path) -> None:
    git(target, "init", "-q")
    (target / "README.md").write_text("baseline\n", encoding="utf-8")
    git(target, "add", "-A")
    git(target, "commit", "-q", "-m", "baseline")


class NativeTestOutcomeTest(unittest.TestCase):
    def _r(self, name: str, status: str) -> "er.CommandResult":
        return er.CommandResult(name=name, command=[], status=status,
                                exit_code=0, duration_seconds=0.0, stdout="", stderr="")

    def test_passed_when_all_test_checks_pass(self):
        self.assertEqual(er.native_test_outcome([self._r("python:pytest", "passed")]), "passed")

    def test_failed_when_any_test_check_fails(self):
        self.assertEqual(
            er.native_test_outcome([self._r("python:pytest", "passed"), self._r("go:test", "failed")]),
            "failed",
        )

    def test_none_when_no_test_checks(self):
        # 只有 lint/build 这类非测试命令 → 不能宣称套件跑过
        self.assertEqual(er.native_test_outcome([self._r("python:ruff", "passed")]), "none")

    def test_skipped_test_is_not_passed(self):
        self.assertEqual(er.native_test_outcome([self._r("python:pytest", "skipped")]), "none")


class GateRepoBranchTest(unittest.TestCase):
    def _gate(self, request):
        return er.verification_gate_details(request, semgrep=None, native=[], diff_cov=None, impact=None)

    def test_non_git_target_blocks_test_coverage(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td)
            gate = self._gate(make_request(target))
            reasons = " | ".join(str(x) for x in gate["blocking_reasons"])
            self.assertIn("not a git repository", reasons)

    def test_code_changed_without_test_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td)
            init_repo_with_baseline(target)
            (target / "src").mkdir()
            # 改了业务代码,但没有任何测试文件(git add 让新文件按完整路径出现,
            # 否则整个未跟踪目录会被 git 折叠成 "src/" 而识别不到具体代码文件)
            (target / "src" / "widget.py").write_text(
                "def render(x):\n    return x + 1\n", encoding="utf-8"
            )
            git(target, "add", "-A")
            gate = self._gate(make_request(target))
            reasons = " | ".join(str(x) for x in gate["blocking_reasons"])
            self.assertIn("code changed without a matching test change", reasons)

    def test_code_with_matching_test_clears_that_block(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td)
            init_repo_with_baseline(target)
            (target / "src").mkdir()
            (target / "tests").mkdir()
            (target / "src" / "widget.py").write_text(
                "def render(x):\n    return x + 1\n", encoding="utf-8"
            )
            # 测试真引用改动符号 render
            (target / "tests" / "test_widget.py").write_text(
                "from src.widget import render\n\ndef test_render():\n    assert render(1) == 2\n",
                encoding="utf-8",
            )
            git(target, "add", "-A")
            gate = self._gate(make_request(target))
            reasons = " | ".join(str(x) for x in gate["blocking_reasons"])
            self.assertNotIn("code changed without a matching test change", reasons)


if __name__ == "__main__":
    unittest.main()
