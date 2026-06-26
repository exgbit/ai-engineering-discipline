"""扫描目标项目现有测试,建立"功能/接口符号 → 守护测试"的反向索引 + 盲区。

给旧项目换人上手用:看索引就知道每个函数/类有哪些测试守着、哪些功能没测。

诚实边界:这是"测试文本里出现了符号名"的**静态映射,不是真覆盖率**。一处"guard"
只表示符号名出现在测试文本里(可能是 import/注释/字符串);名字碰撞会过度关联;
盲区是"很可能没测"的强信号,不是零覆盖的证明。真覆盖率仍需语言自带的 coverage 工具。
"""
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

# 复用 execute_request 的符号提取与文件分类(它和本脚本同目录,是 skill 副本的权威源)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from code_analysis import (  # noqa: E402
    _CODE_EXTS,
    _match_symbol,
    is_code_file,
    is_framework_artifact,
    is_test_file,
)
from execute_request import GENERATED, md_cell  # noqa: E402

SKIP_DIRS = {
    "node_modules", "vendor", "dist", "build", "target", ".git", ".venv", "venv",
    "__pycache__", ".tox", ".mypy_cache", ".pytest_cache", ".claude", ".codex",
    ".github", "docs", ".idea", ".vscode",
}
MAX_FILES = 5000
MAX_FILE_BYTES = 512 * 1024
_TOKEN_RE = re.compile(r"[A-Za-z_$][\w$]*")
_KIND_RE = re.compile(r"\b(def|class|func|function|fn|interface|type|struct|trait|impl|const|let|var)\b")
_KIND_MAP = {"def": "function", "func": "function", "function": "function", "fn": "function",
             "const": "function", "let": "function", "var": "function"}


def _read_lines(path: Path) -> list[str]:
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return []
        return path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return []


_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_TRIPLE_STR_RE = re.compile(r'""".*?"""|\'\'\'.*?\'\'\'', re.DOTALL)


def _blank_keep_newlines(m: "re.Match") -> str:
    # 把匹配内容清成空白但保留换行,避免打乱行号(测试用例范围跟踪靠行序)
    return re.sub(r"[^\n]", " ", m.group(0))


def _strip_line(line: str) -> str:
    """逐字符扫描一行:跳过字符串字面量内容,遇到字符串外的 # 或 // 行注释就截断。"""
    out = []
    i, n = 0, len(line)
    quote = None
    while i < n:
        c = line[i]
        if quote:
            if c == "\\" and i + 1 < n:  # 转义:跳过下一个字符
                i += 2
                continue
            if c == quote:
                quote = None
            i += 1
            continue
        if c in ("'", '"', "`"):
            quote = c
            i += 1
            continue
        if c == "#":  # Python/shell 行注释
            break
        if c == "/" and i + 1 < n and line[i + 1] == "/":  # // 行注释
            break
        out.append(c)
        i += 1
    return "".join(out)


def _strip_comments_strings(lines: list[str]) -> list[str]:
    """剥离注释和字符串字面量后逐行返回,避免注释/docstring/字符串里出现的符号名被当成
    测试引用(否则测试 docstring 写了函数名会让盲区/影响分析漏报)。务实够用版,覆盖
    Python/JS/TS/Go/Java/Rust/C 常见语法,非完整 tokenizer。"""
    text = "\n".join(lines)
    text = _BLOCK_COMMENT_RE.sub(_blank_keep_newlines, text)   # /* ... */
    text = _TRIPLE_STR_RE.sub(_blank_keep_newlines, text)      # """...""" / '''...'''
    return [_strip_line(ln) for ln in text.split("\n")]


def _kind_of(line: str) -> str:
    m = _KIND_RE.search(line)
    raw = m.group(1) if m else "symbol"
    return _KIND_MAP.get(raw, raw)


def _looks_like_test_case(name: str) -> bool:
    return name.startswith(("test", "Test")) or name.endswith(("Test", "Tests"))


def _iter_files(target: Path):
    files: list[str] = []
    truncated = False
    for root, dirs, names in os.walk(target):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for n in names:
            rel = str((Path(root) / n).relative_to(target)).replace(os.sep, "/")
            if not is_code_file(rel):
                continue  # 只按代码文件计数,避免 assets/数据文件把真正的代码挤出 MAX_FILES
            files.append(rel)
            if len(files) >= MAX_FILES:
                return files, True
    return files, truncated


def build_index(target: Path) -> dict:
    files, truncated = _iter_files(target)
    code_files = [f for f in files if is_code_file(f) and not is_test_file(f) and not is_framework_artifact(f)]
    test_files = [f for f in files if is_test_file(f) and f.endswith(_CODE_EXTS) and not is_framework_artifact(f)]

    # 代码符号: name -> {defined_in, kind}(同名只记首次定义;跨文件同名的后续定义会被合并,
    # 属静态索引的已知局限,见 _render_md 的 Limitations 段;盲区漏报由门禁的图谱通路兜底)
    symbols: dict[str, dict] = {}
    for cf in code_files:
        for line in _read_lines(target / cf):
            name = _match_symbol(line)
            if name and name not in symbols:
                symbols[name] = {"defined_in": cf, "kind": _kind_of(line)}

    # 测试 token 集(文件级)+ 用例级(case -> token set)
    test_tokens: dict[str, set] = {}
    test_cases: dict[str, dict] = {}
    for tf in test_files:
        toks: set = set()
        cases: dict[str, set] = {}
        current = None
        for line in _strip_comments_strings(_read_lines(target / tf)):
            line_toks = _TOKEN_RE.findall(line)
            toks.update(line_toks)
            name = _match_symbol(line)
            if name and _looks_like_test_case(name):
                current = name
                cases.setdefault(current, set())
            if current is not None:
                cases[current].update(line_toks)
        test_tokens[tf] = toks
        test_cases[tf] = cases

    # 反向索引
    guarded: list[dict] = []
    blind: list[dict] = []
    for name, info in sorted(symbols.items()):
        tests = []
        for tf in test_files:
            if name in test_tokens[tf]:
                hit = sorted(c for c, ct in test_cases[tf].items() if name in ct)
                tests.append({"file": tf, "cases": hit})
        row = {"symbol": name, "kind": info["kind"], "defined_in": info["defined_in"]}
        if tests:
            guarded.append({**row, "tests": tests})
        else:
            blind.append(row)

    n = len(symbols)
    return {
        "created": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "code_symbols": n,
            "guarded": len(guarded),
            "blind_spots": len(blind),
            "ref_coverage": round(len(guarded) / n, 3) if n else 0.0,
            "test_files": len(test_files),
            "truncated": truncated,
        },
        "symbols": guarded,
        "blind_spots": blind,
    }


def _render_md(data: dict) -> str:
    s = data["summary"]
    lines = [
        "# Test Index (code symbol -> guarding tests)",
        "",
        "由 ai-engineering-discipline 自动生成。**这是静态名字引用映射,不是执行覆盖率** ——",
        "一处 \"guard\" 只表示该符号名出现在测试文本里(可能是 import / 注释 / 字符串)。详见末尾 Limitations。",
        "需求级意图见 `docs/verify/test-matrix.md`。",
        "",
        "## Summary",
        f"- Code symbols: {s['code_symbols']}",
        f"- Guarded (>=1 test references the name): {s['guarded']} ({int(s['ref_coverage'] * 100)}%)",
        f"- Blind spots (no test references the name): {s['blind_spots']}",
        f"- Test files scanned: {s['test_files']}",
    ]
    if s["truncated"]:
        lines.append(f"- NOTE: scan truncated at {MAX_FILES} files; results are partial.")
    lines += ["", "## Guarded Symbols", "", "| Symbol | Kind | Defined In | Guarding Tests |", "|---|---|---|---|"]
    for g in data["symbols"]:
        cells: list[str] = []
        for t in g["tests"]:
            cells += [f"{t['file']}::{c}" for c in t["cases"]] or [t["file"]]
        shown = ", ".join(cells[:6]) + (f" (+{len(cells) - 6})" if len(cells) > 6 else "")
        lines.append(f"| {md_cell(g['symbol'])} | {g['kind']} | {md_cell(g['defined_in'])} | {md_cell(shown)} |")
    lines += ["", "## Blind Spots (no test references this symbol)", "", "| Symbol | Kind | Defined In |", "|---|---|---|"]
    for b in data["blind_spots"]:
        lines.append(f"| {md_cell(b['symbol'])} | {b['kind']} | {md_cell(b['defined_in'])} |")
    lines += [
        "", "## Limitations",
        "- 静态名字匹配,非覆盖率;一处引用可能是 import / 注释 / 字符串。",
        "- 跨文件同名符号会被合并,常见/短名会过度关联。",
        "- 只可靠提取 def/class/func/箭头赋值(py/go/js/ts 最强);动态分派、反射、re-export、装饰器、BDD 字符串用例不可见。",
        "- 盲区是\"很可能没测\"的强信号,不是零覆盖的证明。真覆盖率仍需语言自带 coverage 工具。",
        "",
    ]
    return "\n".join(lines)


def _append_history(target: Path, data: dict, actions: list) -> None:
    s = data["summary"]
    data_dir = target / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    rec = {"ts": data["created"], "code_symbols": s["code_symbols"],
           "guarded": s["guarded"], "blind_spots": s["blind_spots"]}
    path = data_dir / "test-index-history.jsonl"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    actions.append(f"append: {path}")


def write_test_index(target: Path, actions=None) -> dict:
    if actions is None:
        actions = []
    data = build_index(target)
    verify_dir = target / "docs" / "verify"
    verify_dir.mkdir(parents=True, exist_ok=True)
    json_path = verify_dir / "test-index.json"
    json_path.write_text(
        json.dumps({"generated_by": "ai-engineering-discipline", **data}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    actions.append(f"write: {json_path}")
    md_path = verify_dir / "test-index.md"
    md_path.write_text(GENERATED + "\n" + _render_md(data), encoding="utf-8")
    actions.append(f"write: {md_path}")
    _append_history(target, data, actions)
    return data


def refresh_test_index(target: Path, actions: list) -> None:
    """每次验证后自动刷新的防御性包装:索引是 nice-to-have,绝不破坏门禁/smoke。"""
    try:
        write_test_index(target, actions)
    except Exception as exc:  # noqa: BLE001
        actions.append(f"skip test-index: {exc}")


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: build_test_index.py <target>", file=sys.stderr)
        return 2
    target = Path(sys.argv[1]).expanduser().resolve()
    data = write_test_index(target, [])
    s = data["summary"]
    print(f"test-index: {s['guarded']}/{s['code_symbols']} symbols guarded, "
          f"{s['blind_spots']} blind spots ({s['test_files']} test files)")
    print(f"wrote: {target / 'docs' / 'verify' / 'test-index.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
