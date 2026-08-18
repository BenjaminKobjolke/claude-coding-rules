# Version
9

Increase this version number whenever this rule file changes.

# AI Workflow Rules (All Languages)

See `COMMON_RULES.md` for rules that apply to all languages.

Unlike the per-language `*_RULES.md` files, these rules are **language-independent** and
**always apply**. They are not subject to the "some rules may not apply to this project"
filtering — include them in every project's `CODING_RULES.md`.

These rules define the end-to-end workflow an AI agent must follow when planning and
implementing changes. Each step is an existing skill referenced by its slash name; run the
skill rather than reimplementing its behavior.

---

## Codex toggle

Some of the workflow steps below can be delegated to the Codex CLI. Whether a
project uses Codex is controlled by a marker near the top of `CODING_RULES.md`:

- `<!-- codex: enabled -->` — run the `codex exec` commands below.
- `<!-- codex: disabled -->` or no marker — do NOT run Codex; perform the same
  checks yourself via the listed fallback skills.

The marker is managed by `/coding-rules:codex on|off|status` (or set during
`/coding-rules:apply`). Do not flip it yourself without the user asking.

## Feature / Change Workflow

After a plan is proposed and the user approves it, follow this chain. The DRY
gate is a precondition for implementing — not just an earlier step.

The approved plan must first exist as an explicit Markdown file. Pass that same
path to both plan-DRY commands.

```
plan approved

plan DRY check
  codex enabled:
    codex exec --dangerously-bypass-approvals-and-sandbox "FULL PATH TO PLAN - Can you check the plan for DRY opportunities and if you find any, apply them to the original plan file. Only edit the plan file — do NOT modify any source code or implement the plan. Always add a summary at the end called SUMMARY DRY — if you made changes, describe what and why; if you found nothing, write 'No DRY opportunities found.'"
  codex disabled:
    /plan:dry <plan-file>

plan convention check
  codex enabled:
    codex exec --dangerously-bypass-approvals-and-sandbox "FULL PATH TO PLAN $convention-check - If you want to make any changes, apply them to the original plan file. Only edit the plan file — do NOT modify any source code or implement the plan. Always add a summary at the end called SUMMARY CONVENTION CHECK — if you made changes, describe what and why; if you found nothing, write 'No convention issues found.'"
  codex disabled:
    /convention:check — apply findings to the plan file

/plan:dry-checked    reload the DRY and convention adjusted plan

restate Definition-of-Done aloud

implement
  While implementing, keep the list of every file you created or modified in THIS
  session — you know it from your own edits; do NOT derive it from git (other
  sessions may have concurrent uncommitted changes). After implementing, write the
  list (one path per line) to a changed-files file next to the plan, named after it:
  <plan-file-path-without-.md>-changed-files.md
  (e.g. claude-plans/my-feature-changed-files.md). The plan file is unique per
  session, so concurrent sessions never collide.
  Include only source-code files. Exclude documentation and other non-code
  files (`.md`, plain-text docs, the plan file itself) — the DRY audit only
  looks at code.

post-implementation DRY audit — scope is ONLY the changed-files file above
  codex enabled:
    codex exec --dangerously-bypass-approvals-and-sandbox "Read FULL PATH TO CHANGED-FILES FILE and check ONLY the files listed there for DRY opportunities. Do not use git status or git diff to widen the scope — other sessions may have concurrent uncommitted changes. Do NOT modify any code. Write your suggestions to <plan-file-path-without-.md>-post-implementation-check.md (next to the plan, same naming as the changed-files file), overwriting the file if it already exists. Include for each finding the affected files and a short rationale. Always write the file, even if you found nothing — in that case write a SUMMARY block stating 'No DRY opportunities found.'"
    then read that post-implementation-check file, validate each finding, and apply the valid ones. Bring a finding to the user only if a question arises — otherwise apply silently.
  codex disabled:
    /dry:check <files from the changed-files file, as pathspec>

Post-Feature Verification + Post-Implementation Code Analysis (project-specific, below)

```

### DRY gate (precondition for implementing)

Do not write a single line until ALL are true. Restate this gate aloud at the
moment you start implementing — if you cannot, the gate is not cleared:

- [ ] `/plan:dry <plan-file>` adjusted that file and completed its Ponytail pass.
- [ ] `/plan:dry-checked <plan-file>` reloaded the same adjusted plan.
- [ ] `/convention:check` found the existing utilities/patterns to reuse.

The gate survives the `implement` step: if mid-implementation you add a new
helper, type, or pattern the gate would have caught, stop and re-clear it
before continuing.

### Definition of Done — restate aloud before implementing

Before the first edit, state in chat what "done" means for THIS change:

- [ ] Scope: <one line — what changes, what does not>
- [ ] Reuse: <existing function/component this builds on, with path>
- [ ] DRY gate cleared (above)
- [ ] `/dry:check <session changed-files>` clean (scoped to the changed-files file, never bare)
- [ ] `/verify:after-change` green (tests + analysis)

### Post-implementation DRY audit — paste-in template

Run `/dry:check` scoped to the session's changed-files file, then paste and fill:

```
DRY audit — <change name>
Changed files:     <list from the changed-files file, not git>
Duplication found: <none | describe>
Consolidated into: <shared fn/module + path | n/a>
Convention reused: <name + path>
Verdict:           <clean | needs rework>
```

---

## Bug-Fix Workflow

Bug fixes use a shorter variant (no plan-DRY phase):

```
bugs:fix
  → /verify:after-change
```

---

## Optional Addons

These live in `ai_rules_addons/` and are **not** always-on. Each is opt-in per project — ASK
the user whether they want it before wiring it into that project's `CODING_RULES.md`.

- [`ai_rules_addons/graphify.md`](ai_rules_addons/graphify.md) — graphify knowledge graph:
  scoped + directed AST build, folder layout, gitignore, and the query/refresh rules to paste
  into a project's `CODING_RULES.md`.
