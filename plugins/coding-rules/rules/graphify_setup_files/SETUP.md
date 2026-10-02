# Version
1

Increase this version number whenever this rule file changes.

# graphify Setup (One-time)

Ask the user whether to opt into graphify before following these setup steps.

## One-time setup

1. **Install the Claude Code integration** (writes a generic graphify section into `CLAUDE.md`
   plus PreToolUse hooks that consult the graph before grep/read):
   ```
   /graphify claude install
   ```
2. **Check `.claude/settings.json` for the Windows slash bug.** On Windows the installer writes
   the hook command with backslash paths, e.g. `C:\\Users\\<you>\\.local\\bin\\graphify.EXE`.
   Claude Code runs PreToolUse hooks through Git Bash, which strips the backslashes →
   `C:Users<you>.local...` → `command not found` on every Bash/Read/Glob. Fix: open
   `.claude/settings.json` and replace the backslashes in the hook `command`(s) with forward
   slashes — `C:/Users/<you>/.local/bin/graphify.EXE` (Git Bash accepts drive paths with `/`).
   Also dedupe: the installer may write a redundant backslash `Bash` entry alongside a correct
   `Bash|Grep` one — keep exactly two entries (`Bash|Grep`, `Read|Glob`), forward slashes.
   Then confirm it runs: `"C:/Users/<you>/.local/bin/graphify.EXE" hook-guard search`.
   Note: Claude Code may permission-block edits to `.claude/settings.json` — the user may need
   to explicitly request/approve the fix. Hooks written mid-session don't load until the user
   opens `/hooks` once or restarts the session.
   (Non-Windows hosts are unaffected — skip this step.)
3. **Build the first graph — scoped and directed.** Point it at the folder that holds the
   source code, NOT the repo root:
   ```
   /graphify <code-dir> --directed        # e.g. src/  app/  lib/  internal/
   ```
   - `<code-dir>` = the folder(s) with the code. Scoping keeps `vendor/`, `node_modules/`,
     build output, and tests out of the graph. A repo-root build drowns the signal in deps AND
     drags in non-code files (`docs/`, `*.md`, images, audio) that force the paid LLM pass — a
     scoped code-dir build stays AST-only and free (see the intro of
     `implementation_flow_addons/graphify.md`).
   - **If first-party code lives in MORE than one top-level dir (e.g. `application/` +
     `framework/`, `src/` + `lib/`), build ALL of them as one multi-path merged graph:**
     `/graphify application/ framework/ --directed`. Scoping to only one dir makes every class
     in the others invisible to every query — the graph then reports "not found" for code that
     exists, and the miss is indistinguishable from absence. (Real incident: a query for string
     sanitization helpers returned 61 irrelevant nodes because `FRK_StringHelper` lived in the
     unscanned `framework/` dir.) List the excluded siblings consciously, never by omission.
   - `--directed` is **required**. Without it the graph is undirected and total edge count blends
     incoming and outgoing — you cannot tell a healthy shared base (high fan-**in**) from a god
     class (high fan-**out**).
   - **Scoping does not exclude vendored code committed *inside* `<code-dir>`** (e.g.
     `application/libs/`, `src/vendor/`, a bundled third-party SDK) — those aren't
     gitignored, so graphify scans them and the graph drowns in someone else's classes
     instead of yours. Check `<code-dir>` for such folders before the first build; if
     any exist, add a `.graphifyignore` there first (see "In-tree vendored code" in `implementation_flow_addons/graphify.md`).
4. **Relocate the installer section.** Remove the generic graphify section the installer
   wrote into `CLAUDE.md`. Run `/coding-rules:apply` to copy both graphify
   rule files, then pin the real code dir explicitly in `CLAUDE.md` (for example,
   `This project's code directory is lib/`). See
   `implementation_flow_addons/graphify.md` for the usage rules.
5. **gitignore the output** — build artifacts + cache, never committed:
   ```
   graphify-out/
   <code-dir>/graphify-out/
   ```
6. **Copy the refresh bat.** Copy `graphify_update.bat` (in
   `implementation_flow_addons/`) into the project's `tools/` folder and set its `CODE_DIR` to the real
   code dir. It runs the no-AI live-graph refresh (see "Refreshing after a code change" in
   `IMPLEMENTATION_FLOW.md`)
   and then smoke-tests the root graph (`god-nodes` + a sample `query`). See "Manual refresh bat" in `implementation_flow_addons/graphify.md`.
