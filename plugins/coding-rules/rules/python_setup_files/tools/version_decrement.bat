@echo off
REM Roll the last version segment in pyproject.toml back by one and print it.
uv run python "%~dp0release\version_number.py" decrement
