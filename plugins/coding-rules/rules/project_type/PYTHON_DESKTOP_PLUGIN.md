# Version
1

Increase this version number whenever this rule file changes.

# Python Desktop Host Plugin Rules

These rules apply to Python code that a desktop application discovers, loads, and runs inside its
own process or plugin runtime. Examples include fman extensions. Pair this file with
`COMMON_RULES.md` and `PYTHON_RULES.md`; add `DESIGN_RULES.md` when the plugin provides a user
interface of its own. These rules do not apply to a standalone Python desktop application. For a
standalone PySide6 application, use `python/GUI.md` instead.

The host owns startup, plugin discovery, command registration, UI integration, and its runtime.
Treat its documented plugin API as the boundary between the plugin and the host.

## Use the Host's Extension API

- Read the host's current plugin documentation and supported-version notes before relying on an
  API. Use documented extension points for commands, events, dialogs, settings, tasks, and file
  operations. Do not depend on private modules, undocumented attributes, or host internals.
- Keep host-facing code at the plugin boundary. Put reusable business logic in ordinary Python
  functions or classes that do not import the host SDK; this keeps that logic usable in tests and
  other tools.
- Let the host discover and register extensions using its documented layout and naming rules. Do
  not add a second registration mechanism or run plugin initialization manually unless the host
  requires it.
- Make module import safe: avoid starting work, changing files, showing UI, or mutating global host
  state at import time. Keep initialization small and safe if the host reloads the plugin.
- Check the host and plugin versions at runtime only through documented compatibility APIs. When a
  feature is unavailable, report a clear, actionable message or disable the affected command.

## Commands and User Interaction

- Choose the command base that matches the host context: use a pane-, document-, or selection-bound
  command when it needs that context, and a global command when it does not.
- Validate host-provided selections and context before acting. Handle empty selections, missing
  active documents, unsupported item types, and unavailable services as normal cases.
- Use the host's dialogs, prompts, notifications, and status messages. Avoid blocking console input
  or creating a second UI toolkit for a small interaction that the host already supports.
- Treat cancellation as a distinct result. Do not save settings, start work, or mutate files after a
  prompt or file picker was cancelled. Validate accepted values before using or persisting them.
- Show commands only when their context is supported when the host provides a visibility or
  enablement hook. Keep labels and aliases short, descriptive, and distinct from built-in commands.
- Confirm destructive or broad operations through the host UI, describe their scope, and provide a
  safe way to cancel before work begins.

## Long-Running Work

- Keep command callbacks responsive. Move work that may take noticeable time into the host's
  documented task, job, or background-work API so the host can report progress and cancellation.
- Report progress when the host supports it. Check for cancellation inside long loops and between
  expensive or externally visible operations; stop promptly and leave data in a consistent state.
- Keep UI calls on the execution context required by the host. From background work, use only the
  host's documented notification or task UI methods; do not call arbitrary UI functions from a
  worker.
- Avoid detached threads, subprocesses, or event loops for work the host can manage. If a separate
  process is required, use an argument list rather than a shell command string, capture its result,
  handle cancellation and shutdown, and do not assume the host will wait for it at exit.
- Do not keep work, timers, or callbacks alive after the host cancels or unloads the plugin unless
  the host explicitly supports that lifecycle.

## Filesystem and Host Data

- Use the host's file or resource API for items owned by the host, such as pane selections,
  documents, virtual filesystems, or project resources. Preserve host-specific identifiers and
  schemes; do not treat every item as a local operating-system path.
- Use Python's `pathlib` and standard file APIs for files the plugin itself owns, such as a
  temporary export or a local cache. Keep those paths within an appropriate user-writable location
  provided by the host or operating system, never in the plugin installation directory.
- For writes through a host filesystem API, follow its documented create, replace, notification,
  and cache-invalidation rules so the host sees the result immediately.
- Avoid scanning or rewriting more data than the command needs. Confirm the target and scope before
  destructive operations, and handle permission errors, missing files, and unsupported locations
  without corrupting partial results.

## Configuration and Dependencies

- Store user preferences through the host's settings or persistence API when it provides one. Use a
  namespaced settings key, preserve unrelated settings, validate loaded values, and provide safe
  defaults for missing or malformed data.
- Keep secrets out of plugin source, bundled settings, logs, and shared configuration files. Use
  the host's documented credential storage when available; otherwise explain the supported secure
  configuration path and never silently fall back to a hard-coded secret.
- Keep runtime dependencies minimal and compatible with the Python version and packaging model of
  the host. Do not assume the host's interpreter has developer packages or the latest standard
  library. Declare dependencies using the host's documented plugin mechanism.
- Do not install packages, modify the host interpreter, or change another plugin's environment at
  runtime. Document any native-library, operating-system, or host-version requirements.
- Keep optional integrations optional. A missing external program or service should disable only
  the affected operation and produce a useful message.

## Testing Without the Host

- Keep parsing, validation, transformation, and other domain logic independent of the host API so
  unit tests can run with the project's ordinary Python test runner.
- At the host boundary, use small adapters or injected collaborators. Fake those interfaces in unit
  tests; do not import a private host installation path or patch undocumented host internals.
- Test cancellation, empty or unsupported selections, invalid configuration, filesystem errors,
  and missing optional dependencies in the host-independent layer.
- When the host is not installed, skip only tests that truly require its runtime. Keep those checks
  focused, document the manual host check, and make skipped host tests visible in the test output.
- When the host is available, add a small integration or manual smoke check for discovery,
  registration, and the user-facing host interaction. Do not claim that mocked tests prove the
  plugin loads in the real host.

## Host-Specific Documentation

For fman plugins, consult the [plugin introduction](https://fman.io/docs/plugins-introduction)
and [Plugin API reference](https://fman.io/docs/api). In particular, fman commands should use
`ApplicationCommand` or `DirectoryPaneCommand` according to their scope, long operations should use
the documented `Task` and `submit_task` APIs, user prompts should use fman's dialogs, settings
should use its JSON persistence API, and file URLs should be handled with `fman.url` and `fman.fs`
where appropriate. These examples illustrate the host-boundary rules above; check the current fman
documentation for exact behavior and signatures.
