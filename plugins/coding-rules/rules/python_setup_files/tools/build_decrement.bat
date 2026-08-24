@echo off
REM Decrement the build number in build_version.txt (floored at 0) and print it.
uv run python "%~dp0release\build_number.py" decrement
