@echo off
echo ========================================
echo  <App Name> - Build Installer
echo ========================================
echo.

:: Packages an ALREADY-BUILT dist folder into a single setup exe. Same split as
:: fman (build_windows.bat freezes, build_windows_installer.bat packages) - run
:: compile_exe.bat first, this bat only packages.
::
:: Usage: build_installer.bat [--sign]
::   --sign  code-sign the app exe (before packaging) and the setup exe (after)
::           via tools\sign_exe.bat (release-tool signing profile). Off by
::           default: it needs the signing server, so plain local test builds
::           stay unsigned.

setlocal
set "SIGN="
if /i "%~1"=="--sign" set "SIGN=1"

pushd "%~dp0.."
set "APPDIR=%CD%\dist\<AppExe>"

if not exist "%APPDIR%\<AppExe>.exe" (
    echo ERROR: %APPDIR%\<AppExe>.exe not found.
    echo Run tools\compile_exe.bat first.
    goto :fail
)

set "MAKENSIS=%ProgramFiles(x86)%\NSIS\makensis.exe"
if not exist "%MAKENSIS%" set "MAKENSIS=%ProgramFiles%\NSIS\makensis.exe"
if not exist "%MAKENSIS%" for %%I in (makensis.exe) do set "MAKENSIS=%%~$PATH:I"
if not exist "%MAKENSIS%" (
    echo ERROR: makensis.exe not found. Install NSIS: https://nsis.sourceforge.io/
    goto :fail
)

:: version_get.bat prints the release version (pyproject.toml), e.g. 0.1.4.
for /f "usebackq delims=" %%I in (`call "%~dp0version_get.bat"`) do set "VERSION=%%I"
if "%VERSION%"=="" (
    echo ERROR: could not read the release version from tools\version_get.bat
    goto :fail
)

set "OUTFILE=%CD%\dist\<AppExe>Setup_%VERSION%.exe"
echo Version: %VERSION%
echo.

:: Sign the app exe BEFORE packaging - the signed binary is the one that has to
:: end up inside the installer.
if defined SIGN (
    call "%~dp0sign_exe.bat" "%APPDIR%\<AppExe>.exe" || goto :fail
)

"%MAKENSIS%" /DVERSION=%VERSION% /DSRCDIR="%APPDIR%" /DOUTFILE="%OUTFILE%" "%CD%\installer\setup.nsi"
if errorlevel 1 goto :fail

if defined SIGN (
    call "%~dp0sign_exe.bat" "%OUTFILE%" || goto :fail
)

popd
echo.
echo ========================================
echo  Build OK: %OUTFILE%
echo ========================================
echo.
endlocal
exit /b 0

:fail
popd
echo.
echo ========================================
echo  Build failed!
echo ========================================
echo.
endlocal
exit /b 1
