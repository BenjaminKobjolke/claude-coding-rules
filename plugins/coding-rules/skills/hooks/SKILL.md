---
description: Enable, disable, or show the status of the coding-rules reminder hooks in the current project. Use when the user wants to turn the CODING_RULES.md reminder hooks on or off, or asks whether they are active.
---

# Toggle Coding Rules Reminder Hooks

Controls the reminder hooks shipped by the coding-rules plugin (plan-acceptance and first-edit reminders). The hooks are registered globally by the plugin and stay silent in projects without a `CODING_RULES.md`. Toggling works via a flag file — no settings.json edits, no session restart needed, and re-enabling is instant.

Flag file: `<project>/.claude/hooks/coding-rules-reminder.off` — when it exists, the hook script exits silently for this project.

Accepted arguments: `on`, `off`, `status` (default: `status`).

## off

1. If `<project>/CODING_RULES.md` does not exist, the reminders are already silent here — tell the user to run `/coding-rules:apply` first if they want rules in this project, and stop.
2. Create the empty file `<project>/.claude/hooks/coding-rules-reminder.off`.
3. Confirm: hooks disabled; the CLAUDE.md pointer block still applies.

## on

1. Delete `<project>/.claude/hooks/coding-rules-reminder.off` if it exists.
2. If `<project>/CODING_RULES.md` does not exist, tell the user to run `/coding-rules:apply` — the hooks stay silent until the project has coding rules.
3. Confirm: hooks enabled. Note: the first-edit reminder fires at most once per session — if it already fired this session, the next reminder comes in a new session or at the next plan acceptance.

## status

Report:

- Active for this project: does `CODING_RULES.md` exist in the project root?
- Enabled: does `.claude/hooks/coding-rules-reminder.off` NOT exist?

If `.claude/hooks/coding-rules-reminder.py` or a `coding-rules-reminder` entry in `.claude/settings.json` is still present, that is a leftover from the old per-project install — mention that `/coding-rules:apply` removes it.
