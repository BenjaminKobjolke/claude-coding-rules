@echo off
echo ========================================
echo  Arduino Project - Build
echo ========================================
echo.

:: --- Adjust to your board ---
set FQBN=arduino:avr:uno

:: Check if arduino-cli is installed
where arduino-cli >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ERROR: arduino-cli is not installed or not in PATH
    echo Install it: https://arduino.github.io/arduino-cli/latest/installation/
    pause
    exit /b 1
)

echo Compiling sketch (FQBN: %FQBN%)...
echo.
arduino-cli compile --fqbn %FQBN% "%~dp0."
if %ERRORLEVEL% neq 0 (
    echo.
    echo ========================================
    echo  Build failed!
    echo ========================================
    pause
    exit /b 1
)

echo.
echo ========================================
echo  Build complete!
echo ========================================
echo.
pause
