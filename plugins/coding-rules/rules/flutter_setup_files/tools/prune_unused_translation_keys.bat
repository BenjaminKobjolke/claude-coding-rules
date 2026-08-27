@echo off
cd /d "%~dp0.."
call fvm dart run "%~dp0prune_unused_translation_keys.dart" %*
