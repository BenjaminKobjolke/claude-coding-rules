@echo off
REM Sign a single exe via the XIDA network-share handshake (reuses release-tool PreSigner).
REM Usage: sign_exe.bat <absolute-path-to-exe>
REM The path must be ABSOLUTE: this script cd's into the release-tool checkout,
REM so a relative path would resolve against the wrong directory.
REM ponytail: signing params hardcoded here, same values in every XIDA project.
REM           Factor them into a shared config only if they ever diverge.
REM PreSigner's default timeout of 300s is too short: the signing service has
REM returned a comparable exe at ~5min01s, i.e. right at the boundary. 1800s instead.
setlocal

REM PreSigner verifies the signer via Windows PowerShell 5.1 (Get-AuthenticodeSignature).
REM Launched from a PowerShell 7 parent, the inherited PSModulePath points at PS7
REM module dirs, and 5.1 then fails to load Microsoft.PowerShell.Security - the
REM signer check silently returns None and the poll loop waits out the whole
REM timeout. Clearing it lets 5.1 fall back to its own defaults.
set "PSModulePath="
if "%~1"=="" (
    echo ERROR: no exe path given. Usage: sign_exe.bat ^<path-to-exe^>
    exit /b 1
)
if not exist "%~1" (
    echo ERROR: exe not found: %~1
    exit /b 1
)

cd /d D:\GIT\BenjaminKobjolke\release-tool
call uv run python -c "from release_tool.pre_signer import PreSigner,PreSignConfig; from pathlib import Path; PreSigner(PreSignConfig(True, r'//XIDA-SERVER/SigningExecutables/', r'//XIDA-SERVER/SigningExecutables/signed', 'XIDA GmbH', timeout=1800)).process(Path(r'%~1'))"
if errorlevel 1 (
    echo ERROR: signing failed for %~1
    exit /b 1
)
echo Signed: %~1
endlocal
exit /b 0
