# Version
4

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
    codex exec --dangerously-bypass-approvals-and-sandbox "FULL PATH TO PLAN - Can you check the plan for DRY opportunities and if you find any, apply them to the original plan file. Add a summary at the end what you changed and why."
  codex disabled:
    /plan:dry <plan-file>

plan convention check
  codex enabled:
    codex exec --dangerously-bypass-approvals-and-sandbox "FULL PATH TO PLAN $convention-check - If you want to make any changes, apply them to the original plan file. Add a summary at the end what you changed and why."
  codex disabled:
    /convention:check — apply findings to the plan file

/plan:dry-checked    reload the DRY and convention adjusted plan

restate Definition-of-Done aloud

implement

post-implementation DRY audit
  codex enabled:
    codex exec --dangerously-bypass-approvals-and-sandbox "Check the files changed in this session (staged, unstaged, and untracked — use git status and git diff) for DRY opportunities. Do NOT modify any code. Write your suggestions to claude-plans/post-implementation-check.md, overwriting the file if it already exists. Include for each finding the affected files and a short rationale."
    then read claude-plans/post-implementation-check.md and discuss/apply the findings with the user
  codex disabled:
    /dry:check

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
- [ ] `/dry:check` clean
- [ ] `/verify:after-change` green (tests + analysis)

### Post-implementation DRY audit — paste-in template

Run `/dry:check`, then paste and fill:

```
DRY audit — <change name>
Changed files:     <list>
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
