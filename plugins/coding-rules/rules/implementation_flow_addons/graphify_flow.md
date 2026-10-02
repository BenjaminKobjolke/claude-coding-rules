# Version
2

Increase this version number whenever this rule file changes.

# graphify Flow Steps (Optional Addon)

**Optional.** The flow half of the graphify addon — opt into it together with
`graphify.md`, which carries the folder layout and query rules and lands in the
project's `CODING_RULES.md`. These two sections land in the project's
`IMPLEMENTATION_FLOW.md` because they are steps of the implementation flow, not code
conventions: an orchestrator that runs the flow itself must be able to ignore them.

---

### Delegated checks (Codex / DeepSeek)

When this project delegates the plan/DRY/convention checks to an external CLI
(see `IMPLEMENTATION_FLOW.md` "Delegation backends"), prepend this **graphify delegate
preamble** to the `<PROMPT>` before sending it to that backend:

```
Graphify: this project has a graphify knowledge graph, built at the repo-root
`graphify-out/graph.json`. Run all graphify commands FROM THE REPO ROOT (the
graph is resolved relative to the current directory). For any codebase question,
run `graphify query "<question>"` first (also `graphify path "<A>" "<B>"`,
`graphify explain "<concept>"`) instead of raw grep.
```

Prepend only — do not otherwise change the `<PROMPT>`. The cwd line matters:
`codex exec` / `reasonix run` inherit the caller's directory, and `graphify
query` reads `graphify-out/` relative to cwd — run from a subdir and it finds
nothing, silently degrading to grep. Harmless if the graph is not built yet:
`graphify query` returns nothing and the CLI falls back to reading files.

### Refreshing after a code change

- After a feature or any code change, refresh the live graph with the **CLI update**, run
  from the repo root. One command, no LLM, no API key, seconds:
  ```
  GRAPHIFY_OUT="$PWD/graphify-out" graphify update "$PWD/<code-dir>"
  ```
  PowerShell: `$env:GRAPHIFY_OUT="$PWD\graphify-out"; graphify update "$PWD\<code-dir>"`.
  It re-extracts code files (AST, cached), re-clusters, keeps the existing community labels
  (signature-validated; a changed community is hub-named), preserves the semantic (doc)
  nodes of the last full build, and inherits `directed: true` from the existing graph
  (graphify ≥ 0.9.x, #2342). Prints `No code-graph topology changes detected` when the
  change was a no-op for the graph.
- **Both halves of the command are mandatory.** `graphify update` writes to
  `<path>/graphify-out/`, so without the absolute `GRAPHIFY_OUT` it creates a second,
  stray graph under `<code-dir>/graphify-out/` and the live root graph goes stale. And
  the `<code-dir>` must be **absolute**: with a relative path node ids and `source_file`
  get re-anchored to the repo root, every node is replaced and all labels are lost.
- **Never delete the root `graph.json` before a CLI update.** With no existing graph
  the CLI builds an **undirected** one (nothing to inherit) and the doc nodes are gone.
  Missing or corrupt `graph.json` → full skill rebuild (`/graphify <code-dir> --directed`,
  in a subagent — the skill loads a large instruction file).
- **Multi-path merged graphs** (`application/ framework/`): `update` takes one path — run
  the command once per scanned dir. The reconcile keeps nodes outside the watched subtree.
- **Rebuild at the scope the existing graph already has**, never narrower. Check
  `graphify-out/.graphify_root`; it stays the absolute `<code-dir>` after a CLI update
  (the CLI writes the path exactly as passed). Record the intended scan root in the
  project's `CLAUDE.md` — `.graphify_root` holds an absolute path and `graphify-out/` is
  gitignored, so it cannot carry the scope across clones.
- **Shrink guard.** A deleted source file is evicted normally. If the CLI still refuses
  with `refused to shrink`, the change really removed code — re-run with `--force`. Never
  force to paper over a wrong path or a wrong `GRAPHIFY_OUT`.
- **Doc changes** (`docs/`, `*.md`) are not re-extracted by the CLI (code only). Run the
  skill's incremental flow `/graphify <code-dir> --directed --update` occasionally for
  those; it costs LLM work. **Keep `docs/` in** the graph — it is the prose that answers
  "how does X work"; excluding it via `.graphifyignore` leaves a graph a grep would match.
- Verify after refresh (cheap, no skill load): root `graph.json` has `directed: true`,
  the node count did not collapse, and no `<code-dir>/graphify-out/graph.json` appeared.
  For a **multi-path merge**, also grep `graph.json` for a node-ID prefix belonging to a
  second scanned dir (e.g. `framework_`) to prove that dir is still in the graph.

