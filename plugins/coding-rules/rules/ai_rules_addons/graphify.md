# Version
6

Increase this version number whenever this rule file changes.

# graphify Knowledge Graph (Optional Addon)

**Optional.** Before adding this to a project, ASK the user whether they want to use graphify.
Only wire it into the project's `CODING_RULES.md` if they say yes.

graphify turns a code folder into a queryable knowledge graph — god nodes, communities,
cross-file relationships, fan-in/fan-out. The build is AST-only: no LLM, no API cost. Use it to
orient before grep and to spot god classes.

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
     build output, and tests out of the graph. A repo-root build drowns the signal in deps.
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
   references with the actual `<code-dir>`. Keeping the version with the copied rules allows
   `/coding-rules:apply` to detect stale copies.
5. **gitignore the output** — build artifacts + cache, never committed:
   ```
   graphify-out/
   <code-dir>/graphify-out/
   ```

## Folder layout (know which is which)

- `graphify-out/` at the **project root** = the **live graph** (`graph.json`, `GRAPH_REPORT.md`,
  `graph.html`). The only one queries read. Keep it `directed=True`.
- `<code-dir>/graphify-out/` = **AST cache only** (`cache/`). Scratch that speeds re-extraction.
  Never the live graph under the documented flow. Do not query it.

## What the graph knows (and does not)

- Knows: code structure — classes, methods, calls, references, extends/implements, plus
  fan-in/fan-out and community / god-node structure.
- Does NOT know: business rules, API response shape, or rendered template/view output. It is a
  snapshot — stale until rebuilt. Constants referenced by string can appear as isolated nodes
  (AST limitation, not a missing dependency).

---

## Rules to paste into the project's CODING_RULES.md (only if the user opted in)

Prepend this file's `# Version` block and `# graphify Knowledge Graph (Optional Addon)` title
when copying the following sections.

### Using the graph

- For codebase questions, run `graphify query "<question>"` first when `graphify-out/graph.json`
  exists. `graphify path "<A>" "<B>"` for relationships; `graphify explain "<concept>"` for a
  focused node. These return a small scoped subgraph vs. reading GRAPH_REPORT.md or raw grep.
- Judge coupling by direction: high **fan-in** + low fan-out (shared base / constants / DTO) is
  healthy; high **fan-out** (>~20 outgoing deps) is god-class risk and a refactor signal.
- Read `graphify-out/GRAPH_REPORT.md` only for broad architecture review, or when
  query/path/explain do not surface enough context.

### Delegated checks (Codex / DeepSeek)

When this project delegates the plan/DRY/convention checks to an external CLI
(see `AI_RULES.md` "Delegation backends"), prepend this **graphify delegate
preamble** to the `<PROMPT>` before sending it to that backend:

```
Graphify: this project has a graphify knowledge graph. For any codebase
question, run `graphify query "<question>"` first (also `graphify path "<A>"
"<B>"`, `graphify explain "<concept>"`) instead of raw grep.
```

Prepend only — do not otherwise change the `<PROMPT>`. Harmless if the graph
is not built yet: `graphify query` simply returns nothing and the CLI falls
back to reading files.

### Refreshing after a code change

- After a feature or any code change, rebuild via the **directed skill flow**: re-run
  `/graphify <code-dir> --directed`, writing to the project-root `graphify-out/`.
- Do NOT use the bare `graphify update <code-dir>` CLI — it has no `--directed` flag and writes a
  full UNDIRECTED graph into `<code-dir>/graphify-out/` (wrong location), desyncing the live
  graph. If that stray graph appears, delete `<code-dir>/graphify-out/graph.json` (keep `cache/`).
- Verify after rebuild: `graph.json` has `directed: true` and lives in root `graphify-out/`.
  For a **multi-path merge**, also grep `graph.json` for a node-ID prefix belonging to a second
  scanned dir (e.g. `framework_`) to prove that dir actually landed — `directed: true` passes even
  if one dir silently dropped out of the merge.

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
3. Rebuild. A narrower corpus is a *smaller* graph, which trips the shrink guard (#479) — delete
   the stale `graphify-out/graph.json` first (keep `graphify-out/cache/`), then re-run
   `/graphify <code-dir> --directed`.
4. Verify: grep the vendored library's distinctive class name in the new `graph.json` — it
   should return only first-party code that *uses* the library (e.g. your own `FacebookManager`),
   never the library's own classes.
