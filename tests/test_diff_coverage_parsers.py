"""diff_coverage 跨语言覆盖率解析器的单测。

这些解析器是纯函数(吃报告文本/dict,吐 {relpath: (executed, executable)}),
用 fixture 即可完整验证,**无需安装 go/node/java 工具链**——正好补上 smoke 只建
Python/空壳项目、Go/JS/Java 解析路径零自动化覆盖的缺口。
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import diff_coverage as dc  # noqa: E402


class GoCoverprofileTest(unittest.TestCase):
    def test_executed_vs_executable(self):
        # `import-path/file.go:sl.sc,el.ec numstmt count`,count>0 = 被执行
        text = (
            "mode: set\n"
            "svc/order.go:10.20,12.5 2 1\n"   # 10-12 行,命中
            "svc/order.go:14.2,14.20 1 0\n"   # 14 行,可执行但未命中
        )
        cov = dc._parse_go_coverprofile(text)
        self.assertIn("svc/order.go", cov)
        ex, exe = cov["svc/order.go"]
        self.assertEqual(exe, {10, 11, 12, 14})
        self.assertEqual(ex, {10, 11, 12})

    def test_skips_mode_blank_and_malformed_lines(self):
        text = "mode: count\n\nnot-a-valid-line\nsvc/a.go:1.1,1.10 1 5\n"
        cov = dc._parse_go_coverprofile(text)
        self.assertEqual(set(cov), {"svc/a.go"})
        ex, exe = cov["svc/a.go"]
        self.assertEqual(ex, {1})
        self.assertEqual(exe, {1})


class IstanbulTest(unittest.TestCase):
    def test_statement_hits(self):
        data = {
            "src/order.js": {
                "statementMap": {
                    "0": {"start": {"line": 1}},
                    "1": {"start": {"line": 2}},
                    "2": {"start": {"line": 5}},
                },
                "s": {"0": 3, "1": 0, "2": 1},
            }
        }
        cov = dc._parse_istanbul(data, Path("/proj"))
        self.assertIn("src/order.js", cov)
        ex, exe = cov["src/order.js"]
        self.assertEqual(exe, {1, 2, 5})
        self.assertEqual(ex, {1, 5})

    def test_statement_without_start_line_is_skipped(self):
        data = {"src/a.js": {"statementMap": {"0": {}}, "s": {"0": 1}}}
        cov = dc._parse_istanbul(data, Path("/proj"))
        ex, exe = cov["src/a.js"]
        self.assertEqual(exe, set())
        self.assertEqual(ex, set())


class JacocoTest(unittest.TestCase):
    def test_ci_covered_mi_still_executable(self):
        xml = (
            '<report><package name="com/example">'
            '<sourcefile name="Order.java">'
            '<line nr="3" mi="0" ci="2"/>'   # 命中
            '<line nr="4" mi="1" ci="0"/>'   # 可执行未命中
            "</sourcefile></package></report>"
        )
        cov = dc._parse_jacoco(xml)
        self.assertIn("com/example/Order.java", cov)
        ex, exe = cov["com/example/Order.java"]
        self.assertEqual(exe, {3, 4})
        self.assertEqual(ex, {3})

    def test_package_without_name_uses_bare_filename(self):
        xml = (
            "<report><package>"
            '<sourcefile name="Root.java"><line nr="1" mi="0" ci="1"/></sourcefile>'
            "</package></report>"
        )
        cov = dc._parse_jacoco(xml)
        self.assertIn("Root.java", cov)


class MatchPathTest(unittest.TestCase):
    def test_suffix_match_with_module_prefix(self):
        covered = {"svc/order.go": ({1}, {1, 2})}
        self.assertEqual(dc._match_path(covered, "order.go"), ({1}, {1, 2}))

    def test_longest_match_wins(self):
        covered = {"order.go": ({1}, {1}), "deep/order.go": ({2}, {2})}
        # 两条都后缀匹配 order.go,取路径更长的那条,避免张冠李戴
        self.assertEqual(dc._match_path(covered, "order.go"), ({2}, {2}))

    def test_no_false_substring_match(self):
        # foobar.go 不能匹配 bar.go(按路径段边界,不是裸子串)
        covered = {"x/foobar.go": ({9}, {9})}
        self.assertIsNone(dc._match_path(covered, "bar.go"))


if __name__ == "__main__":
    unittest.main()
