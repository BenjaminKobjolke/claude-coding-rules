@echo off
REM TEMPLATE - replace before use (see FAST_TESTS.md):
REM   __LOCAL_DB__    local MySQL database name the mirror is written to (e.g. my_api)
REM   __LIVE_DB__     human name of the live DB, comments only
REM   __BACKUP_DIR__  folder holding the sqlbackup JSON configs, e.g. E:\[--Sync--]\Backups\my_api\sql
REM   __PROJECT__     JSON basename: __BACKUP_DIR__\__PROJECT__.json (live) + __PROJECT___local.json (local)
setlocal
REM Non-interactive: overwrite local '__LOCAL_DB__' with a fresh copy of the live
REM __LIVE_DB__ DB, via sqlbackup --copy (no mysql/mysqldump binaries needed).
REM Called by tests.bat before every phpunit run, and usable directly to refresh
REM the local mirror by hand. There is deliberately no confirm-prompt twin: tests.bat
REM drops and recreates this DB unattended anyway, and a prompt would hang any
REM non-interactive caller (see the no-pause rule in CODING_RULES.md).
REM Live/local DB credentials come from the JSON configs next to the live backups
REM (__BACKUP_DIR__\__PROJECT__.json / __PROJECT___local.json).

set "sqlbackup_dir=D:\GIT\BenjaminKobjolke\sql-backup"

REM cd /d (never bare 'cd d:' + 'cd <path>'): without /d cmd only sets the target drive's
REM current dir and stays on the active drive, so a C:-rooted shell never gets here at all.
REM The cd is still required: sqlbackup.bat runs `uv run sqlbackup`, which resolves its uv
REM project from the current directory.
cd /d "%sqlbackup_dir%"

REM Call by FULL PATH, never bare 'sqlbackup.bat': agent/non-interactive shells run with
REM NoDefaultCurrentDirectoryInExePath=1, which stops cmd searching the current directory,
REM so a bare name fails with "'sqlbackup.bat' is not recognized" even standing in its folder.
call "%sqlbackup_dir%\sqlbackup.bat" --copy --source "__BACKUP_DIR__\__PROJECT__" --target "__BACKUP_DIR__\__PROJECT___local" --force
set "exit_code=%ERRORLEVEL%"

cd /d "%~dp0"
endlocal & exit /b %exit_code%
