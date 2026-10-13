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

REM No redirect and no pipe: a redirect keeps the run silent until it ends, and a
REM pipe would report the FILTER's exit code, not phpunit's. --debug prints every
REM test as it starts and finishes. --log-events-text (PHPUnit 10+) makes phpunit
REM itself write the same lines to the log, so callers whose stdout capture through
REM nested .bat calls is unreliable (CI, agents) keep a trustworthy pass/fail
REM artifact. --colors=never: phpunit.xml enables colors, and the escape codes
REM would otherwise end up in the captured output.
call "vendor\bin\phpunit.bat" --colors=never --debug --log-events-text "%~dp0_last_test_run.log" %*
set "TESTRESULT=%ERRORLEVEL%"

cd /d "%~dp0"
endlocal & exit /b %TESTRESULT%
