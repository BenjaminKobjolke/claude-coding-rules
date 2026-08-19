# Rule authoring: keep versions.json in sync

Every file in `plugins/coding-rules/rules/*.md` (including `project_type/` and
`ai_rules_addons/`) starts with a `# Version` header. The current version of
every rule file is also tracked centrally in
`plugins/coding-rules/rules/versions.json` — `apply.py` (used by the
`coding-rules:apply` skill) reads that index instead of opening every md file,
so the two MUST stay in sync.

Whenever you change any `plugins/coding-rules/rules/*.md` file:

1. Bump its `# Version` header by 1.
2. Update the matching entry in `plugins/coding-rules/rules/versions.json` to
   the same number (add the entry if the file is new; key = path relative to
   `rules/`, e.g. `project_type/REST_API.md`).
3. Run `python plugins/coding-rules/skills/apply/apply.py --check-versions` to
   verify the header and the index agree, and that no rule file is missing
   from the index.

See `plugins/coding-rules/rules/CREATE_NEW_RULES.md` for the required header
block on brand-new rule files.
