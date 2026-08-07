# claude-coding-rules

Versioned coding rules for Claude Code, packaged as an installable plugin.

Languages: PHP, Python, C#, Flutter/Dart, Svelte, SCSS, Arduino, AutoHotkey, Unity C#, WordPress.
Project types: REST API, Frontend SPA. Plus common rules that apply to every language.

## Install

```
/plugin marketplace add BenjaminKobjolke/claude-coding-rules
/plugin install coding-rules@claude-coding-rules
```

## Skills

| Skill | What it does |
|-------|--------------|
| `/coding-rules:apply` | Copies the applicable rules (common + language + project type + opted-in addons) into your project's `CLAUDE.md`. Rule blocks carry a `# Version`; re-running updates only stale blocks. |
| `/coding-rules:enforce` | Audits your actual codebase against the rules and reports violations — no auto-fixing. |

## Structure

- `plugins/coding-rules/rules/` — the rule files (`COMMON_RULES.md`, `AI_RULES.md`, `*_RULES.md`, `project_type/`, `ai_rules_addons/`)
- `plugins/coding-rules/rules/*_setup_files/` — batch scripts and config templates the rules reference
- `plugins/coding-rules/skills/` — the `apply` and `enforce` skills

## Why copy rules into CLAUDE.md?

Rules are inlined (not `@import`-linked) so each project pins the exact rule text it was built against. The `# Version` block per rule file lets `/coding-rules:apply` upgrade stale blocks deliberately instead of rules changing under a project silently.

## License

MIT
