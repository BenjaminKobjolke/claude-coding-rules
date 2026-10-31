@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
set "REPO_ROOT=%SCRIPT_DIR%..\.."
if exist "%REPO_ROOT%\tools\config.bat" call "%REPO_ROOT%\tools\config.bat"
if not defined SCREENSHOT_TOOL_DIR set "SCREENSHOT_TOOL_DIR=%USERPROFILE%\.automated-application-screenshots"
if not defined DEMO_ADMIN_PASSWORD (
    echo ERROR: Set DEMO_ADMIN_PASSWORD in tools/config.bat.
    exit /b 1
)
uv run --project "%SCREENSHOT_TOOL_DIR%" python "%SCRIPT_DIR%live_flutter.py" %*
exit /b %ERRORLEVEL%

