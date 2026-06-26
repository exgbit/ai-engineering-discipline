"""code-analysis:目标项目的 git 改动文件、改动符号提取、文件分类。

从 execute_request.py 抽出的纯函数簇(只依赖 stdlib),供 execute_request 与
build_test_index 复用。不依赖 ManagedRequest 等框架类型,避免与 execute_request
形成循环 import(需要 request 的 git_diff_base 留在 execute_request)。
"""
import re
import subprocess
from pathlib import Path

_CODE_EXTS = (
    ".py", ".go", ".js", ".ts", ".jsx", ".tsx", ".java", ".rs", ".rb",
    ".php", ".c", ".cc", ".cpp", ".cs", ".kt", ".swift", ".scala",
)


def git_changed_files(target: Path, base_ref: str = "HEAD") -> list[str] | None:
    """目标项目从 base_ref 到当前工作树的改动文件(相对路径)。

    request 创建时记录 Change base;验证时按这个基线看完整需求变更范围,支持
    "先提交测试、后提交实现"的 TDD 流程。旧 request 没有基线时回退 HEAD。
    """
    files: set[str] = set()
    try:
        diff_result = subprocess.run(
            ["git", "-C", str(target), "diff", "--name-status", base_ref],
            capture_output=True, text=True, timeout=30,
        )
        status_result = subprocess.run(
            ["git", "-C", str(target), "status", "--porcelain"],
            capture_output=True, text=True, timeout=30,
        )
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        return None
    if diff_result.returncode != 0 or status_result.returncode != 0:
        return None
    _append_name_status_paths(files, diff_result.stdout)
    _append_status_paths(files, status_result.stdout)
    return sorted(files)


def is_test_file(path: str) -> bool:
    segs = path.lower().split("/")
    if any(seg in {"tests", "test", "__tests__", "spec"} for seg in segs):
        return True
    name = segs[-1]
    return (
        name.startswith("test_") or name.endswith("_test.py") or name.endswith("_test.go")
        or ".test." in name or ".spec." in name
        or name.endswith("test.java") or name.endswith("tests.java")
    )


def is_framework_artifact(path: str) -> bool:
    return path.startswith(("docs/", ".claude/", ".codex/", ".github/")) or path == ".ai-discipline.json"


def is_code_file(path: str) -> bool:
    return path.endswith(_CODE_EXTS)


def is_generated_noise(path: str) -> bool:
    parts = path.split("/")
    return "__pycache__" in parts or path.endswith((".pyc", ".pyo", ".class"))


def git_diff_command(target: Path, base_ref: str, *extra: str) -> list[str]:
    return ["git", "-C", str(target), "diff", base_ref, *extra]


def _append_status_paths(files: set[str], status_text: str) -> None:
    for line in status_text.splitlines():
        path = line[3:].strip() if len(line) > 3 else ""
        if " -> " in path:
            path = path.split(" -> ")[-1].strip()
        if path and not is_generated_noise(path):
            files.add(path)


def _append_name_status_paths(files: set[str], diff_text: str) -> None:
    for line in diff_text.splitlines():
        parts = line.split("\t")
        if not parts:
            continue
        path = parts[-1].strip()
        if path and not is_generated_noise(path):
            files.add(path)


# 从改动代码里提取被定义的符号(函数/类/方法名),用于核对测试是否真的引用了改动。
# 既认 def/class/func 等关键字定义,也认 const/let NAME = (...) => 这类 JS/TS
# 箭头函数 / 函数表达式 / 类表达式的赋值式定义(否则前端代码会整体绕过门禁)。
# 已知盲点(静态正则的固有上限,非 bug):装饰器工厂、re-export、动态分派/反射、
# Rust trait impl 等无法可靠提取。提不到符号时门禁标 uncovered 而非放行(fail-closed);
# 精确受影响面以 codebase-memory 知识图谱为准(见 code_graph.py)。
_SYMBOL_DEF_RE = re.compile(
    r"^[+\s]*(?:export\s+)?(?:default\s+)?(?:public\s+|private\s+|static\s+)*(?:async\s+)?"
    r"(?:def|class|func|function|fn|interface|type|struct|trait|impl)\s+([A-Za-z_$][\w$]*)"
)
_SYMBOL_ASSIGN_RE = re.compile(
    r"^[+\s]*(?:export\s+)?(?:default\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*"
    r"(?:async\s+)?(?:\([^)]*\)\s*=>|[A-Za-z_$][\w$]*\s*=>|function\b|class\b)"
)


def _match_symbol(line):
    match = _SYMBOL_DEF_RE.match(line) or _SYMBOL_ASSIGN_RE.match(line)
    return match.group(1) if match else None


def _nearest_def_above(lines, idx):
    """找改动行所属的符号。装饰器行(@...)属于其下方的函数,向下找;否则向上找最近的 def
    —— 否则改装饰器/签名上方的行会被误归到上一个函数。"""
    if not lines:
        return None
    start = min(max(idx, 0), len(lines) - 1)
    if lines[start].lstrip().startswith("@"):  # 改动落在装饰器上 → 归属下方的函数
        for j in range(start, min(start + 12, len(lines))):
            sym = _match_symbol(lines[j])
            if sym:
                return sym
    for i in range(start, -1, -1):
        sym = _match_symbol(lines[i])
        if sym:
            return sym
    return None


def changed_code_symbols(target: Path, code_files: list[str], base_ref: str = "HEAD") -> set[str]:
    """改动涉及的符号(函数/类名)。用 git diff --unified=0 精确定位改动行:
    - 对每个 hunk,按新文件起始行号在改动后的文件里**向上找最近的 def**(含缩进的类方法);
    - 从新增行(+)提取新增的定义。
    不用 git 自带的 hunk funcname:它只认顶格声明,会把缩进的类方法误归到外层 class
    (于是任何 import 该类的测试都白送通过)。也不用 -W:-W 会把相邻未改函数带进来。"""
    symbols: set[str] = set()
    for f in code_files:
        try:
            content_lines = (target / f).read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            content_lines = []
        diff_text = ""
        try:
            result = subprocess.run(
                ["git", "-C", str(target), "diff", base_ref, "--unified=0", "--", f],
                capture_output=True, text=True, timeout=30,
            )
            diff_text = result.stdout
        except (OSError, subprocess.SubprocessError):
            diff_text = ""
        file_syms: set[str] = set()
        has_hunk = False
        for line in diff_text.splitlines():
            if line.startswith("@@"):
                has_hunk = True
                # @@ -a,b +c,d @@ :取新文件改动起始行 c,在改后文件里向上找最近的 def
                m = re.search(r"\+(\d+)", line)
                if m and content_lines:
                    idx = min(max(int(m.group(1)) - 1, 0), len(content_lines) - 1)
                    sym = _nearest_def_above(content_lines, idx)
                    if sym:
                        file_syms.add(sym)
            elif line.startswith("+") and not line.startswith("+++"):
                sym = _match_symbol(line[1:])
                if sym:
                    file_syms.add(sym)
        # 回退全文提取的两种情形:① 无 diff(untracked/新文件);② git 把改动当作 binary
        # (含 null 字节的代码文件,只输出 "Binary files differ"、无 hunk)。有 hunk 却提
        # 不到符号(纯模块级改动)不回退,留给门禁标 uncovered(见 verification_gate_details)。
        if not diff_text.strip() or (not has_hunk and not file_syms):
            for line in content_lines:
                sym = _match_symbol(line)
                if sym:
                    file_syms.add(sym)
        symbols |= file_syms
    return symbols


def tests_reference_symbols(target: Path, test_files: list[str], symbols: set[str]) -> bool:
    """改动的测试文件是否引用了任一改动符号。提不出符号时返回 True(不阻断)。"""
    if not symbols:
        return True
    for tf in test_files:
        try:
            content = (target / tf).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if any(re.search(rf"\b{re.escape(s)}\b", content) for s in symbols):
            return True
    return False
