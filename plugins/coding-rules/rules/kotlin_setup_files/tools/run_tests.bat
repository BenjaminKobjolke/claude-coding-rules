@echo off
echo ========================================
echo  Kotlin Project - Run Tests
echo ========================================
echo.

echo Running Gradle unit tests...
echo.
:: Keep Gradle output live so callers see test progress and long tasks do not look hung.
call "%~dp0..\run-gradle.bat" testDebugUnitTest --console=plain
set TESTRESULT=%ERRORLEVEL%

if %TESTRESULT% neq 0 (
    echo.
    echo ========================================
    echo  Some tests failed!
    echo ========================================
) else (
    echo.
    echo ========================================
    echo  All tests passed!
    echo ========================================
)
echo.
exit /b %TESTRESULT%
