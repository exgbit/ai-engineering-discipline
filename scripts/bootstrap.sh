#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/bootstrap.sh <target-project-path> [--force] [--install-adapters]

Installs the Spec / Verify / Memory + Loop framework into a target project.

Options:
  --force             Overwrite existing framework files in the target project.
  --install-adapters  Install default open-source adapters: Spec Kit, LangGraph, Semgrep, Mem0.
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
  "$TARGET_DIR/.claude/skills" \
  "$TARGET_DIR/.codex/skills"

copy_file "$FRAMEWORK_ROOT/CLAUDE.md" "$TARGET_DIR/CLAUDE.md"
copy_file "$FRAMEWORK_ROOT/templates/spec-template.md" "$TARGET_DIR/docs/specs/spec-template.md"
copy_file "$FRAMEWORK_ROOT/templates/verify-checklist.md" "$TARGET_DIR/docs/verify/verify-checklist.md"
copy_file "$FRAMEWORK_ROOT/templates/memory-entry.md" "$TARGET_DIR/docs/memory/memory-entry.md"
copy_file "$FRAMEWORK_ROOT/templates/loop-template.md" "$TARGET_DIR/docs/loops/loop-template.md"
copy_file "$FRAMEWORK_ROOT/templates/pr-template.md" "$TARGET_DIR/.github/pull_request_template.md"
copy_file "$FRAMEWORK_ROOT/examples/test-matrix.example.md" "$TARGET_DIR/docs/verify/test-matrix.md"
copy_file "$FRAMEWORK_ROOT/examples/loop-runbook.example.md" "$TARGET_DIR/docs/loops/bugfix-loop.md"

CODEX_SKILL_SRC="$FRAMEWORK_ROOT/skills/ai-engineering-discipline"
CODEX_SKILL_DST="$TARGET_DIR/.codex/skills/ai-engineering-discipline"
if [[ -d "$CODEX_SKILL_DST" && "$FORCE" != "1" ]]; then
  echo "skip existing: $CODEX_SKILL_DST"
else
  mkdir -p "$CODEX_SKILL_DST"
  cp -R "$CODEX_SKILL_SRC/." "$CODEX_SKILL_DST/"
  echo "installed: $CODEX_SKILL_DST"
fi

CLAUDE_SKILL_SRC="$FRAMEWORK_ROOT/claude-code-skills/ai-engineering-discipline"
CLAUDE_SKILL_DST="$TARGET_DIR/.claude/skills/ai-engineering-discipline"
if [[ -d "$CLAUDE_SKILL_DST" && "$FORCE" != "1" ]]; then
  echo "skip existing: $CLAUDE_SKILL_DST"
else
  mkdir -p "$CLAUDE_SKILL_DST"
  cp -R "$CLAUDE_SKILL_SRC/." "$CLAUDE_SKILL_DST/"
  echo "installed: $CLAUDE_SKILL_DST"
fi

write_file_if_missing "$TARGET_DIR/docs/memory/project-rules.md" "Project Rules" \
"- Add project-specific architecture and coding rules here.
- AI-generated code must include verification evidence before merge.
- Repeated mistakes should be converted into memory entries or loop updates."

write_file_if_missing "$TARGET_DIR/docs/memory/module-map.md" "Module Map" \
"| Module | Owner | Boundary |
|---|---|---|
| TBD | TBD | Describe responsibility and forbidden dependencies |"

write_file_if_missing "$TARGET_DIR/docs/memory/pitfalls.md" "Pitfalls" \
"Record repeated bugs, failed assumptions, review findings, and incident lessons here.

## Template

- Date:
- Context:
- Problem:
- Rule / Lesson:
- Verification to add next time:"

if [[ "$INSTALL_ADAPTERS" == "1" ]]; then
  python "$FRAMEWORK_ROOT/scripts/install_default_adapters.py" "$TARGET_DIR" --execute
else
  python "$FRAMEWORK_ROOT/scripts/install_default_adapters.py" "$TARGET_DIR"
fi

echo
echo "Bootstrap complete."
echo "Next steps:"
echo "  1. Read $TARGET_DIR/CLAUDE.md"
echo "  2. Open Claude Code in the target project."
echo "  3. Say: Use ai-engineering-discipline to inspect this project and enter development."
echo "  4. Review docs/adapters/default-stack.md for Spec Kit / LangGraph / Semgrep / Mem0 status."
echo "  5. The skill will create docs/memory/project-scan.md and guide Spec -> Loop -> Verify -> Memory."
