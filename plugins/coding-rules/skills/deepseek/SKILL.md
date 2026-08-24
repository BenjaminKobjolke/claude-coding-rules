---
description: Enable or disable DeepSeek (reasonix CLI) delegation for this project's coding-rules workflow (plan DRY check, convention check, post-implementation DRY audit). Sets the deepseek marker in CODING_RULES.md and, on enable, adds the Bash(reasonix run:*) and PowerShell(reasonix run:*) permissions so reasonix runs without prompts. Use for "enable deepseek", "disable deepseek", "deepseek status", "deepseek test" / "test deepseek" (live smoke test of the permissions).
---

# DeepSeek Toggle

Controls whether the AI workflow rules in this project run `reasonix run --auto`
commands or have the agent perform the same checks itself (`/plan:dry`,
`/convention:check`, `/dry:check`).

State lives as an HTML comment marker near the top of the project's
`CODING_RULES.md`, outside any versioned rule block:

```markdown
<!-- deepseek: enabled -->
```

or

```markdown
<!-- deepseek: disabled -->
```

No marker means disabled.

Argument: `on`, `off`, `status`, or `test`. No argument → report status, then
ask the user whether to change it.

## on

1. If the project has no `CODING_RULES.md`, stop and tell the user to run
   `/coding-rules:apply` first.
2. Set the marker to `<!-- deepseek: enabled -->`: replace an existing
   `<!-- deepseek: ... -->` marker in place, otherwise insert the marker on its
   own line directly after the `<!-- Managed by /coding-rules:apply ... -->`
   comment (or as the first line if that comment is missing).
   Codex and DeepSeek are mutually exclusive delegates. If a
   `<!-- codex: enabled -->` marker exists, set it to `<!-- codex: disabled -->`
   and tell the user Codex was disabled.
3. Check the reasonix CLI is installed (`reasonix --version`). If it fails,
   warn the user that reasonix is not on PATH but keep the marker enabled.

<!-- claude-code-only:start -->
4. Add the permission rules so `reasonix run` runs without approval prompts
   (on Windows, Claude Code may run it via the PowerShell tool instead of Bash).
   Claude Code's permission classifier otherwise blocks
   `reasonix run --auto`. Merge into
   `<project>/.claude/settings.local.json`:

```json
{
  "permissions": {
    "allow": [
      "Bash(reasonix run:*)",
      "PowerShell(reasonix run:*)"
    ]
  }
}
```

Merge rules:

- If the file does not exist, create it with exactly this content.
- If it exists, parse it first. If it is not valid JSON, stop and ask the user —
  never overwrite. Otherwise add missing keys and append each of
  `"Bash(reasonix run:*)"` and `"PowerShell(reasonix run:*)"` that is not already
  present to the existing `permissions.allow` array, preserving all other keys
  and entries.
- Idempotency: entries are checked independently — if both are already in the
  allow list, change nothing.
<!-- claude-code-only:end -->

5. **Keep the manifest in sync.** If `<project>/coding-rules.json` exists, set
   its `delegation` field to `"deepseek"` (parse the JSON, set the one field,
   write it back; leave every other key untouched). If the file does not exist,
   skip — `/coding-rules:apply` will create it. This is what prevents a later
   `/coding-rules:apply` from reusing a stale `delegation` value and silently
   flipping this marker back.

## off

Set the marker to `<!-- deepseek: disabled -->` (same placement rules as `on`).
The workflow steps then fall back to `/plan:dry`, `/convention:check`, and
`/dry:check` run by the agent itself.

Leave any `"Bash(reasonix run:*)"` / `"PowerShell(reasonix run:*)"` permission
entries in `.claude/settings.local.json` untouched — they are harmless while
disabled and save a step on re-enable. Mention this to the user.

Then keep the manifest in sync: if `<project>/coding-rules.json` exists and its
`delegation` is currently `"deepseek"`, set it to `"neither"` (parse, set, write
back; leave other keys untouched). If Codex is separately enabled, that skill
owns the field — do not clobber a `"codex"` value here.

## status

Report:

- Marker state in `CODING_RULES.md` (enabled / disabled / no marker = disabled).
- Whether `"Bash(reasonix run:*)"` and `"PowerShell(reasonix run:*)"` are present
  in `.claude/settings.local.json` `permissions.allow` (report each).
- Whether `reasonix --version` succeeds.
- The `<!-- codex: ... -->` marker state, since only one delegate should be
  enabled at a time.

## test

Runs the `status` static checks, then a live smoke test that catches what
`status` cannot: the permission classifier blocking the actual `reasonix run`
call.

1. Static checks — same four items as `status` above.

<!-- claude-code-only:start -->
2. Live check. From the project directory run:

   ```
   reasonix run --auto "Reply with exactly: DEEPSEEK_OK"
   ```

   - **Pass**: the command ran without a permission prompt and the output
     contains `DEEPSEEK_OK`.
   - **Permission prompt appeared or the call was denied**: that IS the
     failure this test exists for. Report which permission entry is missing
     for the shell tool that was used (`Bash(reasonix run:*)` or
     `PowerShell(reasonix run:*)`) and offer to run the permission-merge step
     from `on` (step 4) to fix it.
   - **reasonix CLI itself errored** (not installed, not logged in, network):
     report that separately — it is a reasonix problem, not a permissions
     problem.
<!-- claude-code-only:end -->

3. Report: one pass/fail line per check, with a one-line fix hint per
   failure — `run /coding-rules:deepseek on` for marker or permission
   failures, install / configure reasonix for CLI failures.
