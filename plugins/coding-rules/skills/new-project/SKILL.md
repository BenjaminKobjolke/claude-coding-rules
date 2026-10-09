---
description: Start a new project from a remembered template. Asks whether a template project exists for this project type, remembers the chosen one in ~/.coding-rules/settings.json and suggests it next time. Use when the user wants to create, start, set up or scaffold a new project, API, app, plugin or tool.
---

# New Project

Run this before creating any file of a new project. Never scaffold from scratch without
asking for a template first.

## 1. Project type

Derive a short lowercase key for the kind of project, e.g. `php-api`, `flutter-app`,
`python-cli`, `svelte-frontend`. Read `~/.coding-rules/settings.json` (it may be missing) and
reuse an existing key of its `templates` map when one means the same kind of project — do not
create `flutter-app` next to an existing `flutter`.

## 2. Ask for the template

Ask the user with one question, options in this order:

1. The remembered template `templates[<type>]`, marked as recommended — only if the key
   exists and the folder still exists on disk.
2. Another template — the user gives the path to the template project.
3. No template — scaffold from scratch.

Ask even when a template is remembered: it is a suggestion, not a decision.

## 3. Remember the choice

When the user chose a template path that differs from the stored one, write it to
`templates[<type>]` in `~/.coding-rules/settings.json`:

- Keep every other key (`folders`, `ignore_prefixes`, other `templates` entries) unchanged.
- If the file is missing, create it from `${CLAUDE_PLUGIN_ROOT}/settings.example.json` with
  an empty `templates` map, then add the entry. `folders` must stay a non-empty list —
  `/coding-rules:update-all` reads the same file and rejects it otherwise.
- "No template" stores nothing and does not remove a remembered template.

## 4. Create the project from the template

1. Copy only what the template tracks, so secrets, caches and build output stay behind:

   ```text
   git -C <template> archive -o <temp>/template.tar HEAD
   tar -xf <temp>/template.tar -C <target>
   ```

   If the template is not a git repository, copy the folder and skip everything its
   `.gitignore` lists.
2. Replace the template's own name with the new project's in every spelling the template
   uses — slug (`template-app-api`), snake case (`template_app`), PascalCase (`TemplateApp`),
   bundle or software id (`de.xida.template`), display title (`Template`). Ask the user for
   any of these that cannot be derived from the project name. Rename files and folders that
   carry the name too (e.g. a Kotlin package folder, a deploy config).
3. Search the new project case-insensitively for the template's name. Every remaining hit is
   either renamed or reported to the user — none is left silently.
4. Reset what belongs to the template only: version number, README text, remote URLs.
5. Run `/coding-rules:apply` in the new project so its rule blocks are current.

If the user chose no template, continue with the normal setup and run `/coding-rules:apply`
once the project has files.
