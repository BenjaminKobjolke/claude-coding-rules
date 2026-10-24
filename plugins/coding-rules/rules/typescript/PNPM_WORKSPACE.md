# Version
1

Increase this version number whenever this rule file changes.

# TypeScript pnpm Workspace Rules (Node, vitest)

See `COMMON_RULES.md` and `TYPESCRIPT_RULES.md`.

## Workspace Layout

- Define `apps/*` and `packages/*` in `pnpm-workspace.yaml`.
- Keep the root `package.json` `private`, declare `packageManager` and `engines.node`, and put only workspace-wide fan-out scripts there (for example, `pnpm -r build`, `pnpm -r test`, and `pnpm -r typecheck`).
- Use ESM with `"type": "module"`. Node is the runtime; do not use Bun APIs.

## TypeScript Configuration

- Keep one strict `tsconfig.base.json` at the root with the compiler options in `TYPESCRIPT_RULES.md`.
- Every package has a `tsconfig.json` that extends the base and sets only package-specific `types`, `paths`, `include`, and `outDir`.
- Path aliases belong to the package that owns them. They must resolve the same way in the bundler (Vite `resolve.alias`) and in vitest; define them once and derive the other configuration, or keep both definitions together.
- Set `types` for each package's runtime and environment as described in `TYPESCRIPT_RULES.md`; do not mix Node and DOM types in one package.

## Package Boundaries

- Apps depend on workspace packages through `workspace:*` dependencies. Packages never import from `apps/*`.
- Cross-package imports use the package name and its `exports`; never reach into another package's `src/` with relative paths.
- Keep packages free of dependency cycles. Move shared code into a package rather than copying it between apps, following the DRY rule in `COMMON_RULES.md`.

## Testing with vitest

- Place `*.test.ts` and `*.test.tsx` next to their source or in the package's `tests/` directory. Each package runs its own `vitest run` script.
- Set DOM tests to a `jsdom` or `happy-dom` environment in that package's vitest config. Node packages use the Node environment.
- Use typed dependency injection seams as described in `TYPESCRIPT_RULES.md`.
- `tools/run_tests.bat` runs unit suites with per-test progress, such as `pnpm -r --workspace-concurrency=1 test -- --reporter=verbose`. `tools/run_integration_tests.bat` runs integration suites. Both scripts follow COMMON_RULES.md's “Test Runner Scripts”: stream progress and return the runner's exit code.

## Errors and Logging

- Each app has one top-level error handler, following `COMMON_RULES.md` -> “Error Handling”: a React error boundary in each renderer or SPA, and `process` handlers in the Node server and Electron main process.
- Use one `logger.ts` per the COMMON_RULES.md logger table. Put it in a shared package when several apps use it.

## Linting and Type Checking

- Keep an ESLint flat config with typescript-eslint at the workspace root.
- Give every package a `typecheck` script that runs `tsc --noEmit`.
- Follow COMMON_RULES.md -> “Confirm Dependency Versions” when adding a package.

## Required Batch Files
<!-- steps: review, code -->

Provide these batch files in `tools/`:

- `tools/install.bat` runs `pnpm install`.
- `tools/build.bat` runs the workspace build.
- `tools/run_tests.bat` runs unit test suites and streams progress.
- `tools/run_integration_tests.bat` runs integration suites and streams progress.

Each script returns the command's exit code and never waits for a keypress.
