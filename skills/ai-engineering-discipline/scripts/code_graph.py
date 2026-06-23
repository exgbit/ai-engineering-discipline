"""封装 codebase-memory-mcp CLI:给框架"建知识图谱 + 影响分析(blast radius)"能力。

框架对它是**硬依赖**(用户要求强制安装,见 adapters/default-stack.json 的 impact 层):
- graph_available() 检测二进制,没装则 doctor / 影响分析门禁报错并要求先装。
- 直接调 CLI(`codebase-memory-mcp cli ...`),不依赖 MCP session 加载;首次自动建 cache 目录
  (否则 index 的 persist 会静默失败)。
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

CACHE_DIR = Path.home() / ".cache" / "codebase-memory-mcp"
INSTALL_HINT = (
    "codebase-memory-mcp is required but not installed. Build and install it:\n"
    "  git clone https://github.com/win4r/codebase-memory-mcp-pro && cd codebase-memory-mcp-pro\n"
    "  ./scripts/build.sh && mkdir -p ~/.local/bin && cp build/c/codebase-memory-mcp ~/.local/bin/\n"
    "  claude mcp add codebase-memory -s user -- ~/.local/bin/codebase-memory-mcp"
)


def graph_binary():
    """codebase-memory-mcp 二进制路径(PATH 或 ~/.local/bin);没装返回 None。"""
    found = shutil.which("codebase-memory-mcp")
    if found:
        return found
    local = Path.home() / ".local" / "bin" / "codebase-memory-mcp"
    return str(local) if local.is_file() else None


def graph_available():
    return graph_binary() is not None


def _run(args, timeout=600):
    binary = graph_binary()
    if not binary:
        return None
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)  # 首次必须建,否则 persist 静默失败
        result = subprocess.run(
            [binary, "cli"] + args, capture_output=True, text=True, timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    # CLI 把 JSON 结果输出在最后一行(前面是 level=info 日志);不同构建版本可能写
    # stdout 或 stderr,两边都要解析,否则会把可用图谱误判成 None。
    combined = f"{result.stdout}\n{result.stderr}"
    for line in reversed(combined.splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except ValueError:
                return None
    return None


def index_repository(target):
    """建/刷新项目知识图谱(新项目也从头建)。返回 {project, status, nodes, edges} 或 None。"""
    return _run(["index_repository", json.dumps({"repo_path": str(Path(target).resolve())})])


def detect_changes(target, since="HEAD", depth=2):
    """先建图拿 project 标识,再 detect_changes:git diff(since)→ 受影响符号 blast radius。
    返回 {impacted_symbols: [...], impacted_count, changed_files, ...} 或 None。"""
    idx = index_repository(target)
    if not idx or not idx.get("project") or idx.get("status") == "error":
        return _static_detect_changes(target, since=since, depth=depth, reason="index_repository failed")
    payload = {"project": idx["project"], "depth": depth, "since": since}
    result = _run(["detect_changes", json.dumps(payload)])
    if not result or not result.get("impacted_symbols"):
        return _static_detect_changes(target, since=since, depth=depth, reason="detect_changes returned empty")
    return result


CODE_EXTS = {".py", ".js", ".jsx", ".ts", ".tsx"}
DEF_RE = re.compile(
    r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?"
    r"(?:def|class|function)\s+([A-Za-z_$][\w$]*)\b"
)
ASSIGN_RE = re.compile(
    r"^\s*(?:export\s+)?(?:default\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*"
    r"(?:async\s+)?(?:\([^)]*\)\s*=>|[A-Za-z_$][\w$]*\s*=>|function\b|class\b)"
)


def _is_code_path(path):
    return Path(path).suffix in CODE_EXTS


def _is_generated_or_vendor(path):
    parts = set(Path(path).parts)
    return bool(parts & {"node_modules", "vendor", "dist", "build", "target", ".git", "__pycache__"})


def _git_lines(target, args):
    try:
        result = subprocess.run(
            ["git", "-C", str(Path(target).resolve()), *args],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    if result.returncode != 0:
        return []
    return result.stdout.splitlines()


def _symbol_from_line(line):
    match = DEF_RE.match(line) or ASSIGN_RE.match(line)
    return match.group(1) if match else None


def _line_indent(line):
    return len(line) - len(line.lstrip(" "))


def _extract_defs(path):
    try:
        lines = Path(path).read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return []
    starts = []
    for idx, line in enumerate(lines):
        name = _symbol_from_line(line)
        if name:
            starts.append((idx, name, _line_indent(line)))
    defs = []
    for pos, (idx, name, indent) in enumerate(starts):
        end = len(lines)
        for next_idx, _, next_indent in starts[pos + 1:]:
            if next_indent <= indent:
                end = next_idx
                break
        defs.append({
            "name": name,
            "file": str(path),
            "start": idx + 1,
            "end": end,
            "body": "\n".join(lines[idx:end]),
        })
    return defs


def _changed_files(target, since):
    return [
        line.strip()
        for line in _git_lines(target, ["diff", "--name-only", since])
        if line.strip() and _is_code_path(line.strip()) and not _is_generated_or_vendor(line.strip())
    ]


def _changed_symbols(target, changed_files, since):
    symbols = set()
    for rel_path in changed_files:
        path = Path(target) / rel_path
        defs = _extract_defs(path)
        for line in _git_lines(target, ["diff", "--unified=0", since, "--", rel_path]):
            if line.startswith("@@"):
                match = re.search(r"\+(\d+)", line)
                if not match:
                    continue
                lineno = int(match.group(1))
                owner = None
                for item in defs:
                    if item["start"] <= lineno <= item["end"]:
                        owner = item["name"]
                        break
                if owner:
                    symbols.add(owner)
            elif line.startswith("+") and not line.startswith("+++"):
                name = _symbol_from_line(line[1:])
                if name:
                    symbols.add(name)
        if not symbols:
            symbols.update(item["name"] for item in defs)
    return symbols


def _all_source_files(target):
    root = Path(target)
    files = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in CODE_EXTS:
            continue
        rel = path.relative_to(root)
        if _is_generated_or_vendor(rel) or _looks_like_test(str(rel)):
            continue
        files.append(path)
    return files


def _static_detect_changes(target, since="HEAD", depth=2, reason="fallback"):
    target = Path(target).resolve()
    changed = _changed_files(target, since)
    changed_symbols = _changed_symbols(target, changed, since)
    if not changed_symbols:
        return {
            "status": "fallback",
            "fallback_reason": reason,
            "changed_files": changed,
            "impacted_count": 0,
            "impacted_symbols": [],
        }

    defs = []
    for path in _all_source_files(target):
        defs.extend(_extract_defs(path))

    callers_by_callee = {name: set() for name in changed_symbols}
    symbol_files = {}
    for item in defs:
        symbol_files.setdefault(item["name"], item["file"])
    all_names = {item["name"] for item in defs}
    for item in defs:
        body = item["body"]
        caller = item["name"]
        for callee in all_names:
            if caller == callee:
                continue
            if re.search(rf"\b{re.escape(callee)}\s*\(", body):
                callers_by_callee.setdefault(callee, set()).add(caller)

    impacted = set(changed_symbols)
    frontier = set(changed_symbols)
    for _ in range(max(0, int(depth))):
        next_frontier = set()
        for name in frontier:
            next_frontier.update(callers_by_callee.get(name, set()))
        next_frontier -= impacted
        impacted.update(next_frontier)
        frontier = next_frontier
        if not frontier:
            break

    symbols = [
        {"name": name, "label": "Function", "file": symbol_files.get(name, "")}
        for name in sorted(impacted)
    ]
    return {
        "status": "fallback",
        "fallback_reason": reason,
        "changed_files": changed,
        "impacted_count": len(symbols),
        "impacted_symbols": symbols,
    }


def _looks_like_test(path):
    p = str(path or "").lower()
    return any(t in p for t in ("test_", "_test", ".test.", ".spec.", "tests/", "/test/", "spec/"))


def impacted_symbol_names(detect_result):
    """从 detect_changes 结果提取受影响的函数/类/接口名(过滤 Module/File 节点 + 测试文件符号——
    测试函数是测试本身,不是被影响的接口)。"""
    if not detect_result:
        return []
    names = []
    for sym in detect_result.get("impacted_symbols") or []:
        if _looks_like_test(sym.get("file")):
            continue
        label = str(sym.get("label", ""))
        if label in {"Function", "Method", "Class", "Interface", "Struct", "Type", "Enum"}:
            name = sym.get("name")
            if name:
                names.append(name)
    return names


def impacted_untested(target, impacted_names):
    """受影响接口 ∩ test-index 盲区(没测试守护的)= 受影响但没测的接口。
    没有 test-index(还没建)时返回空,不误判。"""
    if not impacted_names:
        return []
    ti = Path(target) / "docs" / "verify" / "test-index.json"
    try:
        data = json.loads(ti.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    blind = {b.get("symbol") for b in data.get("blind_spots") or []}
    return sorted(set(impacted_names) & blind)


def write_impact_report(target, impact):
    """把图谱影响分析写成 docs/verify/impact-graph.{md,json}(给 agent 看,据此先补测试)。"""
    out = Path(target) / "docs" / "verify"
    out.mkdir(parents=True, exist_ok=True)
    impacted = impact.get("impacted") or []
    untested = impact.get("untested") or []
    lines = [
        "<!-- ai-engineering:generated -->",
        "# Impact Analysis (knowledge-graph blast radius)",
        "",
        "由 codebase-memory 的 detect_changes 算出:本次改动传递性影响到的接口/函数。",
        "**受影响但没有测试守护的接口,应在开发前先补测试**(交叉 test-index 盲区)。",
        "",
        f"- Affected interfaces: {len(impacted)}",
        f"- Affected **without** a guarding test: {len(untested)}",
        "",
        "## Affected but untested (add tests first)",
    ]
    lines += ([f"- `{n}`" for n in untested]
              or ["- (none — all affected interfaces have tests, or no test-index yet)"])
    lines += ["", "## All affected interfaces", ""]
    lines += [f"- `{n}`" for n in impacted] or ["- (none)"]
    (out / "impact-graph.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out / "impact-graph.json").write_text(
        json.dumps(impact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    import sys
    args = sys.argv[1:]
    if not args:
        print("usage: code_graph.py <target> [since]   |   code_graph.py index <target>")
        return 2
    # index 模式:建/刷新知识图谱(新项目从头建图也走这里)
    if args[0] == "index":
        if len(args) < 2:
            print("usage: code_graph.py index <target>")
            return 2
        if not graph_available():
            print(INSTALL_HINT)
            return 1
        idx = index_repository(Path(args[1]).expanduser().resolve())
        print(json.dumps(idx, ensure_ascii=False) if idx else "index failed")
        return 0 if idx else 1
    # 默认:影响分析(detect_changes blast radius)
    target = Path(args[0]).expanduser().resolve()
    since = args[1] if len(args) > 1 else "HEAD"
    if not graph_available():
        print(INSTALL_HINT)
        return 1
    result = detect_changes(target, since=since)
    print(json.dumps({"available": True, "detect": result,
                      "impacted": impacted_symbol_names(result)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
