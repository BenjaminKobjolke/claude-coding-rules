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
## Phase D2 — Codex toggle (idempotent)

The AI workflow rules can delegate DRY/convention checks to the Codex CLI (see
the Codex toggle section in `AI_RULES.md`). State is a marker near the top of
`CODING_RULES.md`: `<!-- codex: enabled -->` or `<!-- codex: disabled -->`.

- If `CODING_RULES.md` already contains a `<!-- codex: ... -->` marker, keep it
  and do not re-ask.
- Otherwise ask the user: "Use Codex for the DRY and convention checks in this
  project? (If no, Claude performs those checks itself.)"
  - Yes → follow the `on` steps of `${CLAUDE_PLUGIN_ROOT}/skills/codex/SKILL.md`
    (insert `<!-- codex: enabled -->` after the managed-by comment, verify
    `codex --version`, and merge `"Bash(codex exec:*)"` into
    `<project>/.claude/settings.local.json` `permissions.allow` per that skill's
    merge rules).
  - No → insert `<!-- codex: disabled -->` after the managed-by comment.
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

## Applicability

`AI_RULES.md` is language-independent and always applies — it is NOT subject to the "some rules may not apply to this project" filtering below. Always include it in full.

For language-specific, project-type, and supplemental rules, include the rules that apply to the current project. Some rules might not apply (for example Twig template rules for a project that is only an API). Include optional addon rules only after the user opts in. If you are unsure which rules apply, ask the user whether to include all candidate rules or only the applicable ones.

## Setup file templates

Rule files may reference `*_setup_files/` folders (batch scripts, config templates). Those ship with this plugin too, under `${CLAUDE_PLUGIN_ROOT}/rules/<language>_setup_files/`. Copy templates from there into the project when a rule calls for them.
