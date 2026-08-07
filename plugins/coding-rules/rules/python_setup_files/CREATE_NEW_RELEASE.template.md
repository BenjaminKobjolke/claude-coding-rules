# Creating a New Release (template)

Copy this to `docs/CREATE_NEW_RELEASE.md` and fill in the `<...>` placeholders for
your project. It pairs with the `tools/` bats and `tools/release/build_number.py`
from `python_setup_files/`.

A release is identified by the label **`<version>_<build>`**, e.g. `0.1.0_22`:
- `version` (semver) — `pyproject.toml` `[project] version`, bumped by hand.
- `build` (integer) — `build_version.txt` at the project root.

## 1. Version & build number

```bat
tools\version_get.bat       :: prints <version>_<build>
tools\build_get.bat         :: prints the build number
tools\build_increment.bat   :: bump build before a release
tools\build_decrement.bat   :: undo
```

Bump the semver `version` in `pyproject.toml` by hand for feature/breaking changes.

## 2. Release notes + en.json

Create `release_notes/<version>_<build>/en.json` (the `notes` array is the text):

```json
{
  "version": "<version>",
  "build": <build>,
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
tools\build_increment.bat
tools\<build-bat>
```

## 5. In-app Release Notes view

Location: `<where in the app>`. Loads all releases newest-first, shows the latest
first with Older/Newer navigation, falls back to `en.json` when a locale is missing.
