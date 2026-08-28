# Version
18

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

## Delegation backends (Codex / DeepSeek)

Some of the workflow steps below can be delegated to an external CLI instead
of being performed by the agent itself. Two backends are supported, and they
are **mutually exclusive** — at most one is enabled at a time:

- `<!-- codex: enabled -->` — delegate to Codex, running:
  `codex exec --dangerously-bypass-approvals-and-sandbox "<PROMPT>"`
- `<!-- deepseek: enabled -->` — delegate to DeepSeek, running:
  `reasonix run --auto "<PROMPT>"`
- Neither marker `enabled` (or no marker) — do NOT delegate; perform the same
  checks yourself via the listed fallback skills.

Read precedence if both markers somehow end up `enabled`: Codex wins, then
DeepSeek, then the self-fallback.

**Self-fallback in a subagent.** When neither backend is enabled, prefer
running each fallback skill in a subagent (Agent/Task tool, `general-purpose`
type) rather than inline — the skill's file reads and reasoning stay out of
the main context window. The subagent runs the skill and returns **only**
its summary (and the list of files it changed). Any file edits the skill
makes (plan file, code) persist, so the main agent picks them up.

Exceptions that MUST stay in the main context: `/plan:dry-checked` (it
reloads the adjusted plan INTO context) and restating the
Definition-of-Done / DRY gate aloud.

**Graphify preamble (optional).** If this project's `CODING_RULES.md` includes
the graphify addon, prepend its graphify delegate preamble to every `<PROMPT>`
below before invoking the backend CLI (see the graphify addon's "Delegated
checks" section). If the addon is not present, send `<PROMPT>` unchanged.

The markers are managed by `/coding-rules:codex on|off|status|test` and
`/coding-rules:deepseek on|off|status|test` (or set during
`/coding-rules:apply`). Do not flip them yourself without the user asking.

### Delegation contract (never let a delegate hang)

Applies to EVERY delegated `<PROMPT>` below, both backends. A delegate that
stops to ask a question blocks forever on stdin nobody can answer — these four
rules make that impossible and leave a debug trail when it happens anyway.

- **No questions.** Append this suffix to every `<PROMPT>` before sending it:

  > "Run fully non-interactively. NEVER ask a question and NEVER wait for
  > input. If anything is ambiguous, blocked, or you cannot complete the task,
  > do NOT stop to ask — write your questions and what blocked you into your
  > output file (the plan file, or the check file for steps that write one)
  > under a heading `## DELEGATE QUESTIONS`, then exit immediately. Always
  > write the required SUMMARY block, even on failure."

- **Timeout.** Run every delegate call with `timeout: 600000` (10 min, the
  Bash tool maximum). Never make an untimed delegate call.

- **Log.** Capture stdout+stderr to a log next to the plan file, named
  `<plan-file-path-without-.md>-<step>-delegate.log` where `<step>` is
  `plan-dry`, `convention`, `post-impl` or `graphify`; close stdin so a
  delegate that ignores the contract dies instead of blocking:

  ```
  codex exec --dangerously-bypass-approvals-and-sandbox "<PROMPT>" > "<log>" 2>&1 < /dev/null
  ```

  Overwrite the log per run. On any failure, report the log path to the user
  in one line — that is the debug handle.

- **Success check + fallback.** A delegated step counts as done only if its
  required SUMMARY block is present (`SUMMARY DRY`, `SUMMARY CONVENTION
  CHECK`, `SUMMARY GRAPHIFY`, or the post-implementation check file). Timeout,
  non-zero exit, missing SUMMARY, or a `## DELEGATE QUESTIONS` heading all
  count as failure. On failure: do NOT retry — report one line plus the log
  path, then run that step's `delegate disabled` branch (subagent). If the
  delegate wrote `## DELEGATE QUESTIONS`, answer those questions yourself in
  the fallback run, or surface them to the user if they need a decision.

## Feature / Change Workflow

After a plan is proposed and the user approves it, follow this chain. The DRY
gate is a precondition for implementing — not just an earlier step.

The approved plan must first exist as an explicit Markdown file. Pass that same
path to both plan-DRY commands.

```
plan approved

plan DRY check
  delegate enabled (codex or deepseek — run <PROMPT> via that backend's CLI, see Delegation backends above; prepend graphify preamble if applicable; obey the Delegation contract — no-questions suffix, timeout, log, SUMMARY check):
    <PROMPT> = "FULL PATH TO PLAN - Can you check the plan for DRY opportunities and if you find any, apply them to the original plan file. Only edit the plan file — do NOT modify any source code or implement the plan. Always add a summary at the end called SUMMARY DRY — if you made changes, describe what and why; if you found nothing, write 'No DRY opportunities found.'"
  delegate disabled:
    run /plan:dry <plan-file> in a subagent (see "Self-fallback in a
    subagent"); inline only if a subagent isn't available.

plan convention check
  delegate enabled (codex or deepseek — run <PROMPT> via that backend's CLI, see Delegation backends above; prepend graphify preamble if applicable; obey the Delegation contract — no-questions suffix, timeout, log, SUMMARY check):
    <PROMPT> = "FULL PATH TO PLAN $convention-check - If you want to make any changes, apply them to the original plan file. Only edit the plan file — do NOT modify any source code or implement the plan. Always add a summary at the end called SUMMARY CONVENTION CHECK — if you made changes, describe what and why; if you found nothing, write 'No convention issues found.'"
  delegate disabled:
    run /convention:check in a subagent (see note) — apply findings to the
    plan file

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
  delegate enabled (codex or deepseek — run <PROMPT> via that backend's CLI, see Delegation backends above; prepend graphify preamble if applicable; obey the Delegation contract — no-questions suffix, timeout, log, SUMMARY check):
    <PROMPT> = "Read FULL PATH TO CHANGED-FILES FILE and check ONLY the files listed there for DRY opportunities. Do not use git status or git diff to widen the scope — other sessions may have concurrent uncommitted changes. Do NOT modify any code. Write your suggestions to <plan-file-path-without-.md>-post-implementation-check.md (next to the plan, same naming as the changed-files file), overwriting the file if it already exists. Include for each finding the affected files and a short rationale. Always write the file, even if you found nothing — in that case write a SUMMARY block stating 'No DRY opportunities found.'"
    then read that post-implementation-check file, validate each finding, and apply the valid ones. Bring a finding to the user only if a question arises — otherwise apply silently.
  delegate disabled:
    run /dry:check <files from the changed-files file, as pathspec> in a
    subagent (see note)

Post-Feature Verification + Post-Implementation Code Analysis (project-specific, below)

refresh graphify graph — only if the graphify addon is present in this project's CODING_RULES.md
  NEVER run this rebuild yourself in the main context: the graphify skill loads a
  large instruction file and its build output into the window. Delegate it — the
  rules it must follow live in the graphify addon's "Refreshing after a code
  change" section, already copied into this project's CODING_RULES.md.
  delegate enabled (codex or deepseek — run <PROMPT> via that backend's CLI, see Delegation backends above; prepend graphify preamble if applicable; obey the Delegation contract — no-questions suffix, timeout, log, SUMMARY check):
    <PROMPT> = "Rebuild this project's graphify knowledge graph. Read the graphify section of CODING_RULES.md and follow its 'Refreshing after a code change' rules exactly, including the scope rules — rebuild at the scope the existing graph already has, never narrower. Run the graphify skill's directed rebuild from the repo root (/graphify <code-dir> --directed), writing to the root graphify-out/. Do NOT run a bare `graphify update`. If the graphify skill is not available to you, change nothing and reply exactly GRAPHIFY SKILL UNAVAILABLE. Otherwise end with a summary called SUMMARY GRAPHIFY stating the scan root built, whether graph.json has directed: true, and the node count before and after."
  delegate disabled:
    run the same rebuild in a subagent (see "Self-fallback in a subagent") with the
    same instructions; it returns only the SUMMARY GRAPHIFY block.
  then verify yourself — cheap, no skill load: root `graphify-out/graph.json` has
  `directed: true`, and `graphify-out/.graphify_root` matches the scope that was
  built. If the delegate replied GRAPHIFY SKILL UNAVAILABLE, or either check fails,
  redo the rebuild via the subagent branch.
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
- [ ] `/dry:check <session changed-files>` clean (scoped to the changed-files file, never bare; may run via subagent)
- [ ] `/verify:after-change` green (tests + analysis; may run via subagent)

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
  → /verify:after-change  (run in a subagent — see "Self-fallback in a
    subagent")
```

---

## Optional Addons

These live in `ai_rules_addons/` and are **not** always-on. Each is opt-in per project — ASK
the user whether they want it before wiring it into that project's `CODING_RULES.md`.

- [`ai_rules_addons/graphify.md`](ai_rules_addons/graphify.md) — graphify knowledge graph:
  scoped + directed AST build, folder layout, gitignore, and the query/refresh rules to paste
  into a project's `CODING_RULES.md`.
