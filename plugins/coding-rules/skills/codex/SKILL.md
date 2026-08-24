---
description: Enable or disable Codex CLI delegation for this project's coding-rules workflow (plan DRY check, convention check, post-implementation DRY audit). Sets the codex marker in CODING_RULES.md and, on enable, adds the Bash(codex exec:*) and PowerShell(codex exec:*) permissions so codex runs without prompts. Use for "enable codex", "disable codex", "codex status", "codex test" / "test codex" (live smoke test of the permissions).
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

Argument: `on`, `off`, `status`, or `test`. No argument → report status, then
ask the user whether to change it.

## on

1. If the project has no `CODING_RULES.md`, stop and tell the user to run
   `/coding-rules:apply` first.
2. Set the marker to `<!-- codex: enabled -->`: replace an existing
   `<!-- codex: ... -->` marker in place, otherwise insert the marker on its own
   line directly after the `<!-- Managed by /coding-rules:apply ... -->` comment
   (or as the first line if that comment is missing).
   Codex and DeepSeek are mutually exclusive delegates. If a
   `<!-- deepseek: enabled -->` marker exists, set it to
   `<!-- deepseek: disabled -->` and tell the user DeepSeek was disabled.
3. Check the Codex CLI is installed (`codex --version`). If it fails, warn the
   user that codex is not on PATH but keep the marker enabled.

<!-- claude-code-only:start -->
4. Add the permission rules so `codex exec` runs without approval prompts
   (on Windows, Claude Code may run it via the PowerShell tool instead of Bash).
   Claude Code's permission classifier otherwise blocks
   `codex exec --dangerously-bypass-approvals-and-sandbox`. Merge into
   `<project>/.claude/settings.local.json`:

```json
{
  "permissions": {
    "allow": [
      "Bash(codex exec:*)",
      "PowerShell(codex exec:*)"
    ]
  }
}
```

Merge rules:

- If the file does not exist, create it with exactly this content.
- If it exists, parse it first. If it is not valid JSON, stop and ask the user —
  never overwrite. Otherwise add missing keys and append each of
  `"Bash(codex exec:*)"` and `"PowerShell(codex exec:*)"` that is not already
  present to the existing `permissions.allow` array, preserving all other keys
  and entries.
- Idempotency: entries are checked independently — if both are already in the
  allow list, change nothing.
<!-- claude-code-only:end -->

5. **Keep the manifest in sync.** If `<project>/coding-rules.json` exists, set
   its `delegation` field to `"codex"` (parse the JSON, set the one field, write
   it back; leave every other key untouched). If the file does not exist, skip —
   `/coding-rules:apply` will create it. This is what prevents a later
   `/coding-rules:apply` from reusing a stale `delegation` value and silently
   flipping this marker back.

## off

Set the marker to `<!-- codex: disabled -->` (same placement rules as `on`).
The workflow steps then fall back to `/plan:dry`, `/convention:check`, and
`/dry:check` run by the agent itself.

Leave any `"Bash(codex exec:*)"` / `"PowerShell(codex exec:*)"` permission
entries in `.claude/settings.local.json` untouched — they are harmless while
disabled and save a step on re-enable. Mention this to the user.

Then keep the manifest in sync: if `<project>/coding-rules.json` exists and its
`delegation` is currently `"codex"`, set it to `"neither"` (parse, set, write
back; leave other keys untouched). If DeepSeek is separately enabled, that
skill owns the field — do not clobber a `"deepseek"` value here.

## status

Report:

- Marker state in `CODING_RULES.md` (enabled / disabled / no marker = disabled).
- Whether `"Bash(codex exec:*)"` and `"PowerShell(codex exec:*)"` are present
  in `.claude/settings.local.json` `permissions.allow` (report each).
- Whether `codex --version` succeeds.
- The `<!-- deepseek: ... -->` marker state, since only one delegate should be
  enabled at a time.

## test

Runs the `status` static checks, then a live smoke test that catches what
`status` cannot: the permission classifier blocking the actual `codex exec`
call.

1. Static checks — same three items as `status` above.

<!-- claude-code-only:start -->
2. Live check. From the project directory run:

   ```
   codex exec --dangerously-bypass-approvals-and-sandbox "Reply with exactly: CODEX_OK"
   ```

   - **Pass**: the command ran without a permission prompt and the output
     contains `CODEX_OK`.
   - **Permission prompt appeared or the call was denied**: that IS the
     failure this test exists for. Report which permission entry is missing
     for the shell tool that was used (`Bash(codex exec:*)` or
     `PowerShell(codex exec:*)`) and offer to run the permission-merge step
     from `on` (step 4) to fix it.
   - **Codex CLI itself errored** (not installed, not logged in, network):
     report that separately — it is a codex problem, not a permissions
     problem.
<!-- claude-code-only:end -->

3. Report: one pass/fail line per check, with a one-line fix hint per
   failure — `run /coding-rules:codex on` for marker or permission failures,
   install / `codex login` for CLI failures.
