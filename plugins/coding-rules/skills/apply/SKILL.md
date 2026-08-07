---
description: Copy the applicable coding rules (common, language-specific, project-type, addons) into this project's CLAUDE.md, updating stale rule blocks by version. Use when setting up a project or refreshing its coding rules.
---

# Apply Coding Rules

The rule files ship with this plugin at `${CLAUDE_PLUGIN_ROOT}/rules/`. Do not ask the user for a rules folder path.

Always read `${CLAUDE_PLUGIN_ROOT}/rules/COMMON_RULES.md` and `${CLAUDE_PLUGIN_ROOT}/rules/AI_RULES.md` first, regardless of language — they may contain updated instructions for handling the rule files.

Then determine which additional rule files apply to the current project:

- Language-specific rules: `PHP_RULES.md`, `PYTHON_RULES.md`, `CSHARP_RULES.md`, `FLUTTER_RULES.md`, `SVELTE_RULES.md`, `SCSS_RULES.md`, `ARDUINO_RULES.md`, `AUTOHOTKEY_RULES.md`, `UNITY_CSHARP_RULES.md`, `WORDPRESS_RULES.md`
- Project-type rules: see `PROJECT_TYPES.md` for the overview, files in `project_type/`
- Optional addon rules in `ai_rules_addons/` — include only after the user opts in

Update the project's CLAUDE.md with the rules from the applicable files.

## Version merge

Each rule source starts with a `# Version` block. Include that block when copying rules into CLAUDE.md. For every applicable source file, compare its version with the version in the corresponding copied rule block:

- If the copied block has no version or its version is lower than the source version, replace that copied block with the current applicable source content.
- If both versions are equal, leave the copied block unchanged.
- If the copied version is higher than the source version, do not overwrite it; ask the user how to reconcile the unexpected version.

Identify corresponding copied blocks by the rule document title that follows the version block. Keep all copied rule blocks deduplicated and preserve project-specific CLAUDE.md content outside them. If CLAUDE.md contains coding-rule `@import` lines from an earlier run, remove those imports and replace them with the corresponding current rule content and version block.

## Applicability

`AI_RULES.md` is language-independent and always applies — it is NOT subject to the "some rules may not apply to this project" filtering below. Always include it in full.

For language-specific, project-type, and supplemental rules, include the rules that apply to the current project. Some rules might not apply (for example Twig template rules for a project that is only an API). Include optional addon rules only after the user opts in. If you are unsure which rules apply, ask the user whether to include all candidate rules or only the applicable ones.

## Setup file templates

Rule files may reference `*_setup_files/` folders (batch scripts, config templates). Those ship with this plugin too, under `${CLAUDE_PLUGIN_ROOT}/rules/<language>_setup_files/`. Copy templates from there into the project when a rule calls for them.
