"""设计图先行(require_design_diagram)门禁 + 自动 Mermaid 依赖图的单测。

覆盖:required_verify_checks 的 design_diagram 项、gate 三态(缺文件/占位/已填)、
preset 未开启时不检查、write_design_diagram 占位生成,以及 code_graph 的
impact_graph_data / render_impact_mermaid / write_impact_diagram 与静态回退的边导出;
另含实战评估修复的回归:untracked 新文件对静态回退可见、测试文件不计入 blast radius、
diff-coverage 零改动 not-applicable、fallback 来源透出。
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import code_graph as cg  # noqa: E402
import execute_request as er  # noqa: E402


def make_request(target: Path, task: str = "docs", name: str = "t", verify_params=None) -> "er.ManagedRequest":
    return er.ManagedRequest(
        path=target / "docs" / "ai-engineering" / "current-request.md",
        target=target, task=task, name=name, execute=False, preset=task, risk="medium",
        change_base="", requirements=[],
        spec_path=target / "docs" / "specs" / "t.md",
        loop_path=target / "docs" / "loops" / "loop.md",
        verify_matrix_path=target / "docs" / "verify" / "test-matrix.md",
        memory_path=target / "docs" / "memory",
        spec_params={}, loop_params={}, verify_params=verify_params or {}, memory_params={},
    )


class DesignDiagramGateTest(unittest.TestCase):
    def _gate(self, request):
        return er.verification_gate_details(request, semgrep=None, native=[])

    def _reasons(self, gate) -> str:
        return " | ".join(str(x) for x in gate["blocking_reasons"])

    def test_required_checks_include_design_diagram(self):
        with tempfile.TemporaryDirectory() as td:
            req = make_request(Path(td), verify_params={"require_design_diagram": True})
            self.assertIn("design_diagram", er.required_verify_checks(req))

    def test_missing_file_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            req = make_request(Path(td), verify_params={"require_design_diagram": True})
            self.assertIn("design diagram missing", self._reasons(self._gate(req)))

    def test_placeholder_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            req = make_request(Path(td), verify_params={"require_design_diagram": True})
            er.write_design_diagram(Path(td), req, force=False, actions=[])
            path = er.design_diagram_path(Path(td), req)
            self.assertTrue(path.exists())
            self.assertIn("TBD", path.read_text(encoding="utf-8"))
            self.assertIn("design diagram incomplete", self._reasons(self._gate(req)))

    def test_filled_diagram_passes(self):
        with tempfile.TemporaryDirectory() as td:
            req = make_request(Path(td), verify_params={"require_design_diagram": True})
            path = er.design_diagram_path(Path(td), req)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "# Design Diagram: t\n\n```mermaid\nflowchart LR\n    a --> b\n```\n",
                encoding="utf-8",
            )
            reasons = self._reasons(self._gate(req))
            self.assertNotIn("design diagram missing", reasons)
            self.assertNotIn("design diagram incomplete", reasons)

    def test_tbd_note_and_checklist_do_not_block(self):
        # 设计图是自由 Markdown:正文出现字面 TBD 或未勾选清单不该误拦(回归:曾借用 section_is_complete)
        with tempfile.TemporaryDirectory() as td:
            req = make_request(Path(td), verify_params={"require_design_diagram": True})
            path = er.design_diagram_path(Path(td), req)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "# Design Diagram: t\n\n```mermaid\nflowchart LR\n    a --> b\n```\n\n"
                "备注:TBD Phase 2 再拆分。\n\n- [ ] confirm cache TTL\n",
                encoding="utf-8",
            )
            self.assertNotIn("design diagram", self._reasons(self._gate(req)))

    def test_drawn_diagram_with_tbd_comment_passes(self):
        # 画好的图里留一条合法的 "%% TBD: ..." 二期注释不该误拦(画了内容优先于占位串匹配)
        with tempfile.TemporaryDirectory() as td:
            req = make_request(Path(td), verify_params={"require_design_diagram": True})
            path = er.design_diagram_path(Path(td), req)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "# Design Diagram: t\n\n```mermaid\nflowchart LR\n    a --> b\n"
                "    %% TBD: phase 2 加缓存节点\n```\n",
                encoding="utf-8",
            )
            self.assertNotIn("design diagram", self._reasons(self._gate(req)))

    def test_four_backtick_fence_recognized(self):
        # 4 反引号围栏、info 串带属性的 mermaid 块同样算已画
        with tempfile.TemporaryDirectory() as td:
            req = make_request(Path(td), verify_params={"require_design_diagram": True})
            path = er.design_diagram_path(Path(td), req)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                '# Design Diagram: t\n\n````mermaid title="x"\nflowchart LR\n    a --> b\n````\n',
                encoding="utf-8",
            )
            self.assertNotIn("design diagram", self._reasons(self._gate(req)))

    def test_declaration_only_diagram_blocks(self):
        # 只写 "flowchart LR" 零节点零边 = 没画
        with tempfile.TemporaryDirectory() as td:
            req = make_request(Path(td), verify_params={"require_design_diagram": True})
            path = er.design_diagram_path(Path(td), req)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "# Design Diagram: t\n\n```mermaid\nflowchart LR\n```\n",
                encoding="utf-8",
            )
            self.assertIn("no Mermaid diagram content", self._reasons(self._gate(req)))

    def test_comment_only_mermaid_blocks(self):
        # mermaid 块里只有注释(没画任何节点)= 没画,即使占位注释已删
        with tempfile.TemporaryDirectory() as td:
            req = make_request(Path(td), verify_params={"require_design_diagram": True})
            path = er.design_diagram_path(Path(td), req)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "# Design Diagram: t\n\n```mermaid\n%% 稍后补\n```\n",
                encoding="utf-8",
            )
            self.assertIn("no Mermaid diagram content", self._reasons(self._gate(req)))

    def test_not_required_not_checked(self):
        with tempfile.TemporaryDirectory() as td:
            req = make_request(Path(td), verify_params={})
            gate = self._gate(req)
            self.assertNotIn("design_diagram", gate["required_checks"])
            self.assertNotIn("design diagram", self._reasons(gate))

    def test_write_design_diagram_noop_when_not_required(self):
        with tempfile.TemporaryDirectory() as td:
            req = make_request(Path(td), verify_params={})
            actions: list = []
            er.write_design_diagram(Path(td), req, force=False, actions=actions)
            self.assertFalse(er.design_diagram_path(Path(td), req).exists())
            self.assertEqual(actions, [])


class ImpactGraphDataTest(unittest.TestCase):
    DETECT = {
        "impacted_symbols": [
            {"name": "submit", "label": "Function", "file": "src/order.py"},
            {"name": "Order", "label": "Class", "file": "src/order.py"},
            {"name": "test_submit", "label": "Function", "file": "tests/test_order.py"},
            {"name": "order", "label": "Module", "file": "src/order.py"},
        ],
        "edges": [
            {"caller": "submit", "callee": "Order"},
            {"caller": "test_submit", "callee": "submit"},
        ],
        "changed_symbols": ["submit", "test_submit"],
    }

    def test_filters_tests_modules_and_dangling_edges(self):
        data = cg.impact_graph_data(self.DETECT)
        names = [n["name"] for n in data["nodes"]]
        self.assertEqual(names, ["submit", "Order"])  # 测试符号与 Module 节点被过滤
        self.assertEqual(data["edges"], [{"caller": "submit", "callee": "Order"}])
        self.assertEqual(data["changed"], ["submit"])

    def test_empty_result(self):
        self.assertEqual(cg.impact_graph_data(None), {"nodes": [], "edges": [], "changed": []})

    def test_same_name_in_two_files_both_kept(self):
        # 同名符号分属不同文件都保留;同 (name, file) 重复才去重
        detect = {
            "impacted_symbols": [
                {"name": "save", "label": "Method", "file": "src/order.py"},
                {"name": "save", "label": "Method", "file": "src/user.py"},
                {"name": "save", "label": "Method", "file": "src/order.py"},
            ],
        }
        data = cg.impact_graph_data(detect)
        self.assertEqual(len(data["nodes"]), 2)
        self.assertEqual({n["file"] for n in data["nodes"]}, {"src/order.py", "src/user.py"})

    def test_impacted_symbol_names_matches_nodes(self):
        # impacted_symbol_names 与图节点同源同口径(单一过滤实现,防漂移)
        names = cg.impacted_symbol_names(self.DETECT)
        self.assertEqual(names, [n["name"] for n in cg.impact_graph_data(self.DETECT)["nodes"]])


class RenderMermaidTest(unittest.TestCase):
    def test_with_edges_draws_calls(self):
        nodes = [{"name": "a.fn", "file": "a.py", "label": "Function"},
                 {"name": "b", "file": "b.py", "label": "Function"}]
        out = cg.render_impact_mermaid(nodes, [{"caller": "a.fn", "callee": "b"}], ["b"], ["a.fn"])
        self.assertIn("flowchart LR", out)
        self.assertIn("-->", out)
        self.assertNotIn("a.fn -->", out)  # 节点 ID 已消毒,原名只出现在显示 label 里
        self.assertIn('["a.fn"]', out)
        self.assertIn(" changed;", out)
        self.assertIn(" untested;", out)

    def test_without_edges_groups_by_file(self):
        nodes = [{"name": "a", "file": "x.py", "label": "Function"},
                 {"name": "b", "file": "y.py", "label": "Function"}]
        out = cg.render_impact_mermaid(nodes, [], [], [])
        self.assertIn("subgraph", out)
        self.assertNotIn("-->", out)

    def test_label_escapes_mermaid_metachars(self):
        # 泛型 <> / 引号 / # 会破坏 Mermaid 语法,label 必须转成实体
        nodes = [{"name": 'Repository<User> "#1"', "file": "r.ts", "label": "Class"}]
        out = cg.render_impact_mermaid(nodes, [], [], [])
        self.assertIn("#lt;", out)
        self.assertIn("#gt;", out)
        self.assertIn("#quot;", out)
        self.assertNotIn('<User>', out)


class WriteImpactDiagramTest(unittest.TestCase):
    def test_writes_mermaid_into_docs_diagrams(self):
        with tempfile.TemporaryDirectory() as td:
            impact = {
                "slug": "demo",
                "impacted": ["a"],
                "untested": [],
                "nodes": [{"name": "a", "file": "a.py", "label": "Function"}],
                "edges": [],
                "changed": ["a"],
            }
            cg.write_impact_report(td, impact)
            diagram = Path(td) / "docs" / "diagrams" / "demo-impact.md"
            self.assertTrue(diagram.exists())
            self.assertIn("```mermaid", diagram.read_text(encoding="utf-8"))
            report = (Path(td) / "docs" / "verify" / "impact-graph.md").read_text(encoding="utf-8")
            self.assertIn("docs/diagrams/demo-impact.md", report)
            graph_json = (Path(td) / "docs" / "verify" / "impact-graph.json").read_text(encoding="utf-8")
            self.assertIn('"nodes"', graph_json)
            self.assertIn('"edges"', graph_json)


class StaticFallbackEdgesTest(unittest.TestCase):
    def _git(self, cwd, *args):
        subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True)

    def test_static_fallback_exports_caller_edges(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            src = root / "app.py"
            src.write_text(
                "def callee():\n    return 1\n\n\ndef caller():\n    return callee()\n",
                encoding="utf-8",
            )
            self._git(root, "init", "-q")
            self._git(root, "add", "app.py")
            self._git(root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")
            # 改 callee 函数体 → 静态回退应算出 caller 受传递影响,并导出 caller→callee 边
            src.write_text(
                "def callee():\n    return 2\n\n\ndef caller():\n    return callee()\n",
                encoding="utf-8",
            )
            result = cg._static_detect_changes(root, since="HEAD")
            names = {s["name"] for s in result["impacted_symbols"]}
            self.assertEqual(names, {"callee", "caller"})
            self.assertEqual(result["changed_symbols"], ["callee"])
            self.assertIn({"caller": "caller", "callee": "callee"}, result["edges"])

    def test_untracked_new_file_visible_to_fallback(self):
        # 新功能常见路径:实现文件是 untracked → 图谱口径必须与测试配套门禁一致,能看见它
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "base.py").write_text("def base():\n    return 1\n", encoding="utf-8")
            self._git(root, "init", "-q")
            self._git(root, "add", "base.py")
            self._git(root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")
            (root / "feature.py").write_text(
                "from base import base\n\n\ndef feature():\n    return base() + 1\n",
                encoding="utf-8",
            )
            result = cg._static_detect_changes(root, since="HEAD")
            names = {s["name"] for s in result["impacted_symbols"]}
            self.assertIn("feature", names)

    def test_changed_test_file_not_in_blast_radius(self):
        # 测试文件的改动不算受影响接口:测试是守护者,不是 blast radius 的一部分
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "app.py").write_text("def fn():\n    return 1\n", encoding="utf-8")
            (root / "tests").mkdir()
            (root / "tests" / "test_app.py").write_text(
                "from app import fn\n\n\ndef test_fn():\n    assert fn() == 1\n",
                encoding="utf-8",
            )
            self._git(root, "init", "-q")
            self._git(root, "add", ".")
            self._git(root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")
            (root / "tests" / "test_app.py").write_text(
                "from app import fn\n\n\ndef test_fn():\n    assert fn() == 1\n\n\ndef test_more():\n    assert fn()\n",
                encoding="utf-8",
            )
            result = cg._static_detect_changes(root, since="HEAD")
            names = {s["name"] for s in result["impacted_symbols"]}
            self.assertNotIn("test_more", names)
            self.assertNotIn("test_fn", names)


class DiffCoverageGateMessagesTest(unittest.TestCase):
    def _reasons(self, request, diff_cov):
        gate = er.verification_gate_details(request, semgrep=None, native=[], diff_cov=diff_cov)
        return " | ".join(str(x) for x in gate["blocking_reasons"])

    def test_not_run_message_does_not_blame_tool(self):
        # 未运行 ≠ 工具缺失:不能把用户支去装 coverage 工具
        with tempfile.TemporaryDirectory() as td:
            req = make_request(Path(td), verify_params={"require_diff_coverage": True})
            reasons = self._reasons(req, diff_cov=None)
            self.assertIn("diff-coverage required but not run", reasons)
            self.assertNotIn("coverage tool unavailable", reasons)

    def test_not_applicable_zero_changes_no_block(self):
        # 没改业务代码 → not-applicable,不阻断(预编码阶段 verify 不该被 diff-coverage 拦)
        with tempfile.TemporaryDirectory() as td:
            req = make_request(Path(td), verify_params={"require_diff_coverage": True})
            diff_cov = {"available": True, "not_applicable": True, "uncovered_lines": {}, "reason": "no code changes to cover"}
            self.assertNotIn("diff-coverage", self._reasons(req, diff_cov))


class GraphSourceTransparencyTest(unittest.TestCase):
    def test_impact_report_states_fallback_source(self):
        # 静态回退是正则近似,来源必须透出到产物,不静默降级
        with tempfile.TemporaryDirectory() as td:
            impact = {
                "slug": "demo",
                "impacted": ["a"],
                "untested": [],
                "graph_source": "static-fallback",
                "fallback_reason": "detect_changes returned empty",
                "nodes": [{"name": "a", "file": "a.py", "label": "Function"}],
                "edges": [],
                "changed": ["a"],
            }
            cg.write_impact_report(td, impact)
            report = (Path(td) / "docs" / "verify" / "impact-graph.md").read_text(encoding="utf-8")
            self.assertIn("static-fallback", report)
            self.assertIn("detect_changes returned empty", report)


if __name__ == "__main__":
    unittest.main()
