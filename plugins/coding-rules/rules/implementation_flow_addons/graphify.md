# Version
13

Increase this version number whenever this rule file changes.

# graphify Knowledge Graph (Optional Addon)

**Optional.** Before adding this to a project, ASK the user whether they want to use graphify.
Only wire it into the project's `CODING_RULES.md` if they say yes.

graphify turns a code folder into a queryable knowledge graph — god nodes, communities,
cross-file relationships, fan-in/fan-out. Use it to orient before grep and to spot god classes.

**Keep the build AST-only (no LLM, no API cost) by scoping to the code dir.** graphify runs a
free deterministic AST pass on *code* files, but a separate **LLM pass** on every *non-code*
file — docs, `.md`, `.txt`, config `.yaml`, images (vision), audio/video (whisper). That pass
needs an LLM (Gemini key or the host agent) and costs tokens. A build scoped to a pure-code dir
(`lib/`, `src/`, `app/`) has zero non-code files, so it skips the LLM pass entirely and rebuilds
need no AI. A repo-root build (`/graphify .`) sweeps in `docs/`, `README.md`, icons, and sound
assets — forcing the LLM pass. **Always scope to the code dir; never build the repo root.**

---

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
     scoped code-dir build stays AST-only and free (see intro).
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
     any exist, add a `.graphifyignore` there first (see "In-tree vendored code" below).
4. **Relocate the `CLAUDE.md` section** the installer wrote: remove it from `CLAUDE.md` and
   instead add this file's `# Version` block and document title followed by the "Using" +
   "Refreshing" rules below to the project's `CODING_RULES.md`, replacing generic `.`/`src`
   references with the actual `<code-dir>`. **Pin the real code-dir explicitly** (e.g. a
   "This project's `<code-dir>` is `lib/`" line) so a later rebuild can't default to the repo
   root and trip the LLM pass. Keeping the version with the copied rules allows
   `/coding-rules:apply` to detect stale copies.
5. **gitignore the output** — build artifacts + cache, never committed:
   ```
   graphify-out/
   <code-dir>/graphify-out/
   ```
6. **Copy the refresh bat.** Copy `graphify_update.bat` (ships beside this file in
   `implementation_flow_addons/`) into the project's `tools/` folder and set its `CODE_DIR` to the real
   code dir. It runs the no-AI live-graph refresh (see "Refreshing after a code change" in
   `IMPLEMENTATION_FLOW.md`)
   and then smoke-tests the root graph (`god-nodes` + a sample `query`). See "Manual
   refresh bat" below.

## Folder layout (know which is which)

- `graphify-out/` at the **project root** = the **live graph** (`graph.json`, `GRAPH_REPORT.md`,
  `graph.html`). The only one queries read. Keep it `directed=True`.
- `graphify-out/cache/` at the project root = AST cache written by the CLI refresh (it runs
  with `GRAPHIFY_OUT` pointing at the root folder, see "Refreshing"). Scratch only.
- `<code-dir>/graphify-out/` = legacy AST cache from the skill build. Never the live graph
  under the documented flow; safe to delete. If a `graph.json` ever appears in there, a bare
  `graphify update` ran without `GRAPHIFY_OUT` — delete that `graph.json`, keep `cache/`.

## What the graph knows (and does not)

- Knows: code structure — classes, methods, calls, references, extends/implements, plus
  fan-in/fan-out and community / god-node structure.
- Does NOT know: business rules, API response shape, or rendered template/view output. It is a
  snapshot — stale until rebuilt. Constants referenced by string can appear as isolated nodes
  (AST limitation, not a missing dependency).

---

## Rules to paste into the project's CODING_RULES.md (only if the user opted in)

Prepend this file's `# Version` block and `# graphify Knowledge Graph (Optional Addon)` title
when copying the following sections. The flow-side sections (the delegate preamble and the
post-change refresh) live in `graphify_flow.md` and land in `IMPLEMENTATION_FLOW.md` instead —
opt into both files together.

### Using the graph

- For codebase questions, run `graphify query "<question>"` first when `graphify-out/graph.json`
  exists. `graphify path "<A>" "<B>"` for relationships; `graphify explain "<concept>"` for a
  focused node. These return a small scoped subgraph vs. reading GRAPH_REPORT.md or raw grep.
- Judge coupling by direction: high **fan-in** + low fan-out (shared base / constants / DTO) is
  healthy; high **fan-out** (>~20 outgoing deps) is god-class risk and a refactor signal.
- Read `graphify-out/GRAPH_REPORT.md` only for broad architecture review, or when
  query/path/explain do not surface enough context.

### Manual refresh bat (`tools/graphify_update.bat`)

Copied from the `graphify_update.bat` template beside this addon, adjusted (`CODE_DIR`).
Run it from anywhere — it `pushd`es to the repo root itself.

- **Does:** (1) the live-graph CLI refresh from "Refreshing after a code change" in
  `IMPLEMENTATION_FLOW.md` (sets `GRAPHIFY_OUT` to the root
  `graphify-out\`, passes the absolute code dir); (2) smoke test — prints the root
  graph's `directed` flag + node count, `god-nodes`, a sample `query`.
- **Does NOT:** re-extract docs (see "Doc changes" in `IMPLEMENTATION_FLOW.md`) or build a first graph — that is the
  skill flow (`/graphify <code-dir> --directed`).
- **When to use:** after a code change outside an AI session, or as a "is graphify still
  wired up?" check after cloning, a dependency change, or a graphify upgrade.

### In-tree vendored code — exclude it, scoping alone won't

`--directed`-scoping the build to `<code-dir>` keeps external `vendor/`/`node_modules/` out
automatically, but a **committed** third-party library living *inside* `<code-dir>` (a bundled
SDK, a copied library folder) is not gitignored, so graphify scans it like first-party code.
Symptom: god-nodes / oversized communities in `GRAPH_REPORT.md` whose class names belong to a
library, not the app (e.g. hundreds of `Facebook*`/`GraphNode*` nodes from an in-tree Facebook
SDK).

Fix once per project:

1. Spot the vendored folder(s) under `<code-dir>` (e.g. `application/libs/`). Committed
   **asset/sprite dirs** are the same kind of noise — bundled UI images (jQuery-UI/colorbox
   sprites, e.g. `extensions/backend/assets/images/`) aren't code but graphify still scans them;
   exclude them the same way.
2. Drop a `.graphifyignore` at the scan root (gitignore syntax, honored by default):
   ```
   # Vendored / third-party code + bundled assets — not our architecture, noise in the graph
   libs/
   ```
3. Rebuild with the CLI refresh plus `--force` — a narrower corpus is a *smaller* graph,
   which trips the shrink guard (#479):
   `GRAPHIFY_OUT="$PWD/graphify-out" graphify update --force "$PWD/<code-dir>"`.
   Do NOT delete `graphify-out/graph.json` first (see "Refreshing after a code change" in
   `IMPLEMENTATION_FLOW.md`: the CLI would rebuild
   it undirected and drop the doc nodes).
4. Verify: grep the vendored library's distinctive class name in the new `graph.json` — it
   should return only first-party code that *uses* the library (e.g. your own `FacebookManager`),
   never the library's own classes.
