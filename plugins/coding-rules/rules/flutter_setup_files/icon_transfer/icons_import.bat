@echo off
REM Import changed icon sources and regenerate launcher icons when needed.
REM Usage: icons_import.bat [source folder] - asks when no folder is given.
setlocal
set "SOURCE=%~1"
if not defined SOURCE set /p "SOURCE=Folder with the changed icon files: "
if not defined SOURCE (
    echo ERROR: No source folder given.
    exit /b 1
)
set "SOURCE=%SOURCE:"=%"
python "%~dp0icon_transfer.py" import "%SOURCE%"
exit /b %ERRORLEVEL%
