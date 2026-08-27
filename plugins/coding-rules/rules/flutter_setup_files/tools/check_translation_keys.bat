@echo off
cd /d "%~dp0.."
call fvm dart run "%~dp0check_translation_keys.dart" %*
