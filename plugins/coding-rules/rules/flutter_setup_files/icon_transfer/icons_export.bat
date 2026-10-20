@echo off
REM Copy every editable icon source of the app into a folder for a designer.
REM Usage: icons_export.bat [target folder] - asks when no folder is given.
setlocal
set "TARGET=%~1"
if not defined TARGET set /p "TARGET=Target folder for the icon files: "
if not defined TARGET (
    echo ERROR: No target folder given.
    exit /b 1
)
set "TARGET=%TARGET:"=%"
python "%~dp0icon_transfer.py" export "%TARGET%"
exit /b %ERRORLEVEL%
