# Version
1

Increase this version number whenever this rule file changes.

# Python Desktop GUI (tkinter)

Applies on top of `PYTHON_RULES.md` when the project has a tkinter desktop interface.

## When tkinter Is Acceptable

PySide6 in [`python/GUI.md`](GUI.md) stays the default for new desktop applications. tkinter is
appropriate for small, standard-library-only tools that must ship as a tiny single executable,
such as setup or configuration helpers and one-window utilities.

Do not migrate an existing tkinter application to PySide6 by default. Migrate only when the human
asks or when the application outgrows tkinter, such as by needing many screens, rich styling, or
Qt-only widgets.

## Layout and Widgets

- Prefer `tkinter.ttk` widgets over classic widgets such as `tk.Button`, and configure a
  `ttk.Style` theme.
- Use one geometry manager per container: `grid` for forms and `pack` for simple stacks. Never mix
  them in the same parent.
- Set `columnconfigure` and `rowconfigure` weights so layouts resize correctly.
- Keep the window class responsible for building widgets and wiring events. Put business logic,
  file I/O, and subprocess calls in services.
- Construct services in the entry point and inject them into the window constructor.
- Keep `tk.Variable` objects on the window and convert their values to plain Python values before
  calling services.

See [`DESIGN_RULES.md`](../DESIGN_RULES.md) for design decisions.

## Threading

Tk is single-threaded; never access widgets from a worker thread. Run long operations such as
downloads, file copies, or subprocesses in a `threading.Thread(daemon=True)` or a
`concurrent.futures` executor. Return results through a `queue.Queue` polled with
`root.after(100, ...)`, or schedule UI updates with `root.after(0, callback)` on the Tk main
thread. Disable the controls that started the work while it runs. Show errors in the UI and the
log; never swallow them.

## Testing

Keep application logic in services that can be tested with plain pytest without starting Tk. For a
window smoke test, create `tk.Tk()` in a fixture, call `withdraw()`, build the window, call
`update_idletasks()`, assert that key widgets exist, then call `destroy()`. If creating `tk.Tk()`
raises `tk.TclError` because no display is available (for example, in CI), skip the smoke test with
`pytest.skip`. Never call `mainloop()` in tests.

## Single-File Packaging (PyInstaller)

Build from a batch file under `tools/` with `pyinstaller --onefile --windowed --name <tool>`.
Resolve bundled resources from `getattr(sys, "_MEIPASS", <source dir>)`, so the same code works
from source and from the extracted single-file bundle. Keep dependencies standard-library-only to
keep the executable small. For the broader release and installer workflow, see
[`python/RELEASE.md`](RELEASE.md) and [`python/INSTALLER.md`](INSTALLER.md).
