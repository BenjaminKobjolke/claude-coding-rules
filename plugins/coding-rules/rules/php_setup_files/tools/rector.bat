@echo off
REM Rector runner.
REM Usage: tools\rector.bat            - dry-run (preview changes only)
REM        tools\rector.bat process    - apply changes
REM
REM Config: tools\rector.php

if not exist "%~dp0php_upgrade_config.bat" (
    echo ERROR: php_upgrade_config.bat not found.
    echo Copy php_upgrade_config.example.bat to php_upgrade_config.bat and set your paths.
    exit /b 1
)
call "%~dp0php_upgrade_config.bat"
cd /d "%~dp0.."

if not exist "vendor\bin\rector" (
    echo Rector not installed. Run: composer require --dev rector/rector
    exit /b 1
)

if "%1"=="process" (
    echo Applying Rector deprecation fixes...
    %PHP_TARGET_EXE% -d memory_limit=2G vendor\bin\rector process --config=tools\rector.php --no-progress-bar
) else (
    echo Rector dry-run (preview only, no changes applied)...
    %PHP_TARGET_EXE% -d memory_limit=2G vendor\bin\rector process --dry-run --config=tools\rector.php --no-progress-bar
)
