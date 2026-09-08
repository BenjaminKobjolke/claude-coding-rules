# graphify Knowledge Graph (optional addon)

[graphify](https://github.com/safishamsi/graphify) turns a code folder into a queryable
knowledge graph: classes, methods, calls, extends/implements, fan-in/fan-out, communities,
god nodes. The addon wires it into a project's `CODING_RULES.md` so the agent queries the
graph before grepping and refreshes it after every code change.

Rule source: `plugins/coding-rules/rules/ai_rules_addons/graphify.md` (versioned; copied
into the project by `/coding-rules:apply`). Refresh bat template:
`plugins/coding-rules/rules/ai_rules_addons/graphify_update.bat`.

Opt-in per project — `/coding-rules:apply` asks before adding it.

## Prerequisites

```
uv tool install graphifyy      # or: pip install graphifyy
graphify --version             # rules were verified against 0.9.51
```

## One-time setup (per project)

1. `/graphify claude install` — writes hooks + a generic CLAUDE.md section.
2. Windows only: fix the hook command in `.claude/settings.json` — backslash paths
   (`C:\\Users\\...\\graphify.EXE`) break under Git Bash; use forward slashes. Keep exactly two
   entries (`Bash|Grep`, `Read|Glob`).
3. First build, scoped and directed, from the repo root:
   ```
   /graphify <code-dir> --directed                 # src/  lib/  app/ ...
   /graphify application/ framework/ --directed    # several first-party dirs -> one merged graph
   ```
   Scope to the code dir, never the repo root: non-code files (docs, images, audio) force a
   paid LLM pass; a pure-code dir stays AST-only and free. `--directed` is required — without
   it fan-in and fan-out blend and god classes are invisible.
4. Move the generic CLAUDE.md section into `CODING_RULES.md` via `/coding-rules:apply`
   (graphify addon = yes) and pin the code dir in `CLAUDE.md` (e.g. "This project's
   `<code-dir>` is `lib/`").
5. gitignore `graphify-out/` and `<code-dir>/graphify-out/`.
6. Copy `graphify_update.bat` to `tools/`, set `CODE_DIR`.

Vendored code committed inside `<code-dir>` (bundled SDKs, sprite folders) is scanned like
your own code. Drop a `.graphifyignore` at the scan root before the first build; if the
graph already exists, rebuild with `graphify update --force` (see below).

## Folder layout

| Path | What it is |
|------|------------|
| `graphify-out/` (repo root) | The **live graph**: `graph.json`, `GRAPH_REPORT.md`, `graph.html`. The only one queries read. Must have `directed: true`. |
| `graphify-out/cache/` | AST cache written by the CLI refresh. Scratch. |
| `graphify-out/.graphify_root` | Absolute scan root of the last build. Overwritten by every `/graphify <path>` run. |
| `<code-dir>/graphify-out/` | Legacy AST cache from the skill build. Safe to delete. A `graph.json` in here means a bare `graphify update` ran without `GRAPHIFY_OUT` — delete that `graph.json`, keep `cache/`. |

## Querying

Run from the repo root — the graph is resolved relative to the current directory.

```
graphify query "how is X validated"     # BFS subgraph, first stop for codebase questions
graphify path "AuthModule" "Database"   # shortest path between two concepts
graphify explain "SomeClass"            # one node and its neighbours
graphify god-nodes --top 10             # architectural hubs
```

Coupling: high fan-**in** + low fan-out = healthy shared base. Fan-**out** above ~20 =
god-class risk. `GRAPH_REPORT.md` only for broad architecture review.

The graph knows structure, not business rules, response shapes or rendered output. It is a
snapshot — stale until refreshed.

## Refreshing after a code change

This is the step `AI_RULES.md` runs after every implementation. One command, no LLM, no API
key, seconds (1 s on a 360-node graph, ~12 s on 4,900 nodes):

```bash
GRAPHIFY_OUT="$PWD/graphify-out" graphify update "$PWD/<code-dir>"
```

PowerShell:

```powershell
$env:GRAPHIFY_OUT="$PWD\graphify-out"; graphify update "$PWD\<code-dir>"
```

What it does: re-extracts code (AST, cached), re-clusters, keeps community labels
(signature-validated; a changed community gets a hub name), preserves the doc nodes of the
last full build, inherits `directed: true` from the existing graph. Deleted files are
evicted. `No code-graph topology changes detected` is a successful no-op.

Both halves are mandatory:

- `GRAPHIFY_OUT` absolute — `graphify update` writes to `<path>/graphify-out/`. Without the
  override it creates a stray graph under `<code-dir>/graphify-out/` and the live graph goes
  stale.
- `<code-dir>` absolute — with a relative path every node id and `source_file` is
  re-anchored to the repo root; all nodes are replaced and all labels lost.

Multi-path graphs: `update` takes one path — run it once per scanned dir.

Verify (cheap): root `graph.json` has `directed: true`, node count did not collapse, no
`<code-dir>/graphify-out/graph.json` appeared.

`tools/graphify_update.bat` runs the same command plus a smoke test (`directed` flag, node
count, `god-nodes`, sample `query`). Use it outside AI sessions.

### When the CLI refresh is not enough

| Situation | Do |
|-----------|----|
| `refused to shrink` | Change really deleted code: `graphify update --force ...`. Never force a wrong path or wrong `GRAPHIFY_OUT`. |
| Doc changes (`docs/`, `*.md`) | CLI is code-only. Occasionally `/graphify <code-dir> --directed --update` (skill, costs LLM work). |
| Narrowed scope (`.graphifyignore` added) | `graphify update --force ...` with `GRAPHIFY_OUT`. |
| `graph.json` missing or corrupt | Full skill build `/graphify <code-dir> --directed`, in a subagent (skill loads a large instruction file). |

**Never delete the root `graph.json` before a CLI update.** With no existing graph the CLI
builds an **undirected** graph and the doc nodes are gone.

## Why not the skill rebuild after every change?

`/graphify <code-dir> --directed` is the full pipeline: skill load (~750 lines), detect,
full AST extraction, cluster, the agent hand-labels every community, HTML export, manifest.
Minutes, and LLM work per run. The CLI update does the same AST refresh in seconds and keeps
the labels. The skill flow is for first builds, doc changes and recovery only.

## Delegated checks (Codex / DeepSeek)

When the plan/DRY checks run through `codex exec` or `reasonix run`, the addon's
"graphify delegate preamble" is prepended to each prompt: it tells the delegate the graph
exists at the repo-root `graphify-out/`, to run graphify commands from the repo root, and to
`graphify query` before grepping. Harmless if the graph is not built yet.

## Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| `command not found` on every Bash/Read after install (Windows) | Backslash hook paths in `.claude/settings.json` — switch to forward slashes. |
| Queries return "not found" for code that exists | Dir not in scope. Rebuild as a multi-path merge with every first-party dir. |
| Hundreds of library classes as god nodes | Vendored code inside `<code-dir>` — `.graphifyignore` + `update --force`. |
| `<code-dir>/graphify-out/graph.json` exists | Bare `graphify update` ran. Delete that `graph.json`, keep `cache/`, refresh with `GRAPHIFY_OUT`. |
| Graph came back undirected | `graph.json` was deleted before a CLI update. Full skill build `--directed`. |
| PowerShell scrolling breaks after a build | ANSI output from `graspologic`; upgrade graphify or use Windows Terminal. |
