# claude-coding-rules

Versioned coding rules for Claude Code, packaged as an installable plugin.

Languages: PHP, Python, C#, Flutter/Dart, Svelte, SCSS, Arduino, AutoHotkey, Unity C#, WordPress.
Project types: REST API, Frontend SPA. Plus common rules that apply to every language.

## Install

```
/plugin marketplace add BenjaminKobjolke/claude-coding-rules
/plugin install coding-rules@claude-coding-rules
```

For developing the plugin from a local clone, see [DEBUG.md](DEBUG.md).

## Skills

| Skill | What it does |
|-------|--------------|
| `/coding-rules:apply` | Writes the applicable rules (common + language + project type + opted-in addons) into your project's `CODING_RULES.md`, puts a versioned pointer block into `CLAUDE.md`, and installs a plan-acceptance hook that reminds Claude to read the rules. Rule blocks carry a `# Version`; re-running updates only stale blocks and migrates legacy inlined `CLAUDE.md` rules. |
| `/coding-rules:enforce` | Audits your actual codebase against the rules and reports violations — no auto-fixing. |
| `/coding-rules:hooks` | `on` / `off` / `status` for the reminder hooks in the current project. Toggles via a flag file — no settings.json edits, no session restart needed. |
| `/coding-rules:sync-codex` | Installs the skills into OpenAI Codex (`~/.codex/skills/`) so the same rules work there. |

## Using with OpenAI Codex

Codex has no plugin marketplace — skills are folders in `~/.codex/skills/`. Either run
`/coding-rules:sync-codex` from Claude Code, or clone this repo and run:

```bash
python plugins/coding-rules/skills/sync-codex/sync_to_codex.py
```

This installs `coding-rules-apply` and `coding-rules-enforce` as Codex skills with the
rule files bundled. Re-run after updating the repo. Details: [docs/CODEX.md](docs/CODEX.md).

## Structure

- `plugins/coding-rules/rules/` — the rule files (`COMMON_RULES.md`, `AI_RULES.md`, `*_RULES.md`, `project_type/`, `ai_rules_addons/`)
- `plugins/coding-rules/rules/*_setup_files/` — batch scripts and config templates the rules reference
- `plugins/coding-rules/skills/` — the `apply` and `enforce` skills

## Why a separate CODING_RULES.md?

Rules are copied (not `@import`-linked) so each project pins the exact rule text it was built against. The `# Version` block per rule file lets `/coding-rules:apply` upgrade stale blocks deliberately instead of rules changing under a project silently.

They live in `CODING_RULES.md` instead of `CLAUDE.md` so the ~1,000–1,800 lines of rules are not in context every turn. `CLAUDE.md` carries only a small versioned pointer block that mandates reading `CODING_RULES.md` before any code work. The pointer is deliberately **not** an `@import` — Claude Code auto-expands imports into context, which would defeat the point.

To make the read near-guaranteed, `apply` also installs reminder hooks (`.claude/hooks/coding-rules-reminder.py` + `.claude/settings.json`): a `PostToolUse` hook on `ExitPlanMode` re-injects the read instruction the moment a plan is accepted, and a `PreToolUse` hook on `Edit|Write` does the same on the first code edit of any session (tracked by a per-session marker file, silent for later edits).

## License

MIT
