@echo off
REM PHP Compatibility Checker (full per-file report)
REM Usage: tools\compat-check-detail.bat [php-version]

if not exist "%~dp0php_upgrade_config.bat" (
    echo ERROR: php_upgrade_config.bat not found.
    echo Copy php_upgrade_config.example.bat to php_upgrade_config.bat and set your paths.
    exit /b 1
)
call "%~dp0php_upgrade_config.bat"
cd /d "%~dp0.."

if not exist "vendor\bin\phpcs.bat" (
    echo PHPCompatibility not installed. Run: composer require --dev phpcompatibility/php-compatibility
    exit /b 1
)

set TARGET=%PHP_TARGET_VERSION%
if not "%1"=="" set TARGET=%1

echo.
echo ============================================
echo  PHP Compatibility Check - DETAILED
echo  Target PHP Version: %TARGET%
echo ============================================
echo.

%PHP_LEGACY_EXE% vendor/bin/phpcs --config-set installed_paths vendor/phpcompatibility/php-compatibility

%PHP_LEGACY_EXE% vendor/bin/phpcs --standard=PHPCompatibility ^
    --runtime-set testVersion %TARGET% ^
    --extensions=php ^
    --ignore=%SCAN_IGNORE% ^
    --report=full ^
    -p ^
    %SCAN_DIRS%
