@echo off
REM Print the full release label <version>_<build> (version from pyproject.toml).
uv run python "%~dp0release\build_number.py" label
