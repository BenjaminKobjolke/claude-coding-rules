# Flutter Windows Releases

Use this guide only when a Flutter project ships a Windows desktop release.
It produces a local, versioned NSIS installer; signing and publishing are
separate concerns.

## Prerequisites

- Run `fvm flutter doctor -v` and install the Visual Studio Desktop development
  with C++ workload if Windows support is missing.
- Install NSIS and make `makensis` available on `PATH`.
- Keep the project's Flutter version in `.fvmrc` and run all Flutter commands
  through FVM.

## Project setup

Generate the Windows host from the project root:

```bat
fvm flutter create --platforms=windows .
```

Set `BINARY_NAME` in `windows/CMakeLists.txt` to the desired executable name
and change the window title in `windows/runner/main.cpp`. Update the matching
metadata in `windows/runner/Runner.rc`.

Replace `windows/runner/resources/app_icon.ico` with a multi-resolution icon.
When ImageMagick is available, a source PNG can be converted with:

```bat
magick assets\icon\app_icon.png -define icon:auto-resize=256,128,64,48,32,16 windows\runner\resources\app_icon.ico
```

## Installer and build scripts

Keep `installer/installer.nsi` small: copy the complete
`build\windows\x64\runner\Release` directory, create Start Menu and
uninstall shortcuts, and provide an uninstaller. Use an install directory
under `$PROGRAMFILES64` and `RequestExecutionLevel admin`.

Provide two scripts in `tools/`:

- `build_windows.bat` runs `fvm flutter build windows` and reports the bundle.
- `build_windows_release.bat` calls that build, requires `makensis`, reads the
  `version:` value from `pubspec.yaml`, invokes NSIS, and renames the output
  to `<Product>_v<version>_<build>.exe` under `releases/windows/`.

Ignore `releases/`. Do not commit certificate files or publishing credentials.

## Verify

Run the normal analysis and tests, then:

```bat
tools\build_windows.bat
tools\build_windows_release.bat
```

Confirm the release bundle launches, platform-plugin features work, and the
installer creates working Start Menu and uninstaller shortcuts. Add code
signing only when distributing beyond trusted internal users.
