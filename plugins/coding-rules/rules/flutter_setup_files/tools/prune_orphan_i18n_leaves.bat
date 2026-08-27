@echo off
cd /d "%~dp0.."
call fvm dart run "%~dp0prune_orphan_i18n_leaves.dart" %*
