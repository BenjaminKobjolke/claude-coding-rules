@echo off
echo ========================================
echo  Kotlin Project - Run Analysis
echo ========================================
echo.

:: lintKotlin requires the kotlinter plugin (see KOTLIN_RULES.md).
call "%~dp0..\run-gradle.bat" lintKotlin lintDebug --console=plain
exit /b %ERRORLEVEL%
