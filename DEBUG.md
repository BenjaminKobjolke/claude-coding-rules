# Local Development

How to run this plugin from the local clone instead of GitHub — edits apply without pushing.

## Install from local clone

```
claude plugin marketplace add D:\GIT\BenjaminKobjolke\claude-coding-rules
claude plugin install coding-rules@claude-coding-rules
```

The marketplace is registered in user settings and points at the local folder;
the plugin installs at user scope.

## Dev loop

1. Edit rule files (`plugins/coding-rules/rules/`) or skills (`plugins/coding-rules/skills/`)
2. Pull the changes into the installed copy:

   ```
   claude plugin update coding-rules@claude-coding-rules
   ```

3. Start a new Claude Code session so the skills reload

## Verify install

```
claude plugin list
```

`coding-rules@claude-coding-rules` should show as enabled. In a new session,
`/coding-rules:apply` and `/coding-rules:enforce` appear in the skill list.

## Switch to the GitHub source

To test exactly what external users get:

```
claude plugin marketplace remove claude-coding-rules
claude plugin marketplace add BenjaminKobjolke/claude-coding-rules
claude plugin install coding-rules@claude-coding-rules
```

Updates then require push + `claude plugin update`. Switch back the same way with
the local path.
