# Version
1

Increase this version number whenever this rule file changes.

# Python Windows Installer (NSIS)

Applies on top of `PYTHON_RULES.md` when the project ships a Windows installer.

## Windows Installer (NSIS)

Ship a single `…Setup.exe`, not a zipped folder. Use **NSIS** (`makensis`) — it is
the tool already in use across these projects, and a hand-written `.nsi` is ~100
lines. Do not reach for Inno Setup, WiX, or fbs: fbs generates its NSIS script for
you but drags in a whole build system, and a plain `uv run pyinstaller` project does
not need one.

Reusable pieces in `python_setup_files/`:

- `installer/setup.nsi.template` — the script; fill in app name, exe name, company.
- `tools/build_installer.bat` — packages an existing `dist/<App>/` into the setup exe.
- `tools/sign_exe.bat` — code-signs one exe via the XIDA network-share handshake.

Conventions:

- **Two separate bats, no chaining.** `tools/compile_exe.bat` freezes;
  `tools/build_installer.bat` packages and fails with "run compile_exe.bat first" if
  `dist/` is missing. Neither bat calls the other.
- **Version and build reach the installer as `/D` defines** from the bat
  (`/DVERSION= /DBUILD= /DSRCDIR= /DOUTFILE=`), never via the exe's version resource.
  A bare PyInstaller CLI build has no `--version-file`, so there is no resource to
  read — the bat owns the label. `tools/version_get.bat` already prints the full
  `<version>_<build>` label, so read it once and split on `_` rather than also
  calling `build_get.bat`.
- **Output** = `dist/<App>Setup_<version>_<build>.exe`, so the filename carries the
  release label (see `python/RELEASE.md`).
- **Exclude the app's own runtime files from the payload**:
  `File /r /x settings.json /x sessions.db "${SRCDIR}\*.*"`. PyInstaller builds into
  `dist/`, and every local test run of that exe drops its config and database right
  beside it. Without the exclusions the installer ships the developer's machine
  config and personal data to every user. Verify by listing the install directory
  after a test install — this is not theoretical, it happened.
- **Per-user install into `$LOCALAPPDATA` with `RequestExecutionLevel user`** whenever
  the app writes its data next to its own exe (the
  `DATA_ROOT = Path(sys.executable).parent` pattern). A `C:\Program Files` install
  cannot write there unelevated. Bonus: no UAC prompt at all.
- **Kill the running instance before install and uninstall**:
  `nsExec::Exec 'taskkill /F /IM "${EXENAME}"'`. Ships with Windows, needs no NSIS
  plugin, and a non-zero exit just means it was not running. Without it, upgrading
  while the app is open fails on a locked file.
- **Never delete user data on uninstall.** Remove the program files, shortcuts and
  the `HKCU\...\Uninstall\<App>` key; leave `settings.json` and the database. Use
  plain `RMDir` (not `/r`) on the install root so the folder survives when they do.
- **Registry** goes under `HKCU` (per-user install) with `DisplayName`,
  `DisplayVersion` = the full label, `Publisher`, `DisplayIcon`, `InstallLocation`,
  `UninstallString`, `EstimatedSize`.
- **Signing is opt-in** via `build_installer.bat --sign`, off by default: the XIDA
  handshake needs the `//XIDA-SERVER` share and takes ~5 minutes per binary, so local
  test builds stay unsigned. When on, sign the app exe **before** packaging (the
  signed binary must be the one inside) and the setup exe after. `sign_exe.bat` `cd`s
  into the release-tool checkout, so it must be handed an **absolute** path.
- **Test the installer silently**, no clicking: `Setup.exe /S`, then
  `Uninstall.exe /S`. Check the install dir contents, the Start Menu shortcut, the
  `HKCU` key, that the installed app can write its database, and that a reinstall
  over a running instance succeeds.

---
