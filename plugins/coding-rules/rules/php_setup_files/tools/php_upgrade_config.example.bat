@echo off
REM Copy this file to php_upgrade_config.bat and set your local paths.
REM Then add tools/php_upgrade_config.bat to .gitignore.
REM
REM All PHP upgrade runners (compat-check.bat, rector.bat, tests-php.bat)
REM source this file for per-project paths.

REM Legacy PHP binary used to RUN the PHPCompatibility scanner.
REM PHPCompatibility 9.3.5 itself cannot execute under PHP 8+, so keep an
REM old PHP available even when scanning code targeted at PHP 8.5.
set PHP_LEGACY_EXE=C:\path\to\php7.4\php.exe

REM Target PHP binary. The version your project runs in production / dev.
REM Used by rector.bat and tests-php.bat.
set PHP_TARGET_EXE=C:\path\to\php8.5\php.exe

REM Default scan target version (the PHP version compat-check.bat scans FOR).
set PHP_TARGET_VERSION=8.5

REM Directories (space-separated, relative to project root) that contain
REM PROJECT code — not vendored libs.
set SCAN_DIRS=src

REM Glob patterns to skip during the PHPCompatibility scan.
set SCAN_IGNORE=*/vendor/*,*/cache/*,*/node_modules/*
