---
description: Enable or disable Codex CLI delegation for this project's coding-rules workflow (plan DRY check, convention check, post-implementation DRY audit). Sets the codex marker in CODING_RULES.md and, on enable, adds the Bash(codex exec:*) permission so codex runs without prompts. Use for "enable codex", "disable codex", "codex status".
---

# Codex Toggle

Controls whether the AI workflow rules in this project run `codex exec` commands
or have the agent perform the same checks itself (`/plan:dry`, `/convention:check`,
`/dry:check`).

State lives as an HTML comment marker near the top of the project's
`CODING_RULES.md`, outside any versioned rule block:

```markdown
<!-- codex: enabled -->
```

or

```markdown
<!-- codex: disabled -->
```

No marker means disabled.

Argument: `on`, `off`, or `status`. No argument → report status, then ask the
user whether to change it.

## on

1. If the project has no `CODING_RULES.md`, stop and tell the user to run
   `/coding-rules:apply` first.
2. Set the marker to `<!-- codex: enabled -->`: replace an existing
   `<!-- codex: ... -->` marker in place, otherwise insert the marker on its own
   line directly after the `<!-- Managed by /coding-rules:apply ... -->` comment
   (or as the first line if that comment is missing).
3. Check the Codex CLI is installed (`codex --version`). If it fails, warn the
   user that codex is not on PATH but keep the marker enabled.

<!-- claude-code-only:start -->
4. Add the permission rule so `codex exec` runs without approval prompts.
   Claude Code's permission classifier otherwise blocks
   `codex exec --dangerously-bypass-approvals-and-sandbox`. Merge into
   `<project>/.claude/settings.local.json`:

```json
{
  "permissions": {
    "allow": [
      "Bash(codex exec:*)"
    ]
  }
}
```

Merge rules:

- If the file does not exist, create it with exactly this content.
- If it exists, parse it first. If it is not valid JSON, stop and ask the user —
  never overwrite. Otherwise add missing keys and append `"Bash(codex exec:*)"`
  to the existing `permissions.allow` array, preserving all other keys and
  entries.
- Idempotency: if `"Bash(codex exec:*)"` is already in the allow list, change
  nothing.
<!-- claude-code-only:end -->

## off

Set the marker to `<!-- codex: disabled -->` (same placement rules as `on`).
The workflow steps then fall back to `/plan:dry`, `/convention:check`, and
`/dry:check` run by the agent itself.

Leave any `"Bash(codex exec:*)"` permission entry in
`.claude/settings.local.json` untouched — it is harmless while disabled and
saves a step on re-enable. Mention this to the user.

## status

Report:

- Marker state in `CODING_RULES.md` (enabled / disabled / no marker = disabled).
- Whether `"Bash(codex exec:*)"` is present in
  `.claude/settings.local.json` `permissions.allow`.
- Whether `codex --version` succeeds.
