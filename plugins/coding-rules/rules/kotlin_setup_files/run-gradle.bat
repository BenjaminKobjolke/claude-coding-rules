@echo off
if not defined JAVA_HOME (
    echo ERROR: JAVA_HOME must point to a JDK 17 or newer.
    exit /b 1
)
set PATH=%JAVA_HOME%\bin;%PATH%
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\gradle-heartbeat.ps1" %*
exit /b %ERRORLEVEL%
