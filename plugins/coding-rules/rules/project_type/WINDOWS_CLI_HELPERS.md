# Version
1

Increase this version number whenever this rule file changes.

# Windows Command-Line Helper Collections

See `COMMON_RULES.md` for rules that apply to all projects. These additions target a folder of
small Windows commands on `PATH`, usually thin batch wrappers around a sibling script or tool.

---

## Scope and Pairing

Use this type for a helper collection without a language manifest, where users invoke root-level
`.bat` or `.cmd` commands by name. It covers Windows batch wrappers, Windows PowerShell 5.1
scripts, and small standalone Python helpers. Pair with `COMMON_RULES.md`; add
`AUTOHOTKEY_RULES.md` when the collection contains `.ahk` scripts. Add `PYTHON_RULES.md` only
for a subfolder with its own `pyproject.toml`. Do not add `DESIGN_RULES.md` to a headless command
collection.

Keep `README.md` mandatory. The common test-driven development, integration-test, and standard
test-runner requirements are relaxed for thin wrappers; see Testing. A Python helper with real
logic still has focused unit tests. Common centralized logging does not fit short command-line
helpers: print usage and operational errors to stderr with a useful message and return a non-zero
exit code. A launcher may contain a machine-specific path to another checkout; keep it in one
`PROJECT_ROOT` variable at the top (or use an environment variable with a default) instead of
repeating the path.

---

## First-Party Code vs. Vendored Files

First-party code is the `.bat`, `.cmd`, `.ps1`, `.py`, and `.ahk` written for this collection,
plus its `docs/`. Treat committed `.exe`, `.dll`, `.jar`, `.phar` files, bundled folders such as
`gradle/`, `poppler/`, and `mpv/`, and copied third-party source such as
`python/classes/external/` as vendored.

Never edit, reformat, lint, or otherwise “fix” vendored files. Update a bundle by replacing it as
a whole. Keep a **Vendored tools** section in `README.md` with each tool's name, source URL, and
version; add an entry in the same change that adds a binary or bundle. Exclude vendored files and
folders from code-analyzer configuration.

---

## Batch Wrappers

Use one command per file and a lower-case, hyphenated filename that names what the user types.
Start every `.bat` or `.cmd` file with `@echo off`, then use `setlocal` near the top so internal
variables do not leak to the caller.

<!-- steps: review, code -->
### Arguments, paths, and exit codes

- Quote every path and argument, including positional arguments as `"%~1"`. Forward all user
  arguments with `%*` when the wrapper does not interpret them.
- Refer to a sibling file as `"%~dp0name"`. `%~dp0` already ends in a backslash; do not add
  another one.
- Compare flags case-insensitively with `if /i`. For missing required arguments, print a usage
  line to stderr (for example, `>&2 echo Usage: command <name>`) and return `exit /b 1`.
- Propagate a child's result immediately after the call with `exit /b %ERRORLEVEL%`. Run another
  batch file with `call`; never wrap a batch call in `cmd /c`.
- Change directories with `pushd` and `popd`, not `cd`. Never define a `:EOF` label because it
  shadows the built-in `goto :eof` target.
- Enable delayed expansion only around the block that needs it. When a value must escape
  `setlocal`, use a deliberate hand-out such as `endlocal & set "X=%X%"` or
  `endlocal & cd /d "%TARGET%"`.
- A launcher for another checkout keeps its path in one `set "PROJECT_ROOT=..."` at the top, or
  reads an environment variable and supplies a default.

### PowerShell launcher

Launch a same-named PowerShell script from its batch wrapper and return its exit code:

```bat
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dpn0.ps1" %*
exit /b %ERRORLEVEL%
```

PowerShell starts a batch file in a child `cmd.exe`, so a command that must change the caller's
current directory also needs a same-named `.ps1` twin for use from PowerShell.

---

## PowerShell Scripts (Windows PowerShell 5.1)

Write scripts for Windows PowerShell 5.1. Do not use PowerShell 7-only syntax such as `&&`, `||`,
`??`, or the ternary operator. Use a `param()` block with typed parameters; mark required values
with `[Parameter(Mandatory)]`. Set `$ErrorActionPreference = 'Stop'` so command failures cannot
silently continue.

Use `-LiteralPath` and `-Encoding UTF8` with `Get-Content`, `Set-Content`, `Out-File`, and
`Add-Content`. Save a `.ps1` containing non-ASCII text as UTF-8 with a BOM: Windows PowerShell
5.1 reads BOM-less scripts as ANSI. After a native executable call, exit with its
`$LASTEXITCODE`; when handling a failure without a native exit code, exit with `1`.

If a script temporarily changes an `$env:` value, restore the original value in `finally`, even
when the operation fails. Send data through the pipeline with `Write-Output`, ordinary user
messages with `Write-Host`, and errors with `Write-Error`.

---

## Standalone Python Helpers

Keep a small helper as one script plus, when needed, a small helper-module folder. Launch it from
a batch wrapper with a script path anchored to the wrapper:

```bat
python "%~dp0python\name.py" %*
```

Use `argparse`, put the command behavior behind `def main() -> int`, and end with
`sys.exit(main())`. Prefer the standard library; if third-party packages are needed, the wrapper
must invoke a named virtual environment. Send errors to stderr and return a non-zero exit code.
Keep settings in a JSON file beside the script with a committed `.example` template, and
gitignore generated state and cache files.

When the helper grows dependencies, several modules, or meaningful test needs, move it into its
own uv-managed repository using `PYTHON_RULES.md` and leave this collection with only the batch
launcher. The `fav.bat` pattern is an example of that boundary.

---

## Testing

Thin wrappers do not require the common TDD, integration-test, or `tools/run_tests.bat` rules.
Verify a wrapper by hand: run it with no arguments and check its usage and exit code `1`; run it
with typical arguments; run it from another working directory to prove its `%~dp0` paths work;
and inspect `%ERRORLEVEL%` after both success and failure.

A Python helper with real parsing, branching, or other command logic keeps a standard-library
`unittest` file. Add `tools/run_tests.bat` for that helper, following the common rules for
progress output and preserving the test runner's exit code.

---

## Documentation

List every command in `README.md`, with a one-line description and a usage example. Give longer
commands a dedicated `docs/<COMMAND>.md` page and link to it from the README.

---

## graphify

First-party commands live at the repository root, so configure the code directory as `.`. Add a
root `.graphifyignore` to keep vendored code and non-code files out of the graph. At minimum,
exclude vendored bundle folders, copied third-party source folders, `*.exe`, `*.dll`, `*.jar`,
`*.phar`, and `*.pdb`; also exclude `*.md`, `*.json`, `docs/`, `tickets/`, `claude-plans/`, and
`graphify-out/`. Add any other vendored paths present in the collection. This keeps the graph
focused on first-party code and avoids the non-code LLM pass. See the flat-root graphify guidance
in the apply skill.
