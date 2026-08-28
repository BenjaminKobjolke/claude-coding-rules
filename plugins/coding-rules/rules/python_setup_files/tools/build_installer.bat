@echo off
echo ========================================
echo  <App Name> - Build Installer
echo ========================================
echo.

:: Packages an ALREADY-BUILT dist folder into a single setup exe. Same split as
:: fman (build_windows.bat freezes, build_windows_installer.bat packages) - and
:: compile_exe.bat ends in `pause`, so it cannot be chained from here anyway.
::
:: Usage: build_installer.bat [--sign]
::   --sign  code-sign the app exe (before packaging) and the setup exe (after)
::           via the XIDA network-share handshake. Off by default: it needs the
::           //XIDA-SERVER share and takes ~5 minutes per binary, so plain local
::           test builds stay unsigned.

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

:: version_get.bat prints the full label <version>_<build>, so one uv call covers
:: both defines - split it rather than also shelling out to build_get.bat.
for /f "usebackq delims=" %%I in (`call "%~dp0version_get.bat"`) do set "LABEL=%%I"
for /f "tokens=1,2 delims=_" %%A in ("%LABEL%") do (
    set "VERSION=%%A"
    set "BUILD=%%B"
)
if "%VERSION%"=="" (
    echo ERROR: could not read the release label from tools\version_get.bat
    goto :fail
)

set "OUTFILE=%CD%\dist\<AppExe>Setup_%LABEL%.exe"
echo Version: %VERSION%   Build: %BUILD%
echo.

:: Sign the app exe BEFORE packaging - the signed binary is the one that has to
:: end up inside the installer.
if defined SIGN (
    call "%~dp0sign_exe.bat" "%APPDIR%\<AppExe>.exe" || goto :fail
)

"%MAKENSIS%" /DVERSION=%VERSION% /DBUILD=%BUILD% /DSRCDIR="%APPDIR%" /DOUTFILE="%OUTFILE%" "%CD%\installer\setup.nsi"
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
pause
endlocal
exit /b 0

:fail
popd
echo.
echo ========================================
echo  Build failed!
echo ========================================
echo.
pause
endlocal
exit /b 1
