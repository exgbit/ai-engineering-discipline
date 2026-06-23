#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/bootstrap.sh <target-project-path> [--force] [--install-adapters]

Installs the Spec / Verify / Memory + Loop framework into a target project.

Options:
  --force             Overwrite existing framework files in the target project.
  --install-adapters  Install optional adapter tooling such as Semgrep. codebase-memory remains the required impact-analysis gate; build it as described in README.
USAGE
}

if [[ $# -lt 1 ]]; then
  usage
  exit 1
fi

TARGET_DIR="$1"
FORCE="0"
INSTALL_ADAPTERS="0"
shift

while [[ $# -gt 0 ]]; do
  case "$1" in
    --force)
      FORCE="1"
      ;;
    --install-adapters)
      INSTALL_ADAPTERS="1"
      ;;
    *)
      usage
      exit 1
      ;;
  esac
  shift
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRAMEWORK_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
if command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
elif command -v python >/dev/null 2>&1 && \
     python -c 'import sys; sys.exit(0 if sys.version_info[:2] >= (3, 9) else 1)' >/dev/null 2>&1; then
  PYTHON=python
else
  echo "Python 3.9+ is required (python3 not found)." >&2
  exit 1
fi

if [[ ! -d "$TARGET_DIR" ]]; then
  echo "Target project does not exist: $TARGET_DIR" >&2
  exit 1
fi

copy_file() {
  local src="$1"
  local dst="$2"
  if [[ -e "$dst" && "$FORCE" != "1" ]]; then
    echo "skip existing: $dst"
    return
  fi
  # --force 覆盖用户可能自著的文件前,内容有变化才备份一份 .bak
  if [[ -e "$dst" && "$FORCE" == "1" ]]; then
    case "$(basename "$dst")" in
      CLAUDE.md|AGENTS.md|.ai-discipline.json)
        if ! cmp -s "$src" "$dst"; then
          cp "$dst" "$dst.bak"
          echo "backup: $dst.bak"
        fi
        ;;
    esac
  fi
  mkdir -p "$(dirname "$dst")"
  cp "$src" "$dst"
  echo "installed: $dst"
}

write_file_if_missing() {
  local dst="$1"
  local title="$2"
  local body="$3"
  if [[ -e "$dst" && "$FORCE" != "1" ]]; then
    echo "skip existing: $dst"
    return
  fi
  mkdir -p "$(dirname "$dst")"
  printf '# %s\n\n%s\n' "$title" "$body" > "$dst"
  echo "created: $dst"
}

mkdir -p \
  "$TARGET_DIR/docs/specs" \
  "$TARGET_DIR/docs/verify" \
  "$TARGET_DIR/docs/memory" \
  "$TARGET_DIR/docs/loops" \
  "$TARGET_DIR/.github" \
  "$TARGET_DIR/.github/workflows" \
  "$TARGET_DIR/.claude/commands" \
  "$TARGET_DIR/.claude/skills" \
  "$TARGET_DIR/.codex/skills"

copy_file "$FRAMEWORK_ROOT/CLAUDE.md" "$TARGET_DIR/CLAUDE.md"
copy_file "$FRAMEWORK_ROOT/templates/ai-discipline-config.json" "$TARGET_DIR/.ai-discipline.json"
copy_file "$FRAMEWORK_ROOT/templates/agents-template.md" "$TARGET_DIR/AGENTS.md"
copy_file "$FRAMEWORK_ROOT/templates/spec-template.md" "$TARGET_DIR/docs/specs/spec-template.md"
copy_file "$FRAMEWORK_ROOT/templates/verify-checklist.md" "$TARGET_DIR/docs/verify/verify-checklist.md"
copy_file "$FRAMEWORK_ROOT/templates/memory-entry.md" "$TARGET_DIR/docs/memory/memory-entry.md"
copy_file "$FRAMEWORK_ROOT/templates/loop-template.md" "$TARGET_DIR/docs/loops/loop-template.md"
copy_file "$FRAMEWORK_ROOT/templates/pr-template.md" "$TARGET_DIR/.github/pull_request_template.md"
copy_file "$FRAMEWORK_ROOT/templates/github-ai-discipline.yml" "$TARGET_DIR/.github/workflows/ai-discipline.yml"
copy_file "$FRAMEWORK_ROOT/templates/start-here.md" "$TARGET_DIR/docs/AI_ENGINEERING_START_HERE.md"
copy_file "$FRAMEWORK_ROOT/examples/test-matrix.example.md" "$TARGET_DIR/docs/verify/test-matrix.md"
copy_file "$FRAMEWORK_ROOT/examples/loop-runbook.example.md" "$TARGET_DIR/docs/loops/bugfix-loop.md"

install_skill_dir() {
  local src="$1"
  local dst="$2"
  if [[ -d "$dst" && "$FORCE" != "1" ]]; then
    echo "skip existing: $dst"
  else
    if [[ -d "$dst" && "$FORCE" == "1" ]]; then
      rm -rf "$dst"
    fi
    mkdir -p "$dst"
    tar -C "$src" --exclude='__pycache__' --exclude='*.pyc' --exclude='.DS_Store' -cf - . | tar -C "$dst" -xf -
    find "$dst" -type d -name __pycache__ -prune -exec rm -rf {} +
    find "$dst" -type f \( -name '*.pyc' -o -name '.DS_Store' \) -delete
    echo "installed: $dst"
  fi
}

for skill_name in ai-engineering-discipline ai-spec ai-loop ai-verify ai-memory; do
  install_skill_dir "$FRAMEWORK_ROOT/skills/$skill_name" "$TARGET_DIR/.codex/skills/$skill_name"
  install_skill_dir "$FRAMEWORK_ROOT/claude-code-skills/$skill_name" "$TARGET_DIR/.claude/skills/$skill_name"
done

if [[ -d "$FRAMEWORK_ROOT/claude-code-commands" ]]; then
  for command_file in "$FRAMEWORK_ROOT"/claude-code-commands/*.md; do
    copy_file "$command_file" "$TARGET_DIR/.claude/commands/$(basename "$command_file")"
  done
fi

write_file_if_missing "$TARGET_DIR/docs/memory/project-rules.md" "Project Rules" \
"- Add project-specific architecture and coding rules here.
- AI-generated code must include verification evidence before merge.
- Repeated mistakes should be converted into memory entries or loop updates.
- Existing-project changes must include impact analysis and regression checks before implementation."

write_file_if_missing "$TARGET_DIR/docs/memory/module-map.md" "Module Map" \
"| Module | Owner | Responsibility | Coupled With | Required Regression Checks | Boundary / Forbidden Dependencies |
|---|---|---|---|---|---|
| TBD | TBD | Describe responsibility | upstream/downstream modules, APIs, jobs, data stores | test command or manual check | describe forbidden dependencies |"

write_file_if_missing "$TARGET_DIR/docs/memory/pitfalls.md" "Pitfalls" \
"Record repeated bugs, failed assumptions, review findings, and incident lessons here.

## Template

- Date:
- Context:
- Problem:
- Rule / Lesson:
- Verification to add next time:"

# 适配器安装失败不应中断 bootstrap(框架文件已装好);与 bootstrap.bat 的容错行为保持一致
if [[ "$INSTALL_ADAPTERS" == "1" ]]; then
  "$PYTHON" "$FRAMEWORK_ROOT/scripts/install_default_adapters.py" "$TARGET_DIR" --execute \
    || echo "Warning: adapter install reported failures; review $TARGET_DIR/docs/adapters/default-stack.md." >&2
else
  "$PYTHON" "$FRAMEWORK_ROOT/scripts/install_default_adapters.py" "$TARGET_DIR" || true
fi

echo
echo "Bootstrap complete."
echo "Next steps:"
echo "  1. Read $TARGET_DIR/docs/AI_ENGINEERING_START_HERE.md"
echo "  2. Open Claude Code in the target project."
echo "  3. Run: /ai-start  (initialize and inspect)"
echo "  4. Build with one plain sentence, e.g.: /ai-build add a refund approval flow"
echo "  5. If setup looks wrong, run: /ai-doctor"
