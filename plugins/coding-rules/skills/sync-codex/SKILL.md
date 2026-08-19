---
description: Install or update the coding-rules skills into OpenAI Codex (~/.codex/skills). Use when the user wants these coding rules available in Codex too.
---

# Sync Coding Rules to Codex

Codex loads skills from `~/.codex/skills/<name>/SKILL.md`. This installs the plugin's
`apply` and `enforce` skills there as `coding-rules-apply` and `coding-rules-enforce`,
with the rule files bundled.

Run the bundled script:

```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/sync-codex/sync_skills.py"
```

Re-run it any time the rules or skills change to update the Codex copies.

If `python` is not on PATH, try `python3` or `py`.
