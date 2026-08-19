---
description: Install or update the coding-rules skills into the pi agent (~/.pi/agent/skills). Use when the user wants these coding rules available in pi too.
---

# Sync Coding Rules to pi agent

The pi agent loads skills from `~/.pi/agent/skills/<name>/SKILL.md`. This installs
the plugin's `apply` and `enforce` skills there as `coding-rules-apply` and
`coding-rules-enforce`, with the rule files bundled.

Run the bundled script:

```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/sync-codex/sync_skills.py" pi
```

Re-run it any time the rules or skills change to update the pi copies.

If `python` is not on PATH, try `python3` or `py`.
