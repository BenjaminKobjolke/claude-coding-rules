# Version
1

Increase this version number whenever this rule file changes.

# Electron Rules (TypeScript)

Pair with `TYPESCRIPT_RULES.md`, `typescript/PNPM_WORKSPACE.md`, and
`project_type/FRONTEND.md`.

## Process Boundaries

Keep Electron's three entry points separate:

- `main/` runs in Node and owns windows, operating-system access, and IPC handlers.
- `preload/` exposes the narrow bridge between the main process and the renderer.
- `renderer/` runs in the browser and usually contains the shared web UI.

Renderer code must never import Node or Electron modules. Keep Node-only types
out of its TypeScript configuration, and share UI code with the web app through
workspace packages rather than reaching into app source folders.

## Secure Windows

Create each `BrowserWindow` with these settings:

```ts
webPreferences: {
  contextIsolation: true,
  nodeIntegration: false,
  sandbox: true,
  preload: preloadPath,
}
```

Never load remote content into a window that has a preload script. Keep the
preload small and expose only the operations the renderer needs.

## Typed Preload Bridge

Expose one typed API with `contextBridge.exposeInMainWorld`. Put its interface
in a shared module imported by both the preload and renderer so the bridge
contract has one source of truth. Do not expose Node objects, Electron modules,
or unrestricted filesystem access.

Keep IPC channel names in that shared module as `as const` constants, following
COMMON_RULES.md -> “String Constants”:

```ts
export const IPC_CHANNEL = {
  READ_PROJECT: 'project:read',
} as const;
```

Expose named, typed API methods that use the approved channels. Do not provide a
generic bridge such as `invoke(channel, ...args)` that lets renderer code call
any channel.

## Validate IPC at the Main Boundary

Treat every IPC argument as `unknown` in the main process. Validate its shape
and values before using it, following COMMON_RULES.md -> “Input Validation at
Boundaries”. Types shared with the renderer do not validate data at runtime.
Reject invalid input with a clear error and never trust a renderer-provided
filesystem path, URL, or identifier without checking it against the operation's
allowed values.

## Packaged Renderer Assets

The packaged renderer loads assets from files. Set the desktop build's Vite
base to `./`; a web build may use `/`. Follow `project_type/FRONTEND.md` ->
“Base Path” to select the base per build target without hard-coding a deployment
subpath.
