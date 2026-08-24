@echo off
REM WordPress Coding Standards auto-fix (fixes what is fixable, reports the rest).
REM Usage: tools\phpcbf.bat [path]
REM
REM Config: tools\phpcs.xml

cd /d "%~dp0.."

if not exist "vendor\bin\phpcbf.bat" (
    echo PHPCS / WPCS not installed. Run:
    echo   composer require --dev squizlabs/php_codesniffer wp-coding-standards/wpcs phpcompatibility/phpcompatibility-wp dealerdirect/phpcodesniffer-composer-installer
    exit /b 1
)

if "%1"=="" (
    vendor\bin\phpcbf --standard=tools\phpcs.xml
) else (
    vendor\bin\phpcbf --standard=tools\phpcs.xml %1
)
