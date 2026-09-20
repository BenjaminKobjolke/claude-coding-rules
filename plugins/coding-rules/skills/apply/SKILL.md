---
description: Copy the applicable coding rules (common, language-specific, project-type, addons) into this project's CODING_RULES.md and IMPLEMENTATION_FLOW.md, and add a pointer block to CLAUDE.md. Updates stale rule blocks by version. Use when setting up a project or refreshing its coding rules.
---

# Apply Coding Rules

The rule files ship with this plugin at `${CLAUDE_PLUGIN_ROOT}/rules/`. Do not ask the user for a rules folder path.

Rules are copied into **two** files in the project root:

- `CODING_RULES.md` — code quality and conventions. Everything except the flow sources below.
- `IMPLEMENTATION_FLOW.md` — the end-to-end implementation flow. Exactly two sources land here:
  `IMPLEMENTATION_FLOW.md` and, when the graphify addon is opted into,
  `implementation_flow_addons/graphify_flow.md`. The delegation markers live here too.

The split exists so an external orchestrator can be told to ignore the flow file wholesale while
`CODING_RULES.md` stays binding.

`CLAUDE.md` gets only a small versioned pointer block that mandates reading both files before code work. Do NOT inline full rules into `CLAUDE.md` and do NOT use `@import` for either file — Claude Code auto-expands imports, which would put the full rules in context every turn and defeat the purpose.

Always read `${CLAUDE_PLUGIN_ROOT}/rules/COMMON_RULES.md` and `${CLAUDE_PLUGIN_ROOT}/rules/IMPLEMENTATION_FLOW.md` first, regardless of language — they may contain updated instructions for handling the rule files.

## Phase A — Determine applicable rule files

- Always: `COMMON_RULES.md` and `IMPLEMENTATION_FLOW.md`
- Language-specific rules: `PHP_RULES.md`, `PYTHON_RULES.md`, `CSHARP_RULES.md`, `FLUTTER_RULES.md`, `SVELTE_RULES.md`, `SCSS_RULES.md`, `ARDUINO_RULES.md`, `AUTOHOTKEY_RULES.md`, `UNITY_CSHARP_RULES.md`, `WORDPRESS_RULES.md`
- Project-type rules: see `PROJECT_TYPES.md` for the overview, files in `project_type/`
- Supplemental rules: `DESIGN_RULES.md` — include when the project has a user interface
  (desktop, web, mobile, TUI); skip it for libraries, APIs, and headless tools
- Optional addon rules in `implementation_flow_addons/` — include only after the user opts in.
  graphify is two files opted into together: `implementation_flow_addons/graphify.md` and
  `implementation_flow_addons/graphify_flow.md`

If `<project>/coding-rules.json` already exists, read it: its `rules` map is the
prior selection (keys are paths relative to `rules/`, e.g. `PYTHON_RULES.md`,
`project_type/REST_API.md`). On a re-run, only ask the user about deltas
(newly-relevant languages/project types) instead of re-deriving the whole list.

Optional addon rules (`implementation_flow_addons/*.md`) are the one exception: re-ask
about every addon NOT already present in the `rules` map on every run, even
if a prior run's answer was "no". A previous decline is not durable consent
to skip asking forever — the user's needs change, and addons are cheap to
ask about. Once an addon is accepted and its key lands in `rules`, stop
asking (a present key is durable; treat removal from `CODING_RULES.md` as an
explicit opt-out signal instead of silently re-adding it).

## Delegation choice

The live `<!-- codex: ... -->` / `<!-- deepseek: ... -->` markers in
`IMPLEMENTATION_FLOW.md` are the source of truth — `/coding-rules:codex` and
`/coding-rules:deepseek` set them directly, and they, not the manifest, drive
the workflow. Resolve in this order:

1. **If `IMPLEMENTATION_FLOW.md` exists and already carries a delegation marker**
   (either backend `enabled`, or both `disabled`), pass `--delegation keep`.
   apply.py then preserves whatever the markers currently say — so a manifest
   whose `delegation` field drifted out of sync (e.g. a toggle skill from an
   older version that didn't update it) can never flip the live marker back.
   A pre-split project still carries the marker in `CODING_RULES.md`; apply.py
   reads it from there and moves it to `IMPLEMENTATION_FLOW.md`.
2. **Else if `<project>/coding-rules.json` exists with a `delegation` field**,
   reuse that value (`codex` / `deepseek` / `neither`) — do not re-ask.
3. **Else ask** the user: "Delegate the DRY and convention checks in this
   project to Codex, DeepSeek, or neither (Claude performs those checks
   itself)?" Map the answer to `codex`, `deepseek`, or `neither`.

Pass the resolved value to the `--delegation` flag below. apply.py rewrites the
manifest's `delegation` to the resolved value either way, so `keep` also
self-heals a drifted manifest.

## Fast path — `apply.py`

<!-- claude-code-only:start -->
Detect a Python interpreter: try `python --version`, then `python3`, then
`py`. If one works, use it to run the deterministic core instead of doing
Phases B–E by hand. Tell the user which interpreter was found, e.g. "Found
`python`, applying rules via apply.py." — this is the signal for whether the
fast path or the fallback ran.

```
python <plugin-root>/skills/apply/apply.py \
  --project <project-root> \
  --plugin-root <plugin-root> \
  --rules <comma-separated paths from Phase A, e.g. COMMON_RULES.md,IMPLEMENTATION_FLOW.md,PYTHON_RULES.md> \
  --delegation <codex|deepseek|neither|keep> \
  --python <detected interpreter> \
  --json
```

`<plugin-root>` is `${CLAUDE_PLUGIN_ROOT}`. This single call performs Phases
B, C, D, D2, and E (legacy migration, version-merged `CODING_RULES.md` and
`IMPLEMENTATION_FLOW.md`, `CLAUDE.md` pointer, delegation marker + permission
merge, and clearing any legacy per-project hook install)
and writes `<project>/coding-rules.json`. Parse the JSON report:

- `needs_user_decision` items (an unrecognized legacy block in `CLAUDE.md`, or
  a rule/pointer version conflict where the project's applied version is
  *higher* than the source) — surface each to the user and ask how to
  reconcile; the script left the file untouched so nothing is lost by asking.
- `errors` items (e.g. an unparsable `settings.json`) — report verbatim; the
  file was left untouched.
- Otherwise summarize what changed (which rule blocks were updated, pointer
  status, delegation, hook status) for the user.

Gotchas seen in practice:

- Python projects: recent `ruff format` (seen: 0.16) also reformats Python code
  blocks *inside Markdown*, so a plain `ruff format .` silently rewrites the
  managed `CODING_RULES.md`. The manifest still says the version is current, so a
  later apply run reports `unchanged` and never repairs it. Add
  `extend-exclude = ["*.md"]` under `[tool.ruff]` in `pyproject.toml` when
  scaffolding. To repair a mangled file: delete `CODING_RULES.md` and
  `coding-rules.json`, re-run apply.py with `--delegation keep`.
- A delegate can write `## DELEGATE QUESTIONS` about things that are not real
  blockers on a fresh project: the auto-generated plan filename not matching the
  plan's topic, and `graphify-out/graph.json` not existing yet. Say both up front
  in the prompt file for greenfield projects.
- With `--delegation codex|deepseek` on a fresh project, apply.py wrote the
  marker and the four permission entries but did NOT copy
  `tools/coding_rules_delegate.sh` / `.ps1`. After the run, check `tools/` and
  copy both from `rules/delegate_setup_files/` if missing.
- The manifest version comes from `rules/versions.json`, not the rule file's own
  `# Version` block. If they disagree (seen: `FLUTTER_RULES.md` block 7,
  versions.json 6), the manifest records the stale number — report it.

If no interpreter works, skip this fast path and use the fallback below
instead — tell the user: "No Python interpreter found (`python`/`python3`/`py`
all failed) — applying rules manually, apply.py not used."
<!-- claude-code-only:end -->

## Fallback (manual) — no Python interpreter available

Do Phases B–E below by hand, in order. Tell the user this path is running (see
the interpreter-detection note above) so it's clear `apply.py` was skipped.
This is also the only path when `claude-code-only` content is stripped for
non-Claude-Code agents (see `sync_skills.py`) — in that case the interpreter
check doesn't apply; just note "Running the manual coding-rules-apply flow."

## Phase B — Migrate legacy CLAUDE.md (idempotent)

If the project has a `CLAUDE.md`, scan it for legacy inlined rule blocks: a `# Version` line followed by a number, followed by a rule-document title that matches one of the shipped rule files (e.g. `# Common Rules (All Languages)`, `# Implementation Flow (All Languages)`, its pre-split title `# AI Workflow Rules (All Languages)`, `# PHP Rules`, …). A block ends at the next `# Version` line, the pointer block, or end of file.

- Move every recognized block verbatim into its destination file — `IMPLEMENTATION_FLOW.md` for the flow sources, `CODING_RULES.md` for everything else (create the file if missing).
- If a `# Version` block has an unrecognized title, ask the user before touching it — it may be a user-authored versioned section.
- Preserve every other line of `CLAUDE.md` untouched and in order.
- If `CLAUDE.md` contains coding-rule `@import` lines from an earlier run, delete them; their content lands in `CODING_RULES.md` via Phase C.

## Phase C — Version-merge into CODING_RULES.md and IMPLEMENTATION_FLOW.md

Each rule source starts with a `# Version` block. Include that block when copying rules into its
destination file. Route each source: `IMPLEMENTATION_FLOW.md` and
`implementation_flow_addons/graphify_flow.md` go to the project's `IMPLEMENTATION_FLOW.md`, every
other source to `CODING_RULES.md`. Both files are merged the same way, each with its own header. For every applicable source file, compare its version with the version in the corresponding copied rule block:

- If the copied block has no version or its version is lower than the source version, replace that copied block with the current applicable source content.
- If both versions are equal, leave the copied block unchanged.
- If the copied version is higher than the source version, do not overwrite it; ask the user how to reconcile the unexpected version.

Identify corresponding copied blocks by the rule document title that follows the version block. Keep all copied rule blocks deduplicated. On first creation, start each file with:

```markdown
<!-- Managed by /coding-rules:apply — do not edit rule blocks by hand -->
```

### Migrating a pre-split project (one-time, idempotent)

A project applied before the split has the flow inlined in `CODING_RULES.md`. Move it:

- The block titled `# AI Workflow Rules (All Languages)` (or already
  `# Implementation Flow (All Languages)`) moves verbatim into `IMPLEMENTATION_FLOW.md`; retitle
  the pre-split one, then version-merge it there as usual. Any user-authored tail below it stays
  in place.
- The graphify addon needs no hand-splitting: the two new sources carry the sections between them,
  so a plain version-merge of `implementation_flow_addons/graphify.md` (v13) into `CODING_RULES.md`
  plus `implementation_flow_addons/graphify_flow.md` (v1) into `IMPLEMENTATION_FLOW.md` lands the
  content in the right files.
- Any `<!-- codex: … -->` / `<!-- deepseek: … -->` marker in the `CODING_RULES.md` header moves to
  the `IMPLEMENTATION_FLOW.md` header; strip it from `CODING_RULES.md`.
- Rename the manifest keys `AI_RULES.md` → `IMPLEMENTATION_FLOW.md` and `ai_rules_addons/…` →
  `implementation_flow_addons/…` so a migrated project reports `unchanged`, not a full re-apply.

### Tailored blocks and user-authored sections

- When you tailor a copied rule block to the project (trim inapplicable sections,
  substitute real paths/dirs, apply an addon's paste-form), insert `<!-- tailored -->`
  on its own line directly after the block's title heading. `apply.py` never
  auto-overwrites a tailored block: a newer source version is reported as
  `tailored-stale` in `needs_user_decision`, and you hand-merge the source changes
  into the tailored copy (then bump the block's version to match the source).
  `apply.py` reads the applied version from `coding-rules.json`, not from the block —
  so after a hand-merge also bump that rule's version in the manifest, otherwise the
  next run still reports `tailored-stale`. Re-run `apply.py` to confirm it comes back
  `unchanged`.
- A tailored addon usually has tailored **setup files** too (e.g.
  `tools/graphify_update.bat` from `implementation_flow_addons/`). `apply.py` never touches those —
  diff the project copy against the template on a `tailored-stale` merge and re-copy it,
  re-applying the project's substitutions (`CODE_DIR`, paths).
- User-authored top-level sections after the last managed block (project deviations,
  project-specific rules, …) are preserved by `apply.py` when a block is replaced —
  any heading the source doc doesn't contain starts preserved content, reported per
  rule under `preserved`. Verify preserved titles look intentional, not stale rule
  leftovers.

## Phase D — Pointer block in CLAUDE.md

Merge the following pointer block into the project's `CLAUDE.md` using the same version rules as Phase C (matched by the title `# Coding Rules (Pointer)`). Insert it at the top of `CLAUDE.md` when absent; create `CLAUDE.md` if the project has none. Copy it verbatim:

```markdown
# Version
2

# Coding Rules (Pointer)

This project's rules live in two files in the project root:

- `CODING_RULES.md` — code quality and conventions. BINDING for all code work in
  this repository, always.
- `IMPLEMENTATION_FLOW.md` — the end-to-end flow to follow when planning and
  implementing a change (checks, gates, Definition of Done).

MANDATORY: Before writing or editing ANY code, you MUST Read BOTH files in full
**in the current session**. Do not rely on memory of a previous session, a
summary, or partial reads.

If you are about to make a code change and have not read both files in this
session: STOP, read them, then continue.

An external tool may orchestrate the implementation itself. When a skill or run
states that the implementation is orchestrated, ignore `IMPLEMENTATION_FLOW.md`
entirely — the orchestrator runs those steps as its own phases. `CODING_RULES.md`
stays binding either way.

Do not inline rules back into this file and do not use `@import` for either file —
they are intentionally referenced, not imported.
```

<!-- claude-code-only:start -->
## Phase D2 — Delegation backend toggle (idempotent)

The implementation flow can delegate DRY/convention checks to Codex or DeepSeek
(see the Delegation backends section in `IMPLEMENTATION_FLOW.md`). State is a
marker near the top of `IMPLEMENTATION_FLOW.md`: `<!-- codex: enabled/disabled -->` and
`<!-- deepseek: enabled/disabled -->`. The two are mutually exclusive — at
most one is `enabled`.

Use the choice from the "Delegation choice" step above (do not re-ask here):

Both backends are invoked through the same wrapper script, so both install the
same two files and the same four permission entries:

- copy `${CLAUDE_PLUGIN_ROOT}/rules/delegate_setup_files/coding_rules_delegate.sh`
  and `.ps1` into `<project>/tools/` (create it if missing; overwrite — verbatim
  templates),
- merge `"Bash(tools/coding_rules_delegate.sh:*)"`,
  `"Bash(./tools/coding_rules_delegate.sh:*)"`,
  `"PowerShell(tools/coding_rules_delegate.ps1:*)"` and
  `"PowerShell(./tools/coding_rules_delegate.ps1:*)"` into
  `<project>/.claude/settings.local.json` `permissions.allow` per that skill's
  merge rules.

- Codex → follow the `on` steps of `${CLAUDE_PLUGIN_ROOT}/skills/codex/SKILL.md`
  (insert `<!-- codex: enabled -->` after the managed-by comment, verify
  `codex --version`, install the wrapper + permissions above, and insert
  `<!-- deepseek: disabled -->`).
- DeepSeek → follow the `on` steps of
  `${CLAUDE_PLUGIN_ROOT}/skills/deepseek/SKILL.md` (insert
  `<!-- deepseek: enabled -->` after the managed-by comment, verify
  `reasonix --version`, install the wrapper + permissions above, and insert
  `<!-- codex: disabled -->`).
- Neither → insert `<!-- codex: disabled -->` and `<!-- deepseek: disabled -->`
  after the managed-by comment.
- If a marker for the chosen backend is already `enabled`, still (re-)run that
  backend's wrapper copy and permission merge — idempotent, and picks up
  wrapper/permission changes shipped in newer plugin versions.
<!-- claude-code-only:end -->

<!-- claude-code-only:start -->
## Phase E — Reminder hooks (nothing to install)

The reminder hooks ship with the plugin (`${CLAUDE_PLUGIN_ROOT}/hooks/hooks.json`
+ `hooks/coding-rules-reminder.py`), so they are already active in every project
— no copy into `<project>/.claude/`, no `settings.json` entry. The script gates
itself: it stays silent unless the project has a `CODING_RULES.md`, and silent
while `<project>/.claude/hooks/coding-rules-reminder.off` exists
(`/coding-rules:hooks off`). It resolves the project from `$CLAUDE_PROJECT_DIR`,
falling back to walking up from the session cwd, so a subfolder cwd is fine.

This phase only cleans up the old per-project install, if present:

1. Delete `<project>/.claude/hooks/coding-rules-reminder.py`.
2. In `<project>/.claude/settings.json`, remove every hook whose command
   contains `coding-rules-reminder` (and any entry or event array left empty by
   that removal). Preserve every other key and entry. If the file is not valid
   JSON, stop and ask the user — never overwrite.
3. Keep `<project>/.claude/hooks/coding-rules-reminder.off` — that is the user's
   disable flag.

Note for the user: plan-mode sessions get the reminder at plan acceptance; all
other sessions get it on the first code edit (tracked per session via a marker
file in the temp dir, silent for later edits). The plugin hook runs `python` —
if that is not on PATH, Claude Code reports a non-blocking hook warning.

<!-- claude-code-only:end -->

## Phase F — Write the manifest (fallback path only)

After completing Phases B–E by hand, create or update `<project>/coding-rules.json`
so a later run (by either path) knows what's already applied:

```json
{
  "rules": { "COMMON_RULES.md": 3, "IMPLEMENTATION_FLOW.md": 25, "...": 1 },
  "delegation": "codex",
  "pointerVersion": 2,
  "pluginRoot": "<absolute path to the plugin's rules/ parent, e.g. ${CLAUDE_PLUGIN_ROOT}>"
}
```

- `rules` maps each rule file actually copied into `CODING_RULES.md` or
  `IMPLEMENTATION_FLOW.md` (path
  relative to `rules/`, e.g. `PYTHON_RULES.md`, `project_type/REST_API.md`) to
  the version of that block as written. `pointerVersion` is the version of the
  pointer block currently in `CLAUDE.md`.
- If the project already had `CODING_RULES.md` and/or a pointer block from a
  before-this-feature install (no manifest yet), reconstruct `coding-rules.json`
  from what's *currently* applied — read the version out of each existing block's
  own `# Version` line rather than assuming it's stale, so an already-current
  block isn't second-guessed.
- The fast path (`apply.py`) writes and maintains this file automatically; this
  step exists only because the fallback does the same work by hand.

Note: `coding-rules.json` is project-local state (the `pluginRoot` path is
machine-specific) — tell the user to add it to their `.gitignore` if the
project is version-controlled.

## Applicability

`IMPLEMENTATION_FLOW.md` is language-independent and always applies — it is NOT subject to the "some rules may not apply to this project" filtering below. Always include it in full. Every project gets both destination files; there is no opt-out.

For language-specific, project-type, and supplemental rules, include the rules that apply to the current project. Some rules might not apply (for example Twig template rules for a project that is only an API). Include optional addon rules only after the user opts in. If you are unsure which rules apply, ask the user whether to include all candidate rules or only the applicable ones.

## Setup file templates

Rule files may reference `*_setup_files/` folders (batch scripts, config templates). Those ship with this plugin too, under `${CLAUDE_PLUGIN_ROOT}/rules/<language>_setup_files/`. Copy templates from there into the project when a rule calls for them.
