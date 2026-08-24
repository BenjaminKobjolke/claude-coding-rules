@echo off
REM PHPUnit test runner.
REM Usage: tools\run_tests.bat [testsuite]
REM
REM Assumes composer-installed PHPUnit (composer require --dev phpunit/phpunit).
REM WordPress plugin/integration tests additionally need the WP test suite
REM (see https://make.wordpress.org/core/handbook/testing/automated-testing/).

cd /d "%~dp0.."

if not exist "vendor\bin\phpunit.bat" (
    echo PHPUnit not installed. Run: composer require --dev phpunit/phpunit
    exit /b 1
)

echo.
echo ============================================
echo  PHPUnit Test Run
echo ============================================
echo.

if "%1"=="" (
    vendor\bin\phpunit --colors=always
) else (
    vendor\bin\phpunit --testsuite %1 --colors=always
)
