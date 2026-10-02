# Version
1

Increase this version number whenever this rule file changes.

# Python Release Workflow

Applies on top of `PYTHON_RULES.md` when the project uses release tooling.

## Release Workflow

Set up the release system with `/release:setup`. Reusable pieces live in
`python_setup_files/`:

- `tools/release/build_number.py` — self-contained helper: manages the integer in
  `build_version.txt` (project root) and prints the `<version>_<build>` label
  (version from `pyproject.toml`). Actions: `get | increment | decrement | label`.
- `tools/build_get.bat`, `tools/build_increment.bat`, `tools/build_decrement.bat`,
  `tools/version_get.bat` — thin `uv run` wrappers over the helper.
- `CREATE_NEW_RELEASE.template.md` — fill-in-the-blanks for `docs/CREATE_NEW_RELEASE.md`.
- The Python stack recipe read by `/release:create-release-notes` lives in the shared
  `coding-rules/CREATE_RELEASE_NOTES.md` (`## Python / uv` section), not here.

Conventions:

- **Release label** = `<version>_<build>` (e.g. `0.1.0_22`). `version` is semver in
  `pyproject.toml` (bumped by hand); `build` is an integer in `build_version.txt`.
- **Release notes** = `release_notes/<version>_<build>/<locale>.json`. The actual
  text is the `notes` array. Author **only `en.json`**; generate other locales with
  a translation bat (mandatory — never skip).
- **Bundle `release_notes/` into the build** so the in-app view ships with the binary
  (PyInstaller: add to spec `datas` + `copy_metadata(<pkg>)`).
- **In-app view**: load all releases, sort **newest first**, show the latest first
  with Older/Newer navigation, fall back to `en.json` when a locale is missing.

---
