@echo off
echo ========================================
echo  Arduino Project - Run Host Tests
echo ========================================
echo.

:: Host-side unit tests: compiled and run with g++, no board required.
:: Logic lives in src/*.cpp; tests in test/*.cpp use mocks under test/mocks/.

:: Check if g++ is installed
where g++ >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ERROR: g++ is not installed or not in PATH
    echo Install a host C++ compiler (e.g. MSYS2 / MinGW-w64).
    pause
    exit /b 1
)

set OUT=%~dp0..\build_test\tests.exe
if not exist "%~dp0..\build_test" mkdir "%~dp0..\build_test"

echo Compiling host tests...
echo.
g++ -std=c++17 -I"%~dp0..\src" -I"%~dp0..\include" -I"%~dp0..\test\mocks" ^
    "%~dp0..\test\*.cpp" "%~dp0..\src\*.cpp" -o "%OUT%"
if %ERRORLEVEL% neq 0 (
    echo.
    echo ========================================
    echo  Test build failed!
    echo ========================================
    pause
    exit /b 1
)

echo Running tests...
echo.
"%OUT%"
if %ERRORLEVEL% neq 0 (
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
pause
