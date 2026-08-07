@echo off
REM WordPress Coding Standards lint (report only).
REM Usage: tools\phpcs.bat [path]
REM        tools\phpcs.bat              - scan per phpcs.xml
REM        tools\phpcs.bat src\Foo.php  - scan one path
REM
REM Config: tools\phpcs.xml

cd /d "%~dp0.."

if not exist "vendor\bin\phpcs.bat" (
    echo PHPCS / WPCS not installed. Run:
    echo   composer require --dev squizlabs/php_codesniffer wp-coding-standards/wpcs phpcompatibility/phpcompatibility-wp dealerdirect/phpcodesniffer-composer-installer
    exit /b 1
)

if "%1"=="" (
    vendor\bin\phpcs --standard=tools\phpcs.xml
) else (
    vendor\bin\phpcs --standard=tools\phpcs.xml %1
)
