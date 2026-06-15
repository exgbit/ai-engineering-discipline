@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
call :run_python "%SCRIPT_DIR%execute_request.py" %*
exit /b %ERRORLEVEL%

:run_python
where py >nul 2>nul
if not errorlevel 1 (
  py -3 %*
  exit /b %ERRORLEVEL%
)
python %*
exit /b %ERRORLEVEL%
