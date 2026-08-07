@echo off
REM PHPUnit test runner.
REM Usage: tools\tests-php.bat [testsuite]
REM Example: tools\tests-php.bat Registration
REM
REM Defaults to PHPUnit 11 (latest). For projects migrating from PHPUnit 5-7,
REM swap the phar URL below to https://phar.phpunit.de/phpunit-9.phar — see
REM PHP_UPGRADE_TO_NEWER_VERSION.md step 6 for the typical churn.

if not exist "%~dp0php_upgrade_config.bat" (
    echo ERROR: php_upgrade_config.bat not found.
    echo Copy php_upgrade_config.example.bat to php_upgrade_config.bat and set your paths.
    exit /b 1
)
call "%~dp0php_upgrade_config.bat"
cd /d "%~dp0.."

if not exist "phpunit11.phar" (
    echo PHPUnit 11 phar not found. Downloading...
    powershell -Command "Invoke-WebRequest -Uri 'https://phar.phpunit.de/phpunit-11.phar' -OutFile 'phpunit11.phar'"
    if not exist "phpunit11.phar" (
        echo Failed to download PHPUnit. Get it manually from:
        echo   https://phar.phpunit.de/phpunit-11.phar
        exit /b 1
    )
)

echo.
echo ============================================
echo  PHPUnit Test Run
echo ============================================
echo.

if "%1"=="" (
    %PHP_TARGET_EXE% phpunit11.phar --colors=always
) else (
    %PHP_TARGET_EXE% phpunit11.phar --testsuite %1 --colors=always
)
