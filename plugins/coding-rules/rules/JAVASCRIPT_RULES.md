# Version
1

Increase this version number whenever this rule file changes.

# JavaScript Rules (Bun / Node, ESM)

See `COMMON_RULES.md` for rules that apply to all languages.
See `TYPESCRIPT_RULES.md` for the TypeScript type layer on top of these conventions.

## Runtime & Module System

Use Bun as the runtime. ESM is mandatory — no CommonJS in new code.

`package.json` must declare:

```json
{
  "type": "module",
  "bin": { "<appname>": "src/main.js" },
  "scripts": {
    "start": "bun run src/main.js",
    "build": "bun build --compile --outfile <appname>.exe src/main.js",
    "test": "bun test"
  },
  "engines": { "bun": ">=1.0.0" }
}
```

The entry point starts with a shebang so it is directly executable:

```js
#!/usr/bin/env bun
```

---

## Project Structure

CLI application layout (generalizes to libraries and servers — keep the
`core/` shared-module split either way):

```
project/
├── src/
│   ├── main.js          # Entry point (shebang, dispatches to cli.js, process.exit)
│   ├── cli.js           # Command router + dispatch, central try/catch → exit codes
│   ├── cli_args.js      # Hand-rolled arg parsers, one parseXxxArgs() per command
│   ├── commands/        # One file per command, each exports runXxx(input)
│   │   └── <cmd>.js
│   └── core/            # Shared modules: errors.js, settings.js, logger.js, …
├── tests/               # bun test files: *.test.js
├── tools/               # build.bat, run_tests.bat, run_integration_tests.bat
└── docs/
    └── commands/        # One md per command
```

`cli_args.js` is split from `cli.js` deliberately — router and parsers together
exceed the 300-line file rule.

---

## CLI Argument Parsing

Hand-roll the parser — no yargs/commander for small CLIs (KISS; zero runtime
deps). One `parseXxxArgs(args)` per command in `cli_args.js`, a plain `for`
loop over tokens, and a shared `requireValue()` helper. Invalid input throws
`AppError` with `INPUT_INVALID` (see Error Handling):

```js
export function parseAskArgs(args) {
  const positional = [];
  let timeoutSeconds = 120;

  for (let i = 0; i < args.length; i += 1) {
    const token = args[i];

    if (!token.startsWith('-')) {
      positional.push(token);
      continue;
    }

    if (token === '--timeout') {
      const value = Number(requireValue(args, i, '--timeout'));
      if (!Number.isFinite(value) || value <= 0) {
        throw new AppError(ERROR_CODE.INPUT_INVALID, 'Invalid --timeout value', {
          hint: 'Use a positive number of seconds.'
        });
      }
      timeoutSeconds = Math.floor(value);
      i += 1;
      continue;
    }

    throw new AppError(ERROR_CODE.INPUT_INVALID, `Unknown option: ${token}`);
  }

  return { prompt: positional.join(' '), timeoutSeconds };
}

function requireValue(args, index, flag) {
  const value = args[index + 1];
  if (!value || value.startsWith('-')) {
    throw new AppError(ERROR_CODE.INPUT_INVALID, `Missing value for ${flag}`, {
      hint: `Provide a value after ${flag}.`
    });
  }
  return value;
}
```

---

## Error Handling

One `AppError` class for the whole app, plus const-object enums for error and
exit codes, all in `src/core/errors.js`. Freeze the enum objects
(`Object.freeze`) in new code. No scattered ad-hoc `throw new Error(...)` at
boundaries — normalize everything through `toAppError()` and map to process
exit codes in exactly one place:

```js
export const ERROR_CODE = Object.freeze({
  INPUT_INVALID: 'INPUT_INVALID',
  NETWORK_ERROR: 'NETWORK_ERROR',
  CONFIG_INVALID: 'CONFIG_INVALID',
  UNKNOWN: 'UNKNOWN'
});

export const EXIT_CODE = Object.freeze({
  SUCCESS: 0,
  GENERIC: 1,
  INPUT_INVALID: 2,
  NETWORK: 4,
  CONFIG: 6
});

export class AppError extends Error {
  constructor(code, message, extra = {}) {
    super(message);
    this.name = 'AppError';
    this.code = code;
    this.hint = extra.hint;
    this.details = extra.details;
    this.cause = extra.cause;
  }
}

// Every caught error becomes an AppError before it reaches the top-level handler.
export function toAppError(err) {
  if (err instanceof AppError) return err;
  const message = err instanceof Error ? err.message : String(err);
  return new AppError(ERROR_CODE.UNKNOWN, message || 'Unknown error');
}

export function exitCodeForError(err) {
  switch (err.code) {
    case ERROR_CODE.INPUT_INVALID: return EXIT_CODE.INPUT_INVALID;
    case ERROR_CODE.NETWORK_ERROR: return EXIT_CODE.NETWORK;
    case ERROR_CODE.CONFIG_INVALID: return EXIT_CODE.CONFIG;
    default: return EXIT_CODE.GENERIC;
  }
}
```

The router (`cli.js`) has the single top-level `try/catch`: it calls
`toAppError(err)`, writes `CODE: message` (+ optional `Hint: …`) to stderr,
and returns `exitCodeForError(err)`.

---

## Boundary Normalizers

Plain JS has no compile-time DTOs — enforce shapes at module boundaries with
`normalizeXxx()` functions that coerce loose external data (JSON, page
scraping, API responses) into a known object shape. Every field gets an
explicit type coercion and default; unknown input degrades to safe defaults
instead of `undefined` leaking through:

```js
function normalizeSurfaceState(value) {
  const object = value && typeof value === 'object' ? value : {};
  return {
    url: typeof object.url === 'string' ? object.url : '',
    editorReady: Boolean(object.editorFound),
    loginLike: Boolean(object.loginLike)
  };
}
```

This is the JS counterpart of COMMON_RULES "No Bag-of-Keys Returns at Module
Boundaries" — the normalizer's return shape IS the contract. In TypeScript
projects, typed DTOs replace these (see `TYPESCRIPT_RULES.md`).

---

## Settings / Config

Persist user settings as JSON at `~/.<appname>/settings.json`, owned by one
module `src/core/settings.js` with merge-write semantics. No hardcoded
environment values elsewhere (see COMMON_RULES):

```js
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { dirname, join } from 'node:path';

export function settingsPath() {
  return join(homedir(), '.<appname>', 'settings.json');
}

export function loadSettings() {
  const path = settingsPath();
  if (!existsSync(path)) return {};
  const parsed = JSON.parse(readFileSync(path, 'utf8'));
  return parsed && typeof parsed === 'object' ? parsed : {};
}

export function saveSettings(partial) {
  const path = settingsPath();
  const merged = { ...loadSettings(), ...partial };
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, `${JSON.stringify(merged, null, 2)}\n`, 'utf8');
  return merged;
}
```

Wrap parse/read failures in `AppError` with `CONFIG_INVALID` and a hint how
to fix or reset the file.

---

## Output & Logging

CLIs separate machine output from diagnostics strictly:

- **stdout** is for machine-readable results only: `JSON.stringify(result, null, 2)`.
- **stderr** carries errors as `CODE: message` plus optional `Hint: …` line.
- `console.*` is allowed only in interactive, human-facing commands (setup
  wizards, doctor checks) — never in machine-output paths.

For diagnostic logging use the central logger per the COMMON_RULES logger
table: a `logger` export in `src/core/logger.js` (`logger.ts` in TS) wrapping
the sink, with one config-driven level/off switch. Feature code never calls
`console.log` for logging.

---

## Linting

eslint with flat config (`eslint.config.js` at project root):

```js
export default [
  {
    files: ['**/*.js', '**/*.mjs', '**/*.cjs'],
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module'
    },
    rules: {
      'no-unused-vars': 'warn'
    }
  },
  {
    ignores: ['node_modules/**', 'coverage/**']
  }
];
```

---

## Build & Distribution

Ship CLIs as a single self-contained executable:

```bash
bun build --compile --outfile <appname>.exe src/main.js
```

When behavior must differ between compiled exe and source run, detect it once
in a core module and export the flag:

```js
export const IS_COMPILED =
  typeof Bun !== 'undefined' && (Bun.main.includes('~BUN') || Bun.main.includes('$bunfs'));
```

Dynamic imports that must land in the bundle need a literal specifier —
`bun build --compile` cannot follow computed paths.

---

## Testing

`bun test`, files under `tests/*.test.js`, importing from `bun:test`
(`describe`/`test`/`expect`/`beforeEach`/`afterEach`).

- **End-to-end CLI tests are the backbone**: drive `runCli([...argv])` and
  assert exit codes plus stdout/stderr substrings. This covers routing,
  parsing, and error mapping in one pass.
- **DI seams for side effects.** Modules with external effects (network,
  browser, sleep) export test-only setters so tests swap implementations
  without mocking frameworks:

```js
export function __setAskDepsForTest(deps) {
  if (deps.browserAskRunner) browserAskRunner = deps.browserAskRunner;
  if (deps.sleep) sleepImpl = deps.sleep;
}

export function __resetAskDepsForTest() {
  browserAskRunner = runBrowserAsk;
  sleepImpl = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
}
```

  Always reset in `afterEach` via the `__resetXxxDepsForTest()` counterpart.
- **Private functions** worth testing are exposed through one grouped export
  at the bottom of the module:

```js
export const __test__ = { normalizeSurfaceState, shouldRetry };
```

---

## 5 Essential Additional Rules (must-have)

1. **Required batch files** — `tools/build.bat` (runs the Bun compile build),
   `tools/run_tests.bat` and `tools/run_integration_tests.bat` (per
   COMMON_RULES Test Runner Scripts; they wrap `bun test`).
2. **Naming** — lowercase/snake file names (`cli_args.js`, `settings.js`),
   `camelCase` functions/variables, `PascalCase` classes, `UPPER_SNAKE`
   module-level constants.
3. **Constants placement** — const-object enums (`Object.freeze`) live in the
   module that owns the domain (`ERROR_CODE` in `errors.js`); per-feature
   string constants at the top of the owning command file. No stringly-typed
   values scattered through logic.
4. **Command docs** — one markdown per command under `docs/commands/<cmd>.md`
   (opens with `# <cmd>` + one-line purpose); topic docs at `docs/` root.
5. **Zero runtime dependencies by default** — Bun + `node:` builtins cover
   fs/path/os/fetch. Every new package needs the COMMON_RULES version
   confirmation, and a few lines of stdlib beat a dependency.
