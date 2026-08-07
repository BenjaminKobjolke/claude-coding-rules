@echo off
REM PHP Compatibility Checker (summary report)
REM Usage: tools\compat-check.bat [php-version]
REM Example: tools\compat-check.bat 8.5
REM
REM Uses PHPCompatibility to scan code for version-incompatible patterns
REM WITHOUT running the code. Safe static analysis.

if not exist "%~dp0php_upgrade_config.bat" (
    echo.
    echo ERROR: php_upgrade_config.bat not found.
    echo Copy php_upgrade_config.example.bat to php_upgrade_config.bat and set your paths.
    echo.
    exit /b 1
)
call "%~dp0php_upgrade_config.bat"
cd /d "%~dp0.."

if not exist "vendor\bin\phpcs.bat" (
    echo.
    echo PHPCompatibility not installed. Run:
    echo   composer require --dev phpcompatibility/php-compatibility
    echo.
    exit /b 1
)

set TARGET=%PHP_TARGET_VERSION%
if not "%1"=="" set TARGET=%1

echo.
echo ============================================
echo  PHP Compatibility Check
echo  Target PHP Version: %TARGET%
echo ============================================
echo.

%PHP_LEGACY_EXE% vendor/bin/phpcs --config-set installed_paths vendor/phpcompatibility/php-compatibility

%PHP_LEGACY_EXE% vendor/bin/phpcs --standard=PHPCompatibility ^
    --runtime-set testVersion %TARGET% ^
    --extensions=php ^
    --ignore=%SCAN_IGNORE% ^
    --report=summary ^
    -p ^
    %SCAN_DIRS%

echo.
echo ============================================
echo  For detailed report, run:
echo  tools\compat-check-detail.bat %TARGET%
echo ============================================
echo.
