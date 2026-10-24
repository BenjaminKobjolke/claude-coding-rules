# Version
2

Increase this version number whenever this rule file changes.

# TypeScript Rules (Bun / Node)

See `COMMON_RULES.md` for rules that apply to all languages.

This file is the type layer for any TypeScript project. Runtime, layout, build,
and test conventions come from the paired runtime file:

- Bun CLI apps: `JAVASCRIPT_RULES.md` (all of it applies, with `.ts` file
  extensions).
- pnpm/Node workspaces: `typescript/PNPM_WORKSPACE.md` (do not apply
  `JAVASCRIPT_RULES.md`).
- Browser code bundled by another project type: that type's own section.

## tsconfig

Strict from day one:

```json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "target": "ESNext",
    "verbatimModuleSyntax": true
  }
}
```

`types` follows the runtime: `bun-types` for Bun, `node` for Node packages,
and `vite/client` for Vite browser apps. Never mix Node and DOM types in one
package.

Never weaken `strict` per-file. `// @ts-expect-error` needs a trailing reason
comment; `// @ts-ignore` is forbidden.

---

## No `any`

External data is `unknown`, never `any`. Narrow it with type guards or a
validation library before use. At module boundaries, typed DTOs/interfaces
replace the JS `normalizeXxx()` pattern — the type IS the contract, and the
compiler enforces what the JS normalizer only checks at runtime (see
COMMON_RULES "No Bag-of-Keys Returns at Module Boundaries"):

```ts
interface SurfaceState {
  url: string;
  editorReady: boolean;
  loginLike: boolean;
}

function parseSurfaceState(value: unknown): SurfaceState {
  const object = typeof value === 'object' && value !== null
    ? (value as Record<string, unknown>) : {};
  return {
    url: typeof object.url === 'string' ? object.url : '',
    editorReady: Boolean(object.editorFound),
    loginLike: Boolean(object.loginLike)
  };
}
```

Runtime coercion is still required for external input (the compiler cannot
verify data crossing the process boundary) — but the return type is declared,
so consumers are statically checked.

---

## Enums

Prefer union-of-literals or `as const` objects over `enum` (no runtime
surprises, erasable, better inference):

```ts
export const ERROR_CODE = {
  INPUT_INVALID: 'INPUT_INVALID',
  NETWORK_ERROR: 'NETWORK_ERROR',
  UNKNOWN: 'UNKNOWN'
} as const;

export type ErrorCode = (typeof ERROR_CODE)[keyof typeof ERROR_CODE];
```

Exhaustive `switch` over such unions must end with a `never` check so a new
member cannot be silently unhandled.

---

## Imports & Config Objects

- Type-only imports use `import type { … }` (enforced by
  `verbatimModuleSyntax`).
- Config/constant objects that must match an interface use `satisfies` so the
  literal keeps its narrow inferred type while still being checked:

```ts
const defaults = {
  timeoutSeconds: 120,
  format: 'json'
} satisfies AskOptions;
```

---

## Logging

Central logger per the COMMON_RULES logger table: `logger` export in
`logger.ts`. Same single-off-switch rule as the JS conventions.

---

## Testing

The test runner and file layout come from the runtime file. Typed seams apply
either way: the `__setXxxDepsForTest(deps)` parameter is a
`Partial<XxxDeps>` interface, so tests get completion and the seam cannot drift
from the real dependencies.
