# Using the Coding Rules with OpenAI Codex

Codex has no plugin marketplace. It loads skills from plain folders:
`~/.codex/skills/<name>/SKILL.md`, with any supporting files next to the SKILL.md.

This repo ships a sync script that installs its skills there.

## Install

From Claude Code (with the plugin installed):

```
/coding-rules:sync-codex
```

Or manually, from a clone of this repo:

```bash
python plugins/coding-rules/skills/sync-codex/sync_to_codex.py
```

(`python3` or `py` if `python` is not on PATH.)

## What gets installed

| Codex skill | Source | Contents |
|-------------|--------|----------|
| `~/.codex/skills/coding-rules-apply/` | `skills/apply/SKILL.md` | SKILL.md + full `rules/` folder bundled next to it |
| `~/.codex/skills/coding-rules-enforce/` | `skills/enforce/SKILL.md` | SKILL.md only (it runs apply first) |

The script adapts the content for Codex:

- `${CLAUDE_PLUGIN_ROOT}/...` paths become paths relative to the skill folder
- `/coding-rules:apply` slash-command references become `coding-rules-apply` skill references
- Claude-specific frontmatter is reduced to `name` + `description`

## Update

Re-run the sync after the rules or skills change:

```
/coding-rules:sync-codex
```

The sync overwrites both skill folders each run — no stale-file cleanup needed as long
as the skill names stay `coding-rules-apply` / `coding-rules-enforce`.

## Verify

```bash
python plugins/coding-rules/skills/sync-codex/sync_to_codex.py --self-test
```

In Codex, the skills appear as `coding-rules-apply` and `coding-rules-enforce`.
