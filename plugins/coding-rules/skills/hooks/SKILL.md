---
description: Enable, disable, or show the status of the coding-rules reminder hooks in the current project. Use when the user wants to turn the CODING_RULES.md reminder hooks on or off, or asks whether they are active.
---

# Toggle Coding Rules Reminder Hooks

Controls the reminder hooks installed by `/coding-rules:apply` (plan-acceptance and first-edit reminders). Toggling works via a flag file — the hook entries in `.claude/settings.json` stay untouched, so no session restart is needed and re-enabling is instant.

Flag file: `<project>/.claude/hooks/coding-rules-reminder.off` — when it exists, the hook script exits silently.

Accepted arguments: `on`, `off`, `status` (default: `status`).

## off

1. If `<project>/.claude/hooks/coding-rules-reminder.py` does not exist, the hooks are not installed — tell the user to run `/coding-rules:apply` first and stop.
2. Create the empty file `<project>/.claude/hooks/coding-rules-reminder.off`.
3. Confirm: hooks disabled; the CLAUDE.md pointer block still applies.

## on

1. Delete `<project>/.claude/hooks/coding-rules-reminder.off` if it exists.
2. If `<project>/.claude/hooks/coding-rules-reminder.py` does not exist, tell the user to run `/coding-rules:apply` to install the hooks.
3. Confirm: hooks enabled. Note: the first-edit reminder fires at most once per session — if it already fired this session, the next reminder comes in a new session or at the next plan acceptance.

## status

Report:

- Installed: does `.claude/hooks/coding-rules-reminder.py` exist and does `.claude/settings.json` reference `coding-rules-reminder`?
- Enabled: does `.claude/hooks/coding-rules-reminder.off` NOT exist?
