# Creating a New Release (template)

Copy this to `docs/CREATE_NEW_RELEASE.md` and fill in the `<...>` placeholders for
your project. It pairs with the `tools/` bats and `tools/release/version_number.py`
from `python_setup_files/`.

A release is identified by its version **`<major>.<minor>.<patch>`**, e.g. `0.1.4` —
the `pyproject.toml` `[project] version`, which holds the **last shipped** version.
Each release bumps its last segment (`0.1.3` -> `0.1.4`); there is no build number.
To start a new minor or major line, set the version by hand after a release (e.g.
`0.2.0`); the next release then ships `0.2.1`.

## 1. Version

```bat
tools\version_get.bat         :: prints the version, e.g. 0.1.4
tools\version_increment.bat   :: bump the last segment before a release
tools\version_decrement.bat   :: undo
```

## 2. Release notes + en.json

Create `release_notes/<version>/en.json` (the `notes` array is the text):

```json
{
  "version": "<version>",
  "date": "YYYY-MM-DD",
  "title": "Short headline",
  "notes": ["First change", "Second change"]
}
```

**Author only `en.json`.**

## 3. Translate (DO NOT SKIP) ⚠️

Run `tools\<translation-bat>` to generate the other locales from `en.json`. This is
mandatory — without it non-English users see English.

## 4. Build the release

`release_notes/` is bundled into the build (e.g. PyInstaller spec `datas` +
`copy_metadata(<pkg>)`), so the in-app view ships inside the binary.

```bat
tools\version_increment.bat
tools\compile_exe.bat
tools\build_installer.bat
```

See **Windows Installer (NSIS)** in `python/INSTALLER.md` — `compile_exe.bat`
freezes, `build_installer.bat` packages; they are deliberately not chained.

## 5. In-app Release Notes view

Location: `<where in the app>`. Loads all releases, sorts them by version (numeric
segments, newest first), shows the latest first with Older/Newer navigation, falls
back to `en.json` when a locale is missing.
