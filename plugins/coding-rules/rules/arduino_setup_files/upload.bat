@echo off
echo ========================================
echo  Arduino Project - Upload
echo ========================================
echo.

:: --- Adjust to your board and port ---
set FQBN=arduino:avr:uno
set PORT=COM3

:: Check if arduino-cli is installed
where arduino-cli >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ERROR: arduino-cli is not installed or not in PATH
    echo Install it: https://arduino.github.io/arduino-cli/latest/installation/
    pause
    exit /b 1
)

echo [1/2] Compiling sketch (FQBN: %FQBN%)...
arduino-cli compile --fqbn %FQBN% "%~dp0."
if %ERRORLEVEL% neq 0 (
    echo ERROR: Build failed - not uploading
    pause
    exit /b 1
)

echo.
echo [2/2] Uploading to %PORT%...
arduino-cli upload -p %PORT% --fqbn %FQBN% "%~dp0."
if %ERRORLEVEL% neq 0 (
    echo.
    echo ========================================
    echo  Upload failed!
    echo ========================================
    pause
    exit /b 1
)

echo.
echo ========================================
echo  Upload complete!
echo ========================================
echo.
pause
