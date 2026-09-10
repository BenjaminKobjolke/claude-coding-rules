@echo off
setlocal
REM Unit tests only - the suite that needs no database (see phpunit.xml).
REM Mandated by CODING_RULES.md; tests.bat remains the full runner.
REM No DB pull: the unit suite touches no database, so this works offline.
set "SKIP_DB_PULL=1"
call "%~dp0tests.bat" --testsuite unit %*
set "TESTRESULT=%ERRORLEVEL%"
endlocal & exit /b %TESTRESULT%
