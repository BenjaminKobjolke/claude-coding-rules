---
description: Copy the applicable coding rules (common, language-specific, project-type, addons) into this project's CODING_RULES.md, add a pointer block to CLAUDE.md, and install a plan-acceptance reminder hook. Updates stale rule blocks by version. Use when setting up a project or refreshing its coding rules.
---

# Apply Coding Rules

The rule files ship with this plugin at `${CLAUDE_PLUGIN_ROOT}/rules/`. Do not ask the user for a rules folder path.

Rules are copied into the project's `CODING_RULES.md` (project root). `CLAUDE.md` gets only a small versioned pointer block that mandates reading `CODING_RULES.md` before code work. Do NOT inline full rules into `CLAUDE.md` and do NOT use `@import` for `CODING_RULES.md` — Claude Code auto-expands imports, which would put the full rules in context every turn and defeat the purpose.

Always read `${CLAUDE_PLUGIN_ROOT}/rules/COMMON_RULES.md` and `${CLAUDE_PLUGIN_ROOT}/rules/AI_RULES.md` first, regardless of language — they may contain updated instructions for handling the rule files.

## Phase A — Determine applicable rule files

- Always: `COMMON_RULES.md` and `AI_RULES.md`
- Language-specific rules: `PHP_RULES.md`, `PYTHON_RULES.md`, `CSHARP_RULES.md`, `FLUTTER_RULES.md`, `SVELTE_RULES.md`, `SCSS_RULES.md`, `ARDUINO_RULES.md`, `AUTOHOTKEY_RULES.md`, `UNITY_CSHARP_RULES.md`, `WORDPRESS_RULES.md`
- Project-type rules: see `PROJECT_TYPES.md` for the overview, files in `project_type/`
- Optional addon rules in `ai_rules_addons/` — include only after the user opts in

If `<project>/coding-rules.json` already exists, read it: its `rules` map is the
prior selection (keys are paths relative to `rules/`, e.g. `PYTHON_RULES.md`,
`project_type/REST_API.md`). On a re-run, only ask the user about deltas
(newly-relevant languages/project types) instead of re-deriving the whole list.

Optional addon rules (`ai_rules_addons/*.md`) are the one exception: re-ask
about every addon NOT already present in the `rules` map on every run, even
if a prior run's answer was "no". A previous decline is not durable consent
to skip asking forever — the user's needs change, and addons are cheap to
ask about. Once an addon is accepted and its key lands in `rules`, stop
asking (a present key is durable; treat removal from `CODING_RULES.md` as an
explicit opt-out signal instead of silently re-adding it).

## Delegation choice

If `<project>/coding-rules.json` exists and has a `delegation` field, reuse it
— do not re-ask. Otherwise ask the user: "Delegate the DRY and convention
checks in this project to Codex, DeepSeek, or neither (Claude performs those
checks itself)?" Map the answer to `codex`, `deepseek`, or `neither` for the
`--delegation` flag below.

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
  --rules <comma-separated paths from Phase A, e.g. COMMON_RULES.md,AI_RULES.md,PYTHON_RULES.md> \
  --delegation <codex|deepseek|neither|keep> \
  --python <detected interpreter> \
  --json
```

`<plugin-root>` is `${CLAUDE_PLUGIN_ROOT}`. This single call performs Phases
B, C, D, D2, and E (legacy migration, version-merged `CODING_RULES.md`,
`CLAUDE.md` pointer, delegation marker + permission merge, and hook install)
and writes `<project>/coding-rules.json`. Parse the JSON report:

- `needs_user_decision` items (an unrecognized legacy block in `CLAUDE.md`, or
  a rule/pointer version conflict where the project's applied version is
  *higher* than the source) — surface each to the user and ask how to
  reconcile; the script left the file untouched so nothing is lost by asking.
- `errors` items (e.g. an unparsable `settings.json`) — report verbatim; the
  file was left untouched.
- Otherwise summarize what changed (which rule blocks were updated, pointer
  status, delegation, hook status) for the user.

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

If the project has a `CLAUDE.md`, scan it for legacy inlined rule blocks: a `# Version` line followed by a number, followed by a rule-document title that matches one of the shipped rule files (e.g. `# Common Rules (All Languages)`, `# AI Workflow Rules (All Languages)`, `# PHP Rules`, …). A block ends at the next `# Version` line, the pointer block, or end of file.

- Move every recognized block verbatim into `CODING_RULES.md` (create it if missing).
- If a `# Version` block has an unrecognized title, ask the user before touching it — it may be a user-authored versioned section.
- Preserve every other line of `CLAUDE.md` untouched and in order.
- If `CLAUDE.md` contains coding-rule `@import` lines from an earlier run, delete them; their content lands in `CODING_RULES.md` via Phase C.

## Phase C — Version-merge into CODING_RULES.md

Each rule source starts with a `# Version` block. Include that block when copying rules into `CODING_RULES.md`. For every applicable source file, compare its version with the version in the corresponding copied rule block:

- If the copied block has no version or its version is lower than the source version, replace that copied block with the current applicable source content.
- If both versions are equal, leave the copied block unchanged.
- If the copied version is higher than the source version, do not overwrite it; ask the user how to reconcile the unexpected version.

Identify corresponding copied blocks by the rule document title that follows the version block. Keep all copied rule blocks deduplicated. On first creation, start the file with:

```markdown
<!-- Managed by /coding-rules:apply — do not edit rule blocks by hand -->
```

### Tailored blocks and user-authored sections

- When you tailor a copied rule block to the project (trim inapplicable sections,
  substitute real paths/dirs, apply an addon's paste-form), insert `<!-- tailored -->`
  on its own line directly after the block's title heading. `apply.py` never
  auto-overwrites a tailored block: a newer source version is reported as
  `tailored-stale` in `needs_user_decision`, and you hand-merge the source changes
  into the tailored copy (then bump the block's version to match the source).
- User-authored top-level sections after the last managed block (project deviations,
  project-specific rules, …) are preserved by `apply.py` when a block is replaced —
  any heading the source doc doesn't contain starts preserved content, reported per
  rule under `preserved`. Verify preserved titles look intentional, not stale rule
  leftovers.

## Phase D — Pointer block in CLAUDE.md

Merge the following pointer block into the project's `CLAUDE.md` using the same version rules as Phase C (matched by the title `# Coding Rules (Pointer)`). Insert it at the top of `CLAUDE.md` when absent; create `CLAUDE.md` if the project has none. Copy it verbatim:

```markdown
# Version
1

# Coding Rules (Pointer)

This project's coding rules live in `CODING_RULES.md` in the project root. They are
BINDING for all code work in this repository.

MANDATORY: Before writing or editing ANY code, you MUST Read `CODING_RULES.md`
in full **in the current session**. Do not rely on memory of a previous session,
a summary, or partial reads.

If you are about to make a code change and have not read `CODING_RULES.md` in
this session: STOP, read it, then continue.

Do not inline rules back into this file and do not use `@import` for
`CODING_RULES.md` — it is intentionally referenced, not imported.
```

<!-- claude-code-only:start -->
## Phase D2 — Delegation backend toggle (idempotent)

The AI workflow rules can delegate DRY/convention checks to Codex or DeepSeek
(see the Delegation backends section in `AI_RULES.md`). State is a marker near
the top of `CODING_RULES.md`: `<!-- codex: enabled/disabled -->` and
`<!-- deepseek: enabled/disabled -->`. The two are mutually exclusive — at
most one is `enabled`.

Use the choice from the "Delegation choice" step above (do not re-ask here):

- Codex → follow the `on` steps of `${CLAUDE_PLUGIN_ROOT}/skills/codex/SKILL.md`
  (insert `<!-- codex: enabled -->` after the managed-by comment, verify
  `codex --version`, merge `"Bash(codex exec:*)"` and
  `"PowerShell(codex exec:*)"` into
  `<project>/.claude/settings.local.json` `permissions.allow` per that skill's
  merge rules, and insert `<!-- deepseek: disabled -->`).
- DeepSeek → follow the `on` steps of
  `${CLAUDE_PLUGIN_ROOT}/skills/deepseek/SKILL.md` (insert
  `<!-- deepseek: enabled -->` after the managed-by comment, verify
  `reasonix --version`, merge `"Bash(reasonix run:*)"` and
  `"PowerShell(reasonix run:*)"` into
  `<project>/.claude/settings.local.json` `permissions.allow` per that skill's
  merge rules, and insert `<!-- codex: disabled -->`).
- Neither → insert `<!-- codex: disabled -->` and `<!-- deepseek: disabled -->`
  after the managed-by comment.
- If a marker for the chosen backend is already `enabled`, still (re-)run that
  backend's permission merge — idempotent, and picks up permissions added in
  newer plugin versions.
<!-- claude-code-only:end -->

<!-- claude-code-only:start -->
## Phase E — Install the reminder hooks (idempotent)

Install hooks that remind Claude to read `CODING_RULES.md` when the user accepts a plan (PostToolUse/ExitPlanMode) and on the first code edit of any session (PreToolUse/Edit — per-session marker file, silent afterwards). One script serves both events.

1. Copy `${CLAUDE_PLUGIN_ROOT}/skills/apply/hooks/coding-rules-reminder.py` to `<project>/.claude/hooks/coding-rules-reminder.py`. Overwriting an existing copy is fine — the script is plugin-managed. Do NOT delete an existing `coding-rules-reminder.off` file next to it — that is the user's disable flag (`/coding-rules:hooks off`).
2. Verify a Python interpreter: try `python --version`, then `python3`, then `py`. Use whichever works in the hook command below. If none works, skip the hook, tell the user it was skipped, and note that the CLAUDE.md pointer still covers all sessions.
3. Merge these entries into `<project>/.claude/settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "ExitPlanMode",
        "hooks": [
          {
            "type": "command",
            "command": "python .claude/hooks/coding-rules-reminder.py"
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit",
        "hooks": [
          {
            "type": "command",
            "command": "python .claude/hooks/coding-rules-reminder.py"
          }
        ]
      }
    ]
  }
}
```

Merge rules:

- If `settings.json` does not exist, create it with exactly this content.
- If it exists, parse it first. If it is not valid JSON, stop and ask the user — never overwrite. Otherwise add the `hooks` key if missing, append to an existing `PostToolUse` array, and preserve all other keys and entries.
- Idempotency: before appending, search all existing `PostToolUse` AND `PreToolUse` entries for a command containing `coding-rules-reminder`. If found, update that entry in place if it differs; never add a second one per event.
- The command uses a relative path on purpose: hooks run with the project directory as cwd, and `$CLAUDE_PROJECT_DIR` does not expand under `cmd.exe`.

Note for the user: plan-mode sessions get the reminder at plan acceptance; all other sessions get it on the first code edit (tracked per session via a marker file in the temp dir, silent for later edits). Hooks added mid-session don't load until the user opens `/hooks` once or restarts the session.
<!-- claude-code-only:end -->

## Phase F — Write the manifest (fallback path only)

After completing Phases B–E by hand, create or update `<project>/coding-rules.json`
so a later run (by either path) knows what's already applied:

```json
{
  "rules": { "COMMON_RULES.md": 3, "AI_RULES.md": 10, "...": 1 },
  "delegation": "codex",
  "pointerVersion": 1,
  "python": "python",
  "pluginRoot": "<absolute path to the plugin's rules/ parent, e.g. ${CLAUDE_PLUGIN_ROOT}>"
}
```

- `rules` maps each rule file actually copied into `CODING_RULES.md` (path
  relative to `rules/`, e.g. `PYTHON_RULES.md`, `project_type/REST_API.md`) to
  the version of that block as written. `pointerVersion` is the version of the
  pointer block currently in `CLAUDE.md`. `python` is the interpreter detected
  in Phase E, or `null` if none was found.
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

`AI_RULES.md` is language-independent and always applies — it is NOT subject to the "some rules may not apply to this project" filtering below. Always include it in full.

For language-specific, project-type, and supplemental rules, include the rules that apply to the current project. Some rules might not apply (for example Twig template rules for a project that is only an API). Include optional addon rules only after the user opts in. If you are unsure which rules apply, ask the user whether to include all candidate rules or only the applicable ones.

## Setup file templates

Rule files may reference `*_setup_files/` folders (batch scripts, config templates). Those ship with this plugin too, under `${CLAUDE_PLUGIN_ROOT}/rules/<language>_setup_files/`. Copy templates from there into the project when a rule calls for them.
