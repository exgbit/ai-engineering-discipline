#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/bootstrap.sh <target-project-path> [--force]

Installs the Spec / Verify / Memory + Loop framework into a target project.

Options:
  --force   Overwrite existing framework files in the target project.
USAGE
}

if [[ $# -lt 1 || $# -gt 2 ]]; then
  usage
  exit 1
fi

TARGET_DIR="$1"
FORCE="0"

if [[ $# -eq 2 ]]; then
  if [[ "$2" == "--force" ]]; then
    FORCE="1"
  else
    usage
    exit 1
  fi
fi

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
  "$TARGET_DIR/.claude/skills"

copy_file "$FRAMEWORK_ROOT/CLAUDE.md" "$TARGET_DIR/CLAUDE.md"
copy_file "$FRAMEWORK_ROOT/templates/spec-template.md" "$TARGET_DIR/docs/specs/spec-template.md"
copy_file "$FRAMEWORK_ROOT/templates/verify-checklist.md" "$TARGET_DIR/docs/verify/verify-checklist.md"
copy_file "$FRAMEWORK_ROOT/templates/memory-entry.md" "$TARGET_DIR/docs/memory/memory-entry.md"
copy_file "$FRAMEWORK_ROOT/templates/loop-template.md" "$TARGET_DIR/docs/loops/loop-template.md"
copy_file "$FRAMEWORK_ROOT/templates/pr-template.md" "$TARGET_DIR/.github/pull_request_template.md"
copy_file "$FRAMEWORK_ROOT/examples/test-matrix.example.md" "$TARGET_DIR/docs/verify/test-matrix.md"
copy_file "$FRAMEWORK_ROOT/examples/loop-runbook.example.md" "$TARGET_DIR/docs/loops/bugfix-loop.md"

SKILL_SRC="$FRAMEWORK_ROOT/skills/ai-engineering-discipline"
SKILL_DST="$TARGET_DIR/.claude/skills/ai-engineering-discipline"
if [[ -d "$SKILL_DST" && "$FORCE" != "1" ]]; then
  echo "skip existing: $SKILL_DST"
else
  mkdir -p "$SKILL_DST"
  cp -R "$SKILL_SRC/." "$SKILL_DST/"
  echo "installed: $SKILL_DST"
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

echo
echo "Bootstrap complete."
echo "Next steps:"
echo "  1. Read $TARGET_DIR/CLAUDE.md"
echo "  2. Open Claude Code in the target project."
echo "  3. Say: Use ai-engineering-discipline to inspect this project and enter development."
echo "  4. The skill will create docs/memory/project-scan.md and guide Spec -> Loop -> Verify -> Memory."
