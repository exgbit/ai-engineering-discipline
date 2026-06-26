"""verification gate 的纯函数与若干 gate 分支的单测。

补齐此前只有 smoke 端到端走过、无单测的核心判定逻辑:verification_rollup、
parse_semgrep_summary、count_test_cases、refresh_matrix_row_statuses、
section_is_complete、is_test_check_name,以及 diff_cov / impact 两条 gate 分支
(直接喂 dict,无需真跑工具)。另测本轮新增的 fenced() 代码围栏安全。
"""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import execute_request as er  # noqa: E402


def cr(name: str, status: str, stdout: str = "", stderr: str = "") -> "er.CommandResult":
    return er.CommandResult(
        name=name, command=[], status=status, exit_code=0,
        duration_seconds=0.0, stdout=stdout, stderr=stderr,
    )


def make_request(target: Path, task: str = "docs", verify_params=None) -> "er.ManagedRequest":
    return er.ManagedRequest(
        path=target / "docs" / "ai-engineering" / "current-request.md",
        target=target, task=task, name="t", execute=False, preset=task, risk="medium",
        change_base="", requirements=[],
        spec_path=target / "docs" / "specs" / "t.md",
        loop_path=target / "docs" / "loops" / "loop.md",
        verify_matrix_path=target / "docs" / "verify" / "test-matrix.md",
        memory_path=target / "docs" / "memory",
        spec_params={}, loop_params={}, verify_params=verify_params or {}, memory_params={},
    )


class FencedTest(unittest.TestCase):
    def test_plain_text_uses_three_backticks(self):
        out = er.fenced("hello")
        self.assertTrue(out.startswith("```text\n"))
        self.assertTrue(out.endswith("\n```"))

    def test_content_with_fence_gets_longer_fence(self):
        # 内容自带 ``` → 外层围栏必须更长,否则提前闭合、破坏渲染
        content = "before\n```json\n{}\n```\nafter"
        out = er.fenced(content)
        self.assertTrue(out.startswith("````text\n"))  # 4 个反引号
        self.assertTrue(out.endswith("\n````"))
        # 原内容原样保留(没被吞)
        self.assertIn("```json", out)

    def test_longest_run_wins(self):
        out = er.fenced("a ```` b ``` c")  # 最长 4 个 → 围栏 5 个
        self.assertTrue(out.startswith("`````text\n"))


class VerificationRollupTest(unittest.TestCase):
    def test_nothing_run_is_pending(self):
        self.assertEqual(er.verification_rollup(None, [])[0], "pending")

    def test_failed_is_blocked(self):
        self.assertEqual(er.verification_rollup(None, [cr("python:pytest", "failed")])[0], "blocked")

    def test_skipped_is_pending(self):
        self.assertEqual(er.verification_rollup(None, [cr("python:pytest", "skipped")])[0], "pending")

    def test_semgrep_findings_block(self):
        semgrep = cr("semgrep", "passed", stdout='{"results":[{"extra":{"severity":"ERROR"}}],"errors":[]}')
        self.assertEqual(er.verification_rollup(semgrep, [cr("python:pytest", "passed")])[0], "blocked")

    def test_semgrep_parse_error_blocks(self):
        self.assertEqual(er.verification_rollup(cr("semgrep", "passed", stdout="not json"), [])[0], "blocked")

    def test_clean_semgrep_plus_passed_native_verified(self):
        semgrep = cr("semgrep", "passed", stdout='{"results":[],"errors":[]}')
        self.assertEqual(er.verification_rollup(semgrep, [cr("python:pytest", "passed")])[0], "verified")


class ParseSemgrepSummaryTest(unittest.TestCase):
    def test_counts_findings_and_severity(self):
        raw = '{"results":[{"extra":{"severity":"ERROR"}},{"extra":{"severity":"WARNING"}}],"errors":[]}'
        s = er.parse_semgrep_summary(raw)
        self.assertFalse(s["parse_error"])
        self.assertEqual(s["findings"], 2)
        self.assertEqual(s["errors"], 0)
        self.assertEqual(s["severity_counts"], {"error": 1, "warning": 1})

    def test_bad_json_flags_parse_error(self):
        s = er.parse_semgrep_summary("not json")
        self.assertTrue(s["parse_error"])
        self.assertEqual(s["findings"], 0)

    def test_empty_is_clean(self):
        s = er.parse_semgrep_summary("")
        self.assertFalse(s["parse_error"])
        self.assertEqual(s["findings"], 0)


class CountTestCasesTest(unittest.TestCase):
    def test_pytest_line(self):
        self.assertEqual(er.count_test_cases([cr("python:pytest", "passed", stdout="4 passed, 1 failed")]), (4, 1, True))

    def test_unittest_line(self):
        # "Ran 5 tests" + "failures=2" → passed=3, failed=2
        out = "Ran 5 tests in 0.1s\nFAILED (failures=2)"
        self.assertEqual(er.count_test_cases([cr("x:test", "failed", stdout=out)]), (3, 2, True))

    def test_unparsable_returns_parsed_false(self):
        self.assertEqual(er.count_test_cases([cr("x:test", "passed", stdout="all good")]), (0, 0, False))


class SectionCompleteTest(unittest.TestCase):
    def test_empty_incomplete(self):
        self.assertFalse(er.section_is_complete(""))

    def test_tbd_incomplete(self):
        self.assertFalse(er.section_is_complete("has TBD somewhere"))

    def test_unchecked_box_incomplete(self):
        self.assertFalse(er.section_is_complete("- [ ] not done"))

    def test_real_content_complete(self):
        self.assertTrue(er.section_is_complete("Affected modules: order service; regression: run pytest"))


class IsTestCheckNameTest(unittest.TestCase):
    def test_test_names(self):
        for n in ("python:pytest", "go:test", "python:unittest", "js:vitest-test", "java:gradle-test"):
            self.assertTrue(er.is_test_check_name(n), n)

    def test_non_test_names(self):
        for n in ("native:detect", "python:lint", "java:build", "ts:typecheck"):
            self.assertFalse(er.is_test_check_name(n), n)


class RefreshMatrixRowStatusesTest(unittest.TestCase):
    MATRIX = (
        "## Requirement Traceability\n\n"
        "| ID | Requirement | Status |\n"
        "|---|---|---|\n"
        "| R1 | do x | `red` |\n"
        "| R2 | do y | passed |\n\n"
        "## Notes\n\n"
        "| ID | Note | Status |\n"
        "|---|---|---|\n"
        "| N1 | n | todo |\n"
    )

    def test_passed_refreshes_target_section_only(self):
        out = er.refresh_matrix_row_statuses(self.MATRIX, "passed")
        self.assertIn("| R1 | do x | passed |", out)   # red → passed
        self.assertIn("| R2 | do y | passed |", out)   # 已 passed,不在可刷新集合,保持
        self.assertIn("| N1 | n | todo |", out)        # 不在目标 section,不动

    def test_non_terminal_outcome_is_noop(self):
        self.assertEqual(er.refresh_matrix_row_statuses(self.MATRIX, "none"), self.MATRIX)


class GateDiffCovAndImpactBranchTest(unittest.TestCase):
    def _gate(self, request, diff_cov=None, impact=None):
        return er.verification_gate_details(request, semgrep=None, native=[], diff_cov=diff_cov, impact=impact)

    def test_diff_cov_required_but_unavailable_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            req = make_request(Path(td), task="docs", verify_params={"require_diff_coverage": True})
            gate = self._gate(req, diff_cov={"available": False, "reason": "no tool"})
            reasons = " | ".join(str(x) for x in gate["blocking_reasons"])
            self.assertIn("diff-coverage unavailable", reasons)
            self.assertFalse(gate["can_merge"])

    def test_impact_untested_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            # feature 任务才会走 impact 分支;非 git 仓另会加自己的阻断,但我们只断言 impact 那条
            req = make_request(Path(td), task="feature")
            gate = self._gate(req, impact={"available": True, "impacted": ["foo"], "untested": ["foo"]})
            reasons = " | ".join(str(x) for x in gate["blocking_reasons"])
            self.assertIn("without a guarding test", reasons)


if __name__ == "__main__":
    unittest.main()
