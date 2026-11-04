# Version
1

Increase this version number whenever this rule file changes.

# Browser Widget Rules (JavaScript, npm + webpack)

These rules apply to classic JavaScript widgets built with npm and webpack and loaded by a
separate host page. See `COMMON_RULES.md` for rules that apply to every language.

## Scope

Use this file instead of `JAVASCRIPT_RULES.md` for browser widgets bundled for an external host.
Pair it with `COMMON_RULES.md` and `DESIGN_RULES.md`. Do not select
`project_type/FRONTEND.md`: that rule is for a Vite SPA that owns the page. TypeScript widgets
also use `TYPESCRIPT_RULES.md`.

## Layout
<!-- steps: review, code -->

Keep each independently built widget in its own folder:

```text
<widget>/
├── package.json
├── package-lock.json
├── src/scripts/app.js
├── webpack/base.js
├── webpack/prod.js
├── index.html
├── tools/build.bat
├── docs/
└── README.md
```

Commit each `package-lock.json`. Put pure modules shared by multiple widgets in
`shared/src/scripts/`; a widget must never import another widget's folder. `index.html` is a
local development harness, not a production page.

## Module system

Write widget source as ESM and transpile it with `babel-loader`. Keep webpack configuration files
CommonJS. Do not set `"type": "module"` in `package.json` unless the webpack configuration files
are renamed to `.cjs`.

## Browser globals and instances
<!-- steps: review, code -->

The only global the bundle writes is its host registry entry. Use the host's documented registry
and tool id, and make registration safe to evaluate more than once:

```js
window.AXExternalTools = window.AXExternalTools || {};
window.AXExternalTools.toolId = { mount };
```

Do not depend on other host-page globals such as jQuery or host helpers. Read browser APIs such as
`document`, `matchMedia` and `ResizeObserver` only inside `mount` or functions it calls. Avoid
module-level mutable state, document-wide ids and selectors; query within the supplied container.
Multiple mounted instances must work independently on the same page.

## Mount contract

Export `mount(container, config, api)` and return an object with `destroy()`. Keep per-instance
state in the mount closure. `destroy()` disconnects observers, stops timers and animations, and
removes everything the widget added. Size the widget to its container rather than the window.
Report results only through the host-provided `api`.

## Config at the boundary

Implement one `normalizeConfig()` in `<widget>_config.js` and a frozen `DEFAULT_CONFIG`. Normalize
every field to its expected type and default; missing, empty or invalid input must produce usable
defaults. Keep the host's server-side sanitizer in sync rule for rule with `normalizeConfig()`.
Document the counterpart in the widget README; a change to either sanitizer requires changing the
other in the same feature. Follow the JavaScript equivalent of COMMON's “No Bag-of-Keys Returns”:
use a documented object shape instead of loosely shaped key bags at module boundaries.

## Bundling

Production output is one self-contained `dist/bundle.min.js` per widget. Bundle every dependency
and asset: no CDN, runtime fetch, or separate image or font files. Draw graphics procedurally or
embed data URIs. Import only needed submodules (for example, scoped `@pixi/*` packages or
`gsap/gsap-core`). Replace an unneeded Node built-in with a small `resolve.alias` shim rather than
adding a polyfill package.

`webpack/prod.js` sets `mode: "production"`, `devtool: false`, and configures its minifier to strip
comments. Set `performance.maxEntrypointSize` and `performance.maxAssetSize` as the bundle budget.
Declare every package required by webpack config in `devDependencies`, and runtime libraries in
`dependencies`. Confirm package versions against current stable releases as required by COMMON.

## Development harness

`npm start` runs webpack-dev-server on `index.html`. The harness mounts the widget with a sample
config and a fake `api` that logs reported values, so behavior can be developed without the host
application.

## Deploy artifacts

Treat `dist/` as ignored build output. The widget repository does not commit bundles; the receiving
project commits the delivered copy. `tools/build.bat` runs from the widget root, installs packages
when `node_modules/` is missing, builds, verifies the bundle exists, copies it to the target, and
returns a non-zero exit code on every failure.

Read the target from an environment variable or a gitignored `tools/build_config.bat`, with a
committed `build_config.example.bat` documenting the setting. Never use a hardcoded default path;
follow COMMON's “No Hardcoded Environment Values”. A missing target stops with a clear message.

## Errors and logging

Use one `logger.js` in `shared/`, exporting the `logger` used by the COMMON logger table. Do not
call `console.*` outside that logger or use `alert`. `mount` catches setup errors, logs context and
leaves a short fallback message in its container instead of throwing into the host page. Attach a
`.catch()` handler to animation promises and log failures.

## Linting

Use ESLint flat config. Configure `src/**` and `shared/**` with `sourceType: "module"` and browser
globals; configure `webpack/**` with `sourceType: "commonjs"` and Node globals. Ignore `dist/**`
and `node_modules/**`.

## Testing

Keep config normalization, weighted selection and geometry in pure modules that import no
renderer or DOM. Inject randomness (`random = Math.random`) so tests can be deterministic. Use
built-in `node --test` (Node 22 or newer) for unit tests under `<widget>/tests/*.test.js` and
`shared/tests/`.

The integration test builds the production bundle and loads it to assert that `mount` registers
under the host tool id. If the renderer needs a real DOM at load time, use a headless browser with
the development harness. Root `tools/run_tests.bat` and `tools/run_integration_tests.bat` run the
corresponding suites across widgets, stream progress, and return the runner's exit code; follow
COMMON's “Test Runner Scripts”.

## Names and constants

Use `snake_case` file names, `camelCase` functions, `PascalCase` classes and `UPPER_SNAKE_CASE`
constants. Define enum-like constant objects with `Object.freeze` in the module that owns them.

## Documentation

Each widget README documents its config shape and defaults and the host `api` calls it makes. Put
feature-specific documentation in `<widget>/docs/`.

## Code analysis

Copy `javascript_setup_files/tools/analyze_code_config.example.bat`, `analyze_code.bat` and
`analyze_changed_and_new_files.bat` into the project's `tools/`. Set `LANGUAGE=javascript`, keep
the config itself gitignored, and configure `fail_on` as `warning`.
