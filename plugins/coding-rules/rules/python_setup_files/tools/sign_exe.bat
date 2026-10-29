@echo off
REM Sign a single exe in place with a named release-tool signing profile
REM (SIGNING_PROFILE in config.bat, a section of release-tool\signing_profiles.ini).
REM Usage: sign_exe.bat <absolute-path-to-exe>
REM The path must be ABSOLUTE: this script cd's into the release-tool checkout,
REM so a relative path would resolve against the wrong directory.
setlocal

REM The signer check runs Windows PowerShell 5.1 (Get-AuthenticodeSignature).
REM Launched from a PowerShell 7 parent, the inherited PSModulePath points at PS7
REM module dirs, and 5.1 then fails to load Microsoft.PowerShell.Security - the
REM signer check silently returns None. Clearing it lets 5.1 use its own defaults.
set "PSModulePath="
if "%~1"=="" (
    echo ERROR: no exe path given. Usage: sign_exe.bat ^<path-to-exe^>
    exit /b 1
)
if not exist "%~1" (
    echo ERROR: exe not found: %~1
    exit /b 1
)
if not exist "%~dp0config.bat" (
    echo ERROR: tools\config.bat not found. Copy tools\config_example.bat to tools\config.bat and adjust it.
    exit /b 1
)
call "%~dp0config.bat"
if not defined SIGNING_PROFILE (
    echo ERROR: SIGNING_PROFILE is not set in tools\config.bat.
    exit /b 1
)

cd /d "%RELEASE_TOOL_DIR%"
call uv run python -m release_tool sign "%~1" "%SIGNING_PROFILE%"
if errorlevel 1 (
    echo ERROR: signing failed for %~1
    exit /b 1
)
endlocal
exit /b 0
