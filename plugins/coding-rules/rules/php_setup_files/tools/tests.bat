@echo off
setlocal
REM Full test suite. Refreshes the local DB mirror from live, then runs phpunit.
REM Set SKIP_DB_PULL=1 to reuse the existing local mirror (run_tests.bat does this:
REM the unit suite touches no database and must work offline).

if not "%SKIP_DB_PULL%"=="1" (
    call "%~dp0get_live_db.bat"
    if errorlevel 1 (
        echo Live DB copy failed - aborting before running tests.
        exit /b 1
    )
)

cd /d "%~dp0.."

REM Xdebug's develop mode costs ~12x on function calls and this suite is call-bound.
REM Apache keeps its own phpForApache.ini, so this does not affect debugging the app.
set "XDEBUG_MODE=off"

REM Redirect, never pipe: a pipe would report the FILTER's exit code, not phpunit's.
REM The log gives callers whose stdout capture through nested .bat calls is unreliable
REM (CI, agents) a trustworthy pass/fail artifact. --colors=never: phpunit.xml enables
REM colors, and the escape codes would otherwise end up in that file.
call "vendor\bin\phpunit.bat" --colors=never %* > "%~dp0_last_test_run.log" 2>&1
REM Capture BEFORE the type below - type resets ERRORLEVEL.
set "TESTRESULT=%ERRORLEVEL%"
type "%~dp0_last_test_run.log"

cd /d "%~dp0"
endlocal & exit /b %TESTRESULT%
