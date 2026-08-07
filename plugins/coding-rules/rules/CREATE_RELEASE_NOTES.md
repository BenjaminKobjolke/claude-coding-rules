# Release-notes recipes

Per-stack recipes read by the `/release:create-release-notes` command (defined in
`commands/release/create-release-notes.md`). Detect the project's stack from its root
marker, then use that stack's section below for the concrete commands, paths, and
schema. **The project's own `docs/CREATE_NEW_RELEASE.md` always wins** where it
disagrees with any of this.

Lives here (not under `commands/`) so it does not register as a slash-command.

## Shared rules (all stacks)

- **Author only `en.json`.** Every other locale comes from the project's translator bat
  — never hand-author a non-English file.
- **Anchor = the last shipped end-user release** — a `RELEASE` git commit/tag, store
  metadata, or the newest existing notes folder (stack-specific, see below). **Skip
  `INTERNAL` commits** (internal test builds: TestFlight, Play internal/beta, dev/test
  exe) when locating the anchor — they never reached end users, so they must not shrink
  the window of covered changes.
- List commits since the anchor plus uncommitted work (`git log`, `git status --short`,
  `git diff --stat`). If the project ships from multiple repos, do this for each repo
  listed in the project doc.

---

## Flutter

**Detect this stack:** root-level `pubspec.yaml` containing a Flutter SDK dependency.

### 1. Next version & build number

- Read the `version: <name>+<build>` entry in `pubspec.yaml`.
- Treat the build number as the last shipped build and create notes for
  `<current build + 1>`. Do not edit `pubspec.yaml` while authoring notes.
- Use the project's documented version/show and increment commands. The release build
  may own the increment; never increment twice.
- The user-facing release label is commonly `<version>_<next build>`. Follow the project
  document when the notes folder uses only the build number.

### 2. Anchor specifics

Prefer the last shipped `RELEASE` git tag or commit. If no release tag exists, use the
newest existing release-notes folder and identify the corresponding commit from Git
history. Inspect additional repositories only when the project document says they ship
together.

### 3. Release-notes subdirectory

Default path: `assets/release-notes/<next build>/en.json`. Follow the project document
if it defines a different path or folder label.

### 4. `en.json` schema

The `text` key contains the user-facing note. Keep it at most 400 characters.

```json
{
  "_hint_": "If the language has a formal and an informal way. Then use the informal way.",
  "_hint_2_": "All texts are for a habit tracking and productivity app. So the translations should be adjusted to this genre.",
  "_hint_text": "Maximum length is 400 characters; if it's too long, you must shorten it, even if that means not adhering 100% to the original language. Count the characters afterwards and adjust the length if its still too long.",
  "text": "Your release notes text here."
}
```

### 5. Reminders

- Only create `en.json`; run the translator batch named by the project document to
  generate other locales. If the combined release build owns translation, it is still
  safe to translate before building and the build will verify it.
- Flutter asset folders must be listed under `flutter.assets` in `pubspec.yaml`; use the
  project's documented asset updater when one exists.
- The in-app release-notes view is project-specific; consult `docs/CREATE_NEW_RELEASE.md`
  for its location and behavior.

---

## Python / uv

**Detect this stack:** root-level `pyproject.toml`.

Reusable templates for a project with no release system yet live in
`coding-rules/python_setup_files/` — copy them instead of reinventing. See
`python_setup_files/CREATE_NEW_RELEASE.template.md` for the full release process this
recipe is the notes-only slice of.

### 1. Next version & build number

Label = `<version>_<build>`. `version` is semver in `pyproject.toml` (bumped by hand);
`build` is an integer in `build_version.txt` = the **last shipped** build (`0` = nothing
shipped yet). Model is **bump first, ship next**: `/release:create-release` increments
the counter and ships that number.

```
tools\build_get.bat         :: current (last shipped) build, e.g. 21
tools\version_get.bat       :: <version>_<lastShippedBuild>
```

Author these notes for the **next** label = `<version>_<build_get + 1>` (e.g. if
`build_get` is `21`, the folder is `<version>_22`). `/release:create-release` does the
actual `build_increment` at build time. Edit `pyproject.toml` `version` by hand for a
semver bump.

### 2. Anchor specifics

Single repo by default. The anchor is usually the newest folder under `release_notes/`
(or a `RELEASE`-tagged commit if the project uses them):

```
git log --oneline <last-release-sha>..HEAD
git status --short
git diff --stat
```

If the project doc lists extra repos (backend, data server), gather their commits too
with `git -C <repo> log --oneline --since="<last-release-date>"` and fold user-visible
behavior into the same note.

### 3. Release-notes subdirectory

`release_notes/<version>_<build>/`, e.g. `release_notes/0.1.0_22/`.

### 4. `en.json` schema

The actual note is the **`notes`** array (one user-facing bullet per item):

```json
{
  "version": "0.1.0",
  "build": 22,
  "date": "YYYY-MM-DD",
  "title": "Short headline",
  "notes": [
    "First user-facing change",
    "Second user-facing change"
  ]
}
```

Keys are defined once in `app/release/schema.py` — don't hardcode them elsewhere (this
path is a project convention; confirm against the actual project).

### 5. Reminders

- **Only create `en.json`** — other languages come from the project's translator bat
  (runs the shared `GPT-json-translator` recursively over every `<label>/en.json`).
- The in-app view shows releases newest-first with Older/Newer navigation, and falls
  back to `en.json` when a locale is missing. Location is project-specific — see
  `docs/CREATE_NEW_RELEASE.md`.

---

## JavaScript / npm (+ Android)

**Detect this stack:** root-level `package.json`.

Fills in the concrete commands for an npm app (optionally with an Android/Capacitor
build).

### 1. Next version & build number

The `prebuild` hook bumps **both** `package.json` semver patch and Android
`versionCode` on every `npm run build`. So the next AAB ships as
`currentSemver+1patch` / `currentVersionCode+1`.

Next semver (current patch + 1):

```
node -e "const v=require('./package.json').version.split('.');console.log(v[0]+'.'+v[1]+'.'+(+v[2]+1))"
```

Next `versionCode`:

```
tools/build_number_show.bat
```

Directory name → `<nextSemver>_<nextBuildNumber>`, e.g. `1.0.7_1655`.

For a `--no-bump` build (rare) use the current semver as-is (it skips the
package-version bump); `versionCode` always bumps.

### 2. Anchor specifics

Anchor = the versionCode currently **live on the store**, not the latest local
`RELEASE` commit (a locally built version may never have been uploaded). `RELEASE`
commits are for end-user ships only — internal test builds (TestFlight, Play
internal/beta) use `INTERNAL` and are skipped when locating the anchor.

**2a-i. Determine `$APPSTORE_VERSIONCODE`**

1. If `$CLAUDE_PROJECT_DIR/appstore-versioncode.txt` is **missing**:
   - Ask: *"`appstore-versioncode.txt` is missing. What is the last versionCode uploaded to the appstore?"*
   - Write the integer to `appstore-versioncode.txt` (single line, no trailing whitespace).
2. Read the integer → `$APPSTORE_VERSIONCODE`.

**2a-ii. Detect stale file**

```
git log --oneline --grep="^RELEASE" -n 1
```

Parse the `+<N>` suffix (e.g. `RELEASE (android): 1.1.0+935` → `935`) →
`$LATEST_RELEASE_VERSIONCODE`. If it ≠ `$APPSTORE_VERSIONCODE`:

- Ask: *"Last `RELEASE` commit is `+$LATEST_RELEASE_VERSIONCODE` but `appstore-versioncode.txt` says `$APPSTORE_VERSIONCODE`. Was `+$LATEST_RELEASE_VERSIONCODE` uploaded?"*
- **Yes** → overwrite the file with `$LATEST_RELEASE_VERSIONCODE` and use it.
- **No** → keep the file, continue with the existing value.

**2a-iii. Anchor commit by versionCode**

```
git log --oneline -E --grep="^RELEASE.*\+${APPSTORE_VERSIONCODE}$" -n 1
git log -1 --format="%H %aI" <sha>
```

If zero matches: stop and ask the user to paste the anchor SHA. Do **not** fall back to
"latest RELEASE commit". Use the ISO timestamp as `$LAST_RELEASE_DATE`.

**2b/2c. Commits + uncommitted work**

This project may ship from **multiple repos** (configured in the project doc; the
`ai-chat` example uses `ai-chat`, `ai-chat-api` at `D:/wamp64/www/ai-chat-api`,
`ai-chat-data-server` at `D:/GIT/Intern/ai-chat-data-server`). For each repo:

```
git -C <repo> log --oneline <sha>..HEAD          # this repo: <sha>..HEAD
git -C <repo> log --oneline --since="$LAST_RELEASE_DATE"   # sibling repos
git -C <repo> status --short
git -C <repo> diff --stat
```

### 3. Release-notes subdirectory

`static/release-notes/<semver>_<buildNumber>/`, e.g. `static/release-notes/1.0.3_1638/`.
Legacy build-number-only folders (e.g. `1407`) still load, but new folders must use
`<semver>_<build>`.

### 4. `en.json` schema

```json
{
  "_hint_": "If the language has a formal and an informal way. Then use the informal way.",
  "_hint_2_": "All texts are for a AI chat app. So the translations should be adjusted to this genre. Example: Home in english should be translated to Start in german since a translation like Zuhause doesnt make sense for an app like this",
  "_hint_3_": "SUMMERA and SUMMERA AI are brand names and should not be translated",
  "_hint_text": "Maximum length is 400 characters; if it's too long, you must shorten it, even if that means not adhering 100% to the original language. Count the characters afterwards and adjust the length if its still too long.",
  "text": "Your release notes here"
}
```

The actual note is the single **`text`** field; the `_hint_*` fields steer the
translator (genre, brand glossary, informal tone, 400-char cap). Adjust the genre /
brand / length hints per project.

### 5. Reminders

- **Only create `en.json`** — other languages come from `tools/translator_app-release-notes.bat`.
- The in-app "What's New" screen shows the folder as `Version <semver> (<buildNumber>)` —
  get both halves right. Rendering details: `docs/frontend/WHATS_NEW.md`.

---

## Adding a new stack

No section above matches the detected stack? Ask the user: *"There's no reusable
release-notes recipe for `<lang>` yet. Add one so future projects in this stack inherit
it?"*

- **Yes** → append a new `## <Stack name>` section here, filled in from this project's
  `docs/CREATE_NEW_RELEASE.md`, using the same five-part shape as the sections above:
  1. **Detect this stack** — root marker file (e.g. `Cargo.toml` / `go.mod` / `pom.xml`).
  2. **Next version & build number** — where each lives and how to read/bump it; the
     resulting folder-label format (e.g. `<version>_<build>`).
  3. **Anchor specifics** — anything beyond the shared anchor rule above (extra repos,
     store-versionCode mechanics, etc.), plus the commands to list commits/uncommitted
     work since the anchor.
  4. **Release-notes subdirectory** — path + folder-name format.
  5. **`en.json` schema** — the exact JSON shape and which key holds the actual note
     text, plus the translator bat name and in-app view location.
  Show the new section to the user to confirm, then continue using it.
- **No** → proceed with **only** the project's `docs/CREATE_NEW_RELEASE.md`; do not save
  a recipe.

Either way the release notes still get created — the recipe is just a reusable default
for next time.
