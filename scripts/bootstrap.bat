@echo off
setlocal enabledelayedexpansion

if "%~1"=="" goto usage
if not "%~4"=="" goto usage

set "TARGET_DIR=%~1"
set "FORCE=0"
set "INSTALL_ADAPTERS=0"

shift
:parse_args
if "%~1"=="" goto parsed_args
if "%~1"=="--force" (
  set "FORCE=1"
) else if "%~1"=="--install-adapters" (
  set "INSTALL_ADAPTERS=1"
) else (
  goto usage
)
shift
goto parse_args
:parsed_args

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "FRAMEWORK_ROOT=%%~fI"

if not exist "%TARGET_DIR%\" (
  echo Target project does not exist: %TARGET_DIR% 1>&2
  exit /b 1
)

call :mkdir "%TARGET_DIR%\docs\specs"
call :mkdir "%TARGET_DIR%\docs\verify"
call :mkdir "%TARGET_DIR%\docs\memory"
call :mkdir "%TARGET_DIR%\docs\loops"
call :mkdir "%TARGET_DIR%\.github"
call :mkdir "%TARGET_DIR%\.claude\skills"
call :mkdir "%TARGET_DIR%\.codex\skills"

call :copy_file "%FRAMEWORK_ROOT%\CLAUDE.md" "%TARGET_DIR%\CLAUDE.md"
call :copy_file "%FRAMEWORK_ROOT%\templates\spec-template.md" "%TARGET_DIR%\docs\specs\spec-template.md"
call :copy_file "%FRAMEWORK_ROOT%\templates\verify-checklist.md" "%TARGET_DIR%\docs\verify\verify-checklist.md"
call :copy_file "%FRAMEWORK_ROOT%\templates\memory-entry.md" "%TARGET_DIR%\docs\memory\memory-entry.md"
call :copy_file "%FRAMEWORK_ROOT%\templates\loop-template.md" "%TARGET_DIR%\docs\loops\loop-template.md"
call :copy_file "%FRAMEWORK_ROOT%\templates\pr-template.md" "%TARGET_DIR%\.github\pull_request_template.md"
call :copy_file "%FRAMEWORK_ROOT%\templates\start-here.md" "%TARGET_DIR%\docs\AI_ENGINEERING_START_HERE.md"
call :copy_file "%FRAMEWORK_ROOT%\examples\test-matrix.example.md" "%TARGET_DIR%\docs\verify\test-matrix.md"
call :copy_file "%FRAMEWORK_ROOT%\examples\loop-runbook.example.md" "%TARGET_DIR%\docs\loops\bugfix-loop.md"
for %%S in (ai-engineering-discipline ai-spec ai-loop ai-verify ai-memory) do (
  call :copy_dir "%FRAMEWORK_ROOT%\skills\%%S" "%TARGET_DIR%\.codex\skills\%%S"
  call :copy_dir "%FRAMEWORK_ROOT%\claude-code-skills\%%S" "%TARGET_DIR%\.claude\skills\%%S"
)

call :write_project_rules "%TARGET_DIR%\docs\memory\project-rules.md"
call :write_module_map "%TARGET_DIR%\docs\memory\module-map.md"
call :write_pitfalls "%TARGET_DIR%\docs\memory\pitfalls.md"

if "%INSTALL_ADAPTERS%"=="1" (
  python "%FRAMEWORK_ROOT%\scripts\install_default_adapters.py" "%TARGET_DIR%" --execute
) else (
  python "%FRAMEWORK_ROOT%\scripts\install_default_adapters.py" "%TARGET_DIR%"
)

echo.
echo Bootstrap complete.
echo Next steps:
echo   1. Read %TARGET_DIR%\docs\AI_ENGINEERING_START_HERE.md
echo   2. Open Claude Code in the target project.
echo   3. Say: Use ai-engineering-discipline to inspect this project and enter development.
echo   4. Review docs\adapters\default-stack.md for Spec Kit / LangGraph / Semgrep / Mem0 status.
exit /b 0

:usage
echo Usage:
echo   scripts\bootstrap.bat ^<target-project-path^> [--force] [--install-adapters]
echo.
echo Installs the Spec / Verify / Memory + Loop framework into a target project.
exit /b 1

:mkdir
if not exist "%~1\" mkdir "%~1"
exit /b 0

:copy_file
set "SRC=%~1"
set "DST=%~2"
if exist "%DST%" if not "%FORCE%"=="1" (
  echo skip existing: %DST%
  exit /b 0
)
copy /Y "%SRC%" "%DST%" >nul
echo installed: %DST%
exit /b 0

:copy_dir
set "SRC=%~1"
set "DST=%~2"
if exist "%DST%\" if not "%FORCE%"=="1" (
  echo skip existing: %DST%
  exit /b 0
)
if not exist "%DST%\" mkdir "%DST%"
xcopy "%SRC%\*" "%DST%\" /E /I /Y >nul
echo installed: %DST%
exit /b 0

:write_project_rules
set "DST=%~1"
if exist "%DST%" if not "%FORCE%"=="1" (
  echo skip existing: %DST%
  exit /b 0
)
(
  echo # Project Rules
  echo.
  echo - Add project-specific architecture and coding rules here.
  echo - AI-generated code must include verification evidence before merge.
  echo - Repeated mistakes should be converted into memory entries or loop updates.
) > "%DST%"
echo created: %DST%
exit /b 0

:write_module_map
set "DST=%~1"
if exist "%DST%" if not "%FORCE%"=="1" (
  echo skip existing: %DST%
  exit /b 0
)
(
  echo # Module Map
  echo.
  echo ^| Module ^| Owner ^| Boundary ^|
  echo ^|---^|---^|---^|
  echo ^| TBD ^| TBD ^| Describe responsibility and forbidden dependencies ^|
) > "%DST%"
echo created: %DST%
exit /b 0

:write_pitfalls
set "DST=%~1"
if exist "%DST%" if not "%FORCE%"=="1" (
  echo skip existing: %DST%
  exit /b 0
)
(
  echo # Pitfalls
  echo.
  echo Record repeated bugs, failed assumptions, review findings, and incident lessons here.
  echo.
  echo ## Template
  echo.
  echo - Date:
  echo - Context:
  echo - Problem:
  echo - Rule / Lesson:
  echo - Verification to add next time:
) > "%DST%"
echo created: %DST%
exit /b 0
