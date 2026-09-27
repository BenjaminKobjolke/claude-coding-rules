---
description: Update every project that uses the coding rules to the current rule versions, scanning the folders from settings.json.
---

# Update All Coding Rules

Run:

```text
python ${CLAUDE_PLUGIN_ROOT}/skills/update-all/update_all.py
```

When the user asks only to inspect available updates, pass `--dry-run`.

Settings live at `~/.coding-rules/settings.json`. If it is missing, the script writes
`settings.example.json` beside it; copy that file to `settings.json` and set `folders` and
optional `ignore_prefixes`.

Show the user the command's summary. For every project reported as `needs decision`, tell the
user to run `/coding-rules:apply` in that project: tailored stale rules, source-version conflicts,
and unrecognized rules need judgment and are deliberately not changed by the bulk updater.
