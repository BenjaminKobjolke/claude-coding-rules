---
description: Audit the actual codebase for coding-rule violations and report them without auto-fixing. Use when checking whether a project follows the installed coding rules.
---

# Enforce Coding Rules

First run `/coding-rules:apply` to ensure CLAUDE.md has the latest rules.

Then audit the actual project code against those rules. Do NOT auto-fix — report findings and let the user decide what to fix.

## Setup

1. Read CLAUDE.md to determine which rules apply to this project
2. Detect the project language(s) from file extensions and project files
3. Identify source directories — exclude: vendor, node_modules, build output, generated files, .git

## Audit: File & Project-Level Checks

Run these quick structural checks first:

- **README.md exists** — check root directory
- **Test runner scripts exist** — check for `tools/run_tests.bat` and `tools/run_integration_tests.bat`
- **Maximum file length** — find source files exceeding 300 lines (exclude: generated files, config files, test files with many similar cases)
- **No committed secrets** — look for `.env` files with real values, hardcoded API keys, passwords, or tokens in source files

## Audit: Code-Level Checks

Scan source files for these violations. For each, record the file path and line number.

### Use Objects for Related Values
Look for functions/methods with more than 4 parameters. These should use a DTO/config object instead.

### String Constants
Search for the same raw string literal appearing in 3+ different files. These should be centralized in a constants module.

### Error Handling & Logging
- Look for raw output statements (`print`, `console.log`, `echo`, `Console.WriteLine`) used outside of test files — should use structured logging
- Look for scattered try/catch blocks that don't delegate to a centralized error handler

### No God Classes
Flag classes that show warning signs:
- More than 5 public methods
- More than 4 constructor dependencies
- Methods spanning unrelated domains (e.g., validation + database + notification in one class)

### Self-Describing Classes
Look for patterns where field/property lists are hardcoded externally instead of being declared by the class itself through an interface or contract. Common signs:
- Switch statements or if-chains that enumerate fields of another class
- Arrays/lists of field names referencing another class's properties
- Mapping functions that manually list which fields to include

### DRY Violations
Look for obvious code duplication — the same logic block (5+ lines) appearing in multiple files. Flag with both locations.

### Naming Conventions
Check that files, classes, functions, and variables follow the project's language conventions:
- Python/PHP: `snake_case` functions, `PascalCase` classes
- Dart/JS/C#: `camelCase` functions, `PascalCase` classes
- Constants: `UPPER_SNAKE_CASE`

## Audit: Language-Specific Rules

If language-specific rules are in CLAUDE.md, also check those. Common checks:
- **Localization**: hardcoded user-facing strings instead of using the localization library
- **Framework patterns**: not following the framework's recommended patterns (e.g., raw fetch instead of API client, missing Pydantic validation at API boundaries)
- **SCSS specifics**: `@import` instead of `@use`/`@forward` in `.scss` files; selector nesting deeper than 3 levels; hardcoded color/spacing values that should use variables from `_variables.scss`

## Reporting

Present results grouped by rule:

```
## Violations Found

### [Rule Name] — X violations

- `path/to/file.ext:42` — description of the specific violation
- `path/to/file.ext:87` — description of the specific violation

### [Rule Name] — X violations
...

### Rules Passing
- Rule A ✓
- Rule B ✓
```

After presenting the report, ask the user:
1. Which violations they want to fix now
2. Whether any should be marked as acceptable exceptions (with justification)
