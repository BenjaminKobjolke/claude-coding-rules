# Version
1

Increase this version number whenever this rule file changes.

# Obsidian Plugin Rules (TypeScript)

These rules cover community plugins for Obsidian. See `COMMON_RULES.md` for rules that apply to
every language.

## Scope and pairing

Use this file when the root `manifest.json` has `minAppVersion` and `package.json` depends on
`obsidian`. Pair it with `TYPESCRIPT_RULES.md`. Add `DESIGN_RULES.md` when the plugin has a
settings tab, modal, or custom view. Never apply `JAVASCRIPT_RULES.md`; its Bun CLI conventions
(`bin`, shebangs, process exit codes, and `~/.app/settings.json`) do not apply to plugins.

## Runtime

The plugin runs inside Obsidian: in an Electron renderer on desktop and a webview on mobile. Use
browser and Obsidian APIs at runtime. Node.js is for building and testing only.

`fs`, `child_process`, and `electron` are available only on desktop. Set `isDesktopOnly: true` in
`manifest.json` when the plugin cannot work without them. Otherwise guard desktop-only behavior
with `Platform.isDesktopApp` and load Node or Electron modules with `require()` inside that guarded
path. Never use top-level imports for desktop-only modules.

Use Obsidian's `requestUrl` instead of `fetch` for cross-origin HTTP requests.

## TypeScript configuration

Use a strict `tsconfig.json` with `noUncheckedIndexedAccess`, `noEmit`,
`allowImportingTsExtensions`, `isolatedModules`, and `verbatimModuleSyntax`. Include `DOM` in
`lib`, and allow `types: ["node"]`: plugins use DOM APIs at runtime, while Node types support
tests and guarded desktop code. This is the sanctioned DOM and Node type mix for this project
type. `tsc --noEmit` checks types; esbuild emits the plugin bundle.

## Project structure

Keep the plugin's source organized by feature:

```text
manifest.json
versions.json
package.json
esbuild.config.mjs
styles.css
tsconfig.json
src/
  main.ts                    # Plugin subclass and wiring only
  <feature>.ts
  <module>.test.ts           # Tests beside the module
tools/
docs/
```

Treat generated `main.js` and user data `data.json` as output: gitignore them and never edit them
by hand.

## Plugin lifecycle

Keep `src/main.ts` as a thin adapter that extends `Plugin` and wires features together. Register
commands, events, DOM events, intervals, and cleanup callbacks through `this.addCommand`,
`this.registerEvent`, `this.registerDomEvent`, `this.registerInterval`, and `this.register` so
Obsidian can clean them up when the plugin unloads.

Defer expensive startup work to `app.workspace.onLayoutReady`. Use `this.app`, never the global
`app`. Do not detach leaves in `onunload`; let Obsidian manage its views. Do not assign default
hotkeys to commands.

## Obsidian API boundary

Keep modules that import runtime values from `obsidian` (`Plugin`, `Notice`, `Modal`, `Platform`,
or `requestUrl`) as thin adapters. Logic modules may use `import type` from `obsidian`, but must
not import runtime values: the npm package supplies types, and value imports fail under
`node --test`.

Prefer `this.app.vault` methods such as `read`, `process`, and `create` over `vault.adapter`.
Read and update frontmatter through `this.app.fileManager.processFrontMatter`. Normalize
user-supplied paths with `normalizePath` before using them.

## Settings

Define one `XxxSettings` interface and a frozen `DEFAULT_SETTINGS` value. In `loadSettings()`,
treat `await this.loadData()` as `unknown`, validate its shape, and merge valid values over the
defaults. Do not use `any`. Save settings through `this.saveData()`. Put settings UI in one
`PluginSettingTab`.

## UI and DOM

Build elements with Obsidian helpers such as `createEl`, `createDiv`, and `setText`. Never put
data into `innerHTML`. Keep styles in `styles.css` and use Obsidian CSS variables; do not use
inline styles. Write user-facing text in sentence case. Report user-visible failures with a
`Notice`.

## Errors and logging

Export `logger` from `logger.ts` as specified by the logger table in `COMMON_RULES.md`; route all
logging through it and keep it off or warning-only by default. Every command, event, and settings
callback must catch and log failures and leave the UI in a defined state.

## Testing
<!-- steps: review, code -->

Use `node:test` and `node:assert/strict`. Set `npm test` to run
`node --test "src/**/*.test.ts"` on Node.js 22.18 or newer, where type stripping runs `.ts` files
without a flag. Relative imports in tests use the `.ts` extension.

Code reached by tests must use erasable TypeScript syntax: no `enum`, `namespace`, or constructor
parameter properties. Enable `erasableSyntaxOnly` once the whole plugin complies. Keep tested
modules free of runtime imports from `obsidian`; test pure logic with typed fakes such as
`Partial<XxxDeps>`. Check behavior that depends on Obsidian itself by hand in a test vault.

## Build and release
<!-- steps: review, code -->

Use an esbuild config based on the official Obsidian sample plugin. Bundle `src/main.ts` as CJS
to `main.js`; mark `obsidian`, `electron`, `@codemirror/*`, `@lezer/*`, and Node builtins as
external. Production builds are minified without sourcemaps; development builds watch and include
inline sourcemaps.

Set `npm run build` to run `tsc --noEmit --skipLibCheck` followed by
`node esbuild.config.mjs production`. Release assets are `main.js`, `manifest.json`, and
`styles.css`. Use the release version in `manifest.json` and keep `package.json` and
`versions.json` (plugin version to `minAppVersion`) in sync. Pin `obsidian` to a checked version,
not `latest`, following `COMMON_RULES.md` -> “Confirm Dependency Versions”. Keep runtime
dependencies at zero by default.

## Required batch files
<!-- steps: review, code -->

Provide `tools/build.bat` to run `npm run build` and `tools/run_tests.bat` to run `npm test`.
When a local deploy script is useful, copy the release assets to each vault's
`.obsidian/plugins/<id>/` directory using vault paths in a gitignored `tools/vaults.json`; commit
`tools/vaults.example.json` as its template. Use the analyzer scripts from
`javascript_setup_files/tools/` with `LANGUAGE=javascript`.

## Naming

Use snake_case module file names, camelCase functions, PascalCase classes, and UPPER_SNAKE_CASE
constants.
