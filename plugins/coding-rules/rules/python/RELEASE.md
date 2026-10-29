# Version
2

Increase this version number whenever this rule file changes.

# Python Release Workflow

Applies on top of `PYTHON_RULES.md` when the project uses release tooling.

## Release Workflow

Set up the release system with `/release:setup`. Reusable pieces live in
`python_setup_files/`:

- `tools/release/version_number.py` — self-contained helper: reads the
  `pyproject.toml` `[project] version` and bumps or rolls back its last segment.
  Actions: `get | increment | decrement`.
- `tools/version_get.bat`, `tools/version_increment.bat`,
  `tools/version_decrement.bat` — thin `uv run` wrappers over the helper.
- `CREATE_NEW_RELEASE.template.md` — fill-in-the-blanks for `docs/CREATE_NEW_RELEASE.md`.
- The Python stack recipe read by `/release:create-release-notes` lives in the shared
  `coding-rules/CREATE_RELEASE_NOTES.md` (`## Python / uv` section), not here.

Conventions:

- **Release label** = the version `<major>.<minor>.<patch>` (e.g. `0.1.4`), no build
  number. `pyproject.toml` holds the last shipped version; each release bumps the
  last segment (`release-tool create` with `versioning = semver`). For a new
  minor/major line, set e.g. `0.2.0` by hand; the next release ships `0.2.1`.
  Projects that already use `<version>_<build>` labels keep working, but new
  setups use semver.
- **Release notes** = `release_notes/<version>/<locale>.json`, no `build` key. The actual
  text is the `notes` array. Author **only `en.json`**; generate other locales with
  a translation bat (mandatory — never skip).
- **Bundle `release_notes/` into the build** so the in-app view ships with the binary
  (PyInstaller: add to spec `datas` + `copy_metadata(<pkg>)`).
- **In-app view**: load all releases, sort **newest first**, show the latest first
  with Older/Newer navigation; sort by the numeric version segments (`0.1.10`
  after `0.1.9`), never as strings, fall back to `en.json` when a locale is missing.

---
