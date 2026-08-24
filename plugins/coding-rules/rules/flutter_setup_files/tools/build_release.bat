@echo off
echo ========================================
echo  Flutter Project - Build Release APK
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

echo Building release APK...
echo.
fvm flutter build apk --release
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
echo Release APK location:
echo build\app\outputs\flutter-apk\app-release.apk
echo.
pause
