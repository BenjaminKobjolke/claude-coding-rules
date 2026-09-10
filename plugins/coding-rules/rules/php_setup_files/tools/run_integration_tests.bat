@echo off
setlocal
REM Integration tests - every class extending ApiTestCase, which boots the Slim app
REM against a real MySQL database (see phpunit.xml). Pulls a fresh mirror of the
REM live DB first. Mandated by CODING_RULES.md; tests.bat remains the full runner.
call "%~dp0tests.bat" --testsuite integration %*
set "TESTRESULT=%ERRORLEVEL%"
endlocal & exit /b %TESTRESULT%
