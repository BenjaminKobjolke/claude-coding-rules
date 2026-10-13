@echo off
echo ========================================
echo  Flutter Project - Run Tests
echo ========================================
echo.

:: Check if fvm is installed
where fvm >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ERROR: FVM is not installed or not in PATH
    echo Please install FVM first: https://fvm.app/documentation/getting-started/installation
    exit /b 1
)

echo Running tests...
echo.

:: Run flutter test directly: its output streams live, one line per test
:: (--reporter expanded), and ERRORLEVEL below is flutter test's OWN exit code.
:: Never redirect the run into a file and `type` it afterwards - the script is
:: then silent for the whole run and a hanging test looks like a slow suite.
:: Never pipe it into findstr/grep either: the pipe's exit code is the
:: FILTER's, not flutter test's (a real failure can read as pass, or vice
:: versa), and findstr errors on lines over ~8191 chars.
:: To hide benign third-party log noise, filter live in PowerShell and hand
:: flutter test's exit code back - replace the line below with:
::   powershell -NoProfile -Command "fvm flutter test --reporter expanded | Where-Object { $_ -notmatch 'pattern1|pattern2' }; exit $LASTEXITCODE"
call fvm flutter test --reporter expanded
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
