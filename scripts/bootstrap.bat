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

rem 与 bootstrap.sh 一致:复制任何文件前先校验 Python 3.9+,缺失则早失败,不留装一半的现场
set "PYTHON_CMD="
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -c "import sys; sys.exit(0 if sys.version_info[:2]>=(3,9) else 1)" >nul 2>nul
  if not errorlevel 1 set "PYTHON_CMD=py -3"
)
if not defined PYTHON_CMD (
  where python >nul 2>nul
  if not errorlevel 1 (
    python -c "import sys; sys.exit(0 if sys.version_info[:2]>=(3,9) else 1)" >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=python"
  )
)
if not defined PYTHON_CMD (
  echo Python 3.9+ is required ^(py -3 or python not found^). 1>&2
  exit /b 1
)

call :mkdir "%TARGET_DIR%\docs\specs"
call :mkdir "%TARGET_DIR%\docs\verify"
call :mkdir "%TARGET_DIR%\docs\memory"
call :mkdir "%TARGET_DIR%\docs\loops"
call :mkdir "%TARGET_DIR%\.github"
call :mkdir "%TARGET_DIR%\.github\workflows"
call :mkdir "%TARGET_DIR%\.claude\commands"
call :mkdir "%TARGET_DIR%\.claude\skills"
call :mkdir "%TARGET_DIR%\.codex\skills"

call :copy_file "%FRAMEWORK_ROOT%\CLAUDE.md" "%TARGET_DIR%\CLAUDE.md"
call :copy_file "%FRAMEWORK_ROOT%\templates\ai-discipline-config.json" "%TARGET_DIR%\.ai-discipline.json"
call :copy_file "%FRAMEWORK_ROOT%\templates\agents-template.md" "%TARGET_DIR%\AGENTS.md"
call :copy_file "%FRAMEWORK_ROOT%\templates\spec-template.md" "%TARGET_DIR%\docs\specs\spec-template.md"
call :copy_file "%FRAMEWORK_ROOT%\templates\verify-checklist.md" "%TARGET_DIR%\docs\verify\verify-checklist.md"
call :copy_file "%FRAMEWORK_ROOT%\templates\memory-entry.md" "%TARGET_DIR%\docs\memory\memory-entry.md"
call :copy_file "%FRAMEWORK_ROOT%\templates\loop-template.md" "%TARGET_DIR%\docs\loops\loop-template.md"
call :copy_file "%FRAMEWORK_ROOT%\templates\pr-template.md" "%TARGET_DIR%\.github\pull_request_template.md"
call :copy_file "%FRAMEWORK_ROOT%\templates\github-ai-discipline.yml" "%TARGET_DIR%\.github\workflows\ai-discipline.yml"
call :copy_file "%FRAMEWORK_ROOT%\templates\start-here.md" "%TARGET_DIR%\docs\AI_ENGINEERING_START_HERE.md"
call :copy_file "%FRAMEWORK_ROOT%\examples\test-matrix.example.md" "%TARGET_DIR%\docs\verify\test-matrix.md"
call :copy_file "%FRAMEWORK_ROOT%\examples\loop-runbook.example.md" "%TARGET_DIR%\docs\loops\bugfix-loop.md"
for %%S in (ai-engineering-discipline ai-spec ai-loop ai-verify ai-memory) do (
  call :copy_dir "%FRAMEWORK_ROOT%\skills\%%S" "%TARGET_DIR%\.codex\skills\%%S"
  call :copy_dir "%FRAMEWORK_ROOT%\claude-code-skills\%%S" "%TARGET_DIR%\.claude\skills\%%S"
)

if exist "%FRAMEWORK_ROOT%\claude-code-commands\" (
  for %%C in ("%FRAMEWORK_ROOT%\claude-code-commands\*.md") do (
    call :copy_file "%%~fC" "%TARGET_DIR%\.claude\commands\%%~nxC"
  )
)

call :write_project_rules "%TARGET_DIR%\docs\memory\project-rules.md"
call :write_module_map "%TARGET_DIR%\docs\memory\module-map.md"
call :write_pitfalls "%TARGET_DIR%\docs\memory\pitfalls.md"

rem 适配器安装失败不中断 bootstrap(框架文件已装好),但要像 bootstrap.sh 一样显式告警
if "%INSTALL_ADAPTERS%"=="1" (
  call :run_python "%FRAMEWORK_ROOT%\scripts\install_default_adapters.py" "%TARGET_DIR%" --execute
  if errorlevel 1 echo Warning: adapter install reported failures; review %TARGET_DIR%\docs\adapters\default-stack.md. 1>&2
) else (
  call :run_python "%FRAMEWORK_ROOT%\scripts\install_default_adapters.py" "%TARGET_DIR%"
)

echo.
echo Bootstrap complete.
echo Next steps:
echo   1. Read %TARGET_DIR%\docs\AI_ENGINEERING_START_HERE.md
echo   2. Open Claude Code in the target project.
echo   3. Run: /ai-start  (initialize and inspect)
echo   4. Build with one plain sentence, e.g.: /ai-build add a refund approval flow
echo   5. If setup looks wrong, run: /ai-doctor
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
if exist "%DST%" if "%FORCE%"=="1" call :maybe_backup "%SRC%" "%DST%"
copy /Y "%SRC%" "%DST%" >nul
echo installed: %DST%
exit /b 0

:maybe_backup
rem --force 覆盖用户可能自著的文件前,内容有变化才备份一份 .bak
set "BN=%~nx2"
if /i not "%BN%"=="CLAUDE.md" if /i not "%BN%"=="AGENTS.md" if /i not "%BN%"==".ai-discipline.json" exit /b 0
fc /b "%~1" "%~2" >nul 2>&1
if errorlevel 1 (
  copy /Y "%~2" "%~2.bak" >nul
  echo backup: %~2.bak
)
exit /b 0

:copy_dir
set "SRC=%~1"
set "DST=%~2"
if exist "%DST%\" if not "%FORCE%"=="1" (
  echo skip existing: %DST%
  exit /b 0
)
if exist "%DST%\" if "%FORCE%"=="1" rd /s /q "%DST%"
if not exist "%DST%\" mkdir "%DST%"
xcopy "%SRC%\*" "%DST%\" /E /I /Y >nul
for /d /r "%DST%" %%D in (__pycache__) do if exist "%%D" rd /s /q "%%D"
for /r "%DST%" %%F in (*.pyc) do if exist "%%F" del /q "%%F"
for /r "%DST%" %%F in (.DS_Store) do if exist "%%F" del /q "%%F"
echo installed: %DST%
exit /b 0

:run_python
rem 用前面已校验过的解释器(PYTHON_CMD 在文件复制前由 Python 3.9+ 检查解析得到)
%PYTHON_CMD% %*
exit /b %ERRORLEVEL%

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
  echo - Existing-project changes must include impact analysis and regression checks before implementation.
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
  echo ^| Module ^| Owner ^| Responsibility ^| Coupled With ^| Required Regression Checks ^| Boundary / Forbidden Dependencies ^|
  echo ^|---^|---^|---^|---^|---^|---^|
  echo ^| TBD ^| TBD ^| Describe responsibility ^| upstream/downstream modules, APIs, jobs, data stores ^| test command or manual check ^| describe forbidden dependencies ^|
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
