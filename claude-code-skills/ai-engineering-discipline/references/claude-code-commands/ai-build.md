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

4. **Build the graph, then fill the spec yourself.** First read the source files the request touches (the scripts do not analyze code). **codebase-memory (a code knowledge-graph MCP) is REQUIRED — the verify gate blocks a code change without it (opt out only via `AI_DISCIPLINE_GRAPH_OPTIONAL=1`). The framework auto-runs it during verify and writes the blast radius to `docs/verify/impact-graph.md`. You can also call `detect_changes`/`explore` directly to get the affected interfaces and transitive callers, and fill the Impact Analysis from that blast radius — sanity-check it; the framework does not judge the graph's quality.** For a new project, build the graph as soon as the first source/test skeleton exists and use the requirement to define the initial unit tests. For an existing project, build/refresh the graph before implementation and use the impacted function/API/interface set to decide which tests must exist. Then open the generated `docs/specs/<slug>.md` and complete its `TBD` placeholders (requirements, impact analysis, acceptance criteria, test plan) — give a real Impact Analysis and fill `docs/memory/module-map.md` with the boundaries you found. Never hand `TBD`s back to the user.
5. **Write or update tests before implementation.** New project: create the requirement-driven test cases/unit tests first. Existing project: from the graph blast radius, refresh blind spots with `ai_discipline.py index .`, and for every requirement-touched or transitively affected interface with no guarding test, add the necessary test **before** editing implementation. After writing the tests and before editing implementation, record the red phase:
   ```bash
   "$PYTHON" .claude/skills/ai-engineering-discipline/scripts/ai_discipline.py execute . --record-red-phase
   ```
   This writes `docs/verify/red-phase-results.json` / `.md`; tests are expected to fail here. If they do not fail, fix the tests before implementation. Then implement following the loop until tests pass. For feature/bugfix/refactor/migration work you MUST add or update tests that actually exercise the changed code (referencing the changed functions/classes), and the final full test suite must pass. The gate blocks code changes with no test, unrelated tests, missing runnable tests, affected interfaces without guarding tests, missing required diff coverage, a missing knowledge graph, or a graph that returns no affected interface for changed business code. State the plan in one plain sentence before editing code, then proceed unless the user objects.
6. **Verify, then refresh the report** (so the pilot report isn't left showing a stale pre-verify snapshot):

   ```bash
   "$PYTHON" .claude/skills/ai-engineering-discipline/scripts/ai_discipline.py execute . --run-native-checks --run-diff-coverage --fail-on-verify-failure --fail-on-incomplete-coverage
   "$PYTHON" .claude/skills/ai-engineering-discipline/scripts/ai_discipline.py report .
   ```

   Read `docs/verify/verification-results.json` for `can_merge` / `coverage_complete` / blocking reasons.
7. **Report to the user in plain language only**: one short message — what you built, whether the tests pass, and anything not covered (e.g. "added delete-by-title with a test; all tests pass; the security scan isn't installed so it didn't run"). Do NOT show the user the generated spec/loop/verify/memory files, `TBD` placeholders, or terms like `can_merge`/`coverage_complete` — those are internal. Never present "done" as fully verified when `coverage_complete` is false. The framework auto-writes `docs/ai-engineering/SUMMARY.md` in plain language with the same facts — make your message match it (it is the fallback if you don't translate). Update memory only with durable lessons.

**If the request points to a folder of requirements** (many `.md` files and/or images, screenshots, diagrams, PDFs), pass that whole folder to `--requirements <folder>` instead of writing a new file in step 2. Then read every Markdown file and **visually inspect every image/PDF** in it to extract the requirements before filling the spec — image/PDF content is understood visually; the scripts only track the files.

Speak in plain language throughout — never in terms of Spec/Loop/Verify/Memory. Stop and ask only for real stop conditions: destructive operations, production data, credentials, permissions, or unresolvable conflicts.
