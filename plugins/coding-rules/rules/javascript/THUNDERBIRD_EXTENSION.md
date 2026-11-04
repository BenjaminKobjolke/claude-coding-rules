# Version
1

Increase this version number whenever this rule file changes.

# JavaScript Rules (Thunderbird WebExtension)

These rules cover Thunderbird MailExtensions. See `COMMON_RULES.md` for rules that apply to
every language.

## Scope and pairing

Apply this file instead of `JAVASCRIPT_RULES.md` to Thunderbird add-ons. TypeScript add-ons also
use `TYPESCRIPT_RULES.md`. Add `DESIGN_RULES.md` when the add-on has popup or options UI.

## Runtime and module system

The extension runs in Thunderbird's WebExtension engine. Node.js is for tests and development
tools only. Use ESM in extension code, set `"type": "module"` in `package.json`, and set
`background.type` to `"module"` in the manifest. `web-ext-config.cjs` is the allowed CommonJS
exception for build configuration. Extension code has no Bun, shebang, `bin`, `process`, or
`node:` imports.

## Manifest and permissions

Use Manifest V3 for new add-ons. Existing add-ons may remain on MV2 until migrated. Set
`browser_specific_settings.gecko.id` once and keep it fixed across releases. Set
`strict_min_version` to the oldest supported Thunderbird ESR. Put user-visible manifest strings
in `_locales` and refer to them with `__MSG_*__`. The `manifest.json` version is the release
version; keep `package.json` in sync.

Request the least privilege needed. Justify each permission and `host_permissions` entry with the
feature that needs it. Prefer optional permissions for infrequently used features. Do not request
`<all_urls>`.

## Thunderbird APIs

Use the `messenger.*` namespace. Take the tab or window from the event argument; never assume one
is current. Obtain folder, account, and message IDs from the API instead of constructing them
from strings. Read paged results from `messages.list` and `messages.continueList` one page at a
time, following `COMMON_RULES.md` -> “API Clients”.

## Background event page

Thunderbird may suspend a Manifest V3 background when it is idle. Register every event listener
synchronously at the top level of the background module. Do not keep required persistent state
only in memory; store it with the WebExtension storage API. Put a top-level `try`/`catch` at each
listener entry point so an error does not escape the event handler.

## Experiments

Use an experiment only when no WebExtension API provides the needed capability. Keep each
experiment under `experiments/<api>/` with `schema.json` and `implementation.js`. Privileged code
stays minimal and does not call business logic. Remove every window listener and observer in
`onShutdown`. Read the experiment namespace once inside `try`/`catch`, so an unavailable or broken
experiment cannot take down the add-on. Re-test experiments against every new Thunderbird ESR;
they extend add-on review and maintenance work.

## Extension pages and content security

Popup and options pages are extension pages. Do not use inline scripts, `eval`, or remote code.
Build DOM with elements and `textContent`; do not put data into `innerHTML`.

## Settings

Own `storage.local` settings under one key in one options module. Define frozen `DEFAULT_OPTIONS`.
Implement `getOptions(storageArea)` to merge stored values over defaults, and inject the storage
area so the logic can be tested without the global API.

## Messaging

Define message types as frozen constants. Normalize message payloads at the receiving boundary
before business logic uses them.

## Errors and logging

Keep frozen `ERROR_CODE` values and one `AppError` / `toAppError()` module for application errors.
Do not leave catches empty. Each event or UI entry point must leave the user interface in a
defined state after an error.

Use boundary functions such as `normalizeOptions()`, `normalizeMessage()` and
`normalizeXxx()` for storage values, API results, and runtime messages. Treat external values as
untrusted and return a documented shape with safe defaults.

Export the shared `logger` from one module as specified by the COMMON_RULES logger table. Route
all logging through it, with one level or off switch; do not leave stray `console.log` calls.

## Localization

Store every user-visible string in `_locales/<language>/messages.json` and read it with
`messenger.i18n.getMessage`. English is the source locale. Keep locale key sets equal with a test.

## Project structure

Use a structure suited to the add-on's features:

```text
background.js
lib/                 # Pure logic with injected dependencies
popup/
options/
experiments/<api>/
_locales/
icons/
test/
tools/
docs/
```

## Testing
<!-- steps: review, code -->

Use `node --test` with `node:test` and `node:assert/strict`. Pass fake `messenger` and storage
objects into pure modules. For effects that cannot be injected, use test-only setters and reset
them after each test. Expose private functions through one `__test__` export when needed. Test
experiments by hand in Thunderbird.

## Linting

Use ESLint flat config. Lint extension modules with browser globals and readonly `messenger` and
`browser` globals. Lint `experiments/**` as `sourceType: "script"` with `ChromeUtils`,
`ExtensionCommon`, `Services`, and `Ci` globals. Configure tools and tests with Node globals.

Run `web-ext lint`. It validates against Firefox and reports `MANIFEST_FIELD_PRIVILEGED` for
Thunderbird's `experiment_apis`; filter exactly that error and no others.

## Build and distribution
<!-- steps: review, code -->

Build with `web-ext build` and a `web-ext-config.cjs` `ignoreFiles` list that excludes every
development-only tree, including tests, docs, tools, plans, temporary files, and package files.
Check the built `.xpi` contents whenever a folder is added. Run locally with
`web-ext run --firefox-binary thunderbird`.

Keep runtime dependencies at zero; `web-ext` and ESLint are development dependencies. Provide
`tools/build.bat` (or the existing project build batch file) to wrap `npm run build` and
`tools/run_tests.bat` to wrap `npm test`. Use the scripts from
`javascript_setup_files/tools/` for cli-code-analyzer configuration and commands.

## Naming

Use camelCase module file names and functions, PascalCase classes, and UPPER_SNAKE_CASE
constants.
