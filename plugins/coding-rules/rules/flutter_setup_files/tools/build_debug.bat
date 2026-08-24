@echo off
echo ========================================
echo  Flutter Project - Build Debug APK
echo ========================================
echo.

:: Check if fvm is installed
where fvm >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo ERROR: FVM is not installed or not in PATH
    echo Please install FVM first: https://fvm.app/documentation/getting-started/installation
    pause
    exit /b 1
)

echo Building debug APK...
echo.
fvm flutter build apk --debug
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
echo  Build successful!
echo ========================================
echo.
echo Debug APK location:
echo build\app\outputs\flutter-apk\app-debug.apk
echo.
pause
