@echo off
REM Machine-specific settings for the bats in tools\. Copy to config.bat (gitignored) and adjust.
REM Checkout of https://github.com/BenjaminKobjolke release-tool (run `uv sync` in it once).
set "RELEASE_TOOL_DIR=D:\GIT\BenjaminKobjolke\release-tool"
REM Section of release-tool\signing_profiles.ini used by tools\sign_exe.bat.
set "SIGNING_PROFILE=xida remote"
