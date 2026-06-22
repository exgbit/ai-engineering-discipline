# AI Build (plain-language entry)

Deliver a finished, verified change from the user's plain-language request, without making them learn task types, risk, presets, or the Spec/Loop/Verify/Memory workflow.

Request: $ARGUMENTS

If `$ARGUMENTS` is empty, ask the user in one plain sentence what they want to build or fix, then proceed.

First check the framework is installed:

```text
.claude/skills/ai-engineering-discipline/scripts/run_request.py
```

If it does not exist, tell the user to run the framework bootstrap script first, then stop.

Otherwise follow the `ai-engineering-discipline` skill's "Default Entry: One Plain Sentence" flow:

1. **Infer, do not ask.** From the request, infer the task type (feature / bugfix / refactor / migration / docs / verify / memory) and a short name. Pick a `<slug>` from the name. Do not ask the user to choose these.
2. **Capture the requirement** by writing the request into `docs/requirements/<slug>.md`.
3. **Generate the scaffold** (substitute the inferred values):

   ```bash
   set -e
   if command -v python3 >/dev/null 2>&1; then PYTHON=python3; else PYTHON=python; fi
   "$PYTHON" .claude/skills/ai-engineering-discipline/scripts/ai_discipline.py run . \
     --task <inferred> --name "<inferred name>" --requirements docs/requirements/<slug>.md
   ```

4. **Read the code, then fill the spec yourself.** First read the source files the request touches (the scripts do not analyze code). Then open the generated `docs/specs/<slug>.md` and complete its `TBD` placeholders (requirements, impact analysis, acceptance criteria, test plan) from that understanding — give a real Impact Analysis and fill `docs/memory/module-map.md` with the boundaries you found. Never hand `TBD`s back to the user.
5. **Implement in small steps, with tests** following the generated loop. For feature/bugfix/refactor work you MUST add or update tests — the verification gate blocks a code change that ships without a matching test change. State the plan in one plain sentence before editing code, then proceed unless the user objects.
6. **Verify**:

   ```bash
   "$PYTHON" .claude/skills/ai-engineering-discipline/scripts/ai_discipline.py execute . --run-native-checks
   ```

   Read `docs/verify/verification-results.json` for `can_merge` and blocking reasons.
7. **Report to the user in plain language only**: one short message — what you built, whether the tests pass, and anything not covered (e.g. "added delete-by-title with a test; all tests pass; the security scan isn't installed so it didn't run"). Do NOT show the user the generated spec/loop/verify/memory files, `TBD` placeholders, or terms like `can_merge`/`coverage_complete` — those are internal. Never present "done" as fully verified when `coverage_complete` is false. Update memory only with durable lessons.

**If the request points to a folder of requirements** (many `.md` files and/or images, screenshots, diagrams, PDFs), pass that whole folder to `--requirements <folder>` instead of writing a new file in step 2. Then read every Markdown file and **visually inspect every image/PDF** in it to extract the requirements before filling the spec — image/PDF content is understood visually; the scripts only track the files.

Speak in plain language throughout — never in terms of Spec/Loop/Verify/Memory. Stop and ask only for real stop conditions: destructive operations, production data, credentials, permissions, or unresolvable conflicts.
