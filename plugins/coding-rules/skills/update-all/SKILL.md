---
description: Update projects that use the coding rules to the current rule versions, scanning settings.json folders or an explicit project list.
---

# Update All Coding Rules

Run:

```text
python ${CLAUDE_PLUGIN_ROOT}/skills/update-all/update_all.py
```

Pass `--project <path>` to update a specific project folder instead of scanning the configured
folders. Repeat the option to process several projects; explicit project paths do not need a
`settings.json` file. Use `--json` to print one JSON document with `dry_run`, a `projects` array,
and `totals`. Project entries include the path, status (`updated`, `current`, `needs_decision`,
`no_manifest`, or `error`), outdated rule versions, decisions, errors, and kept split files.
The command exits with code 1 if any project errors. In JSON mode, settings warnings go to stderr.
Both options can be combined with `--dry-run` to inspect results without changing projects.

When the user asks only to inspect available updates, pass `--dry-run`.

Settings live at `~/.coding-rules/settings.json`. If it is missing, the script writes
`settings.example.json` beside it; copy that file to `settings.json` and set `folders` and
optional `ignore_prefixes`.

Show the user the command's summary. For every project reported as `needs decision`, tell the
user to run `/coding-rules:apply` in that project: tailored stale rules, source-version conflicts,
and unrecognized rules need judgment and are deliberately not changed by the bulk updater.
Relay any `kept:` files shown on updated projects. If a project lost a section it
uses, run `/coding-rules:apply` there to add that optional file.
