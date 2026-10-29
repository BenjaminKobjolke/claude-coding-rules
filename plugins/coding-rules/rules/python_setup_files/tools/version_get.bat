@echo off
REM Print the release version (pyproject.toml [project] version).
uv run python "%~dp0release\version_number.py" get
