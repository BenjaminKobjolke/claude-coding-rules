# Recipe: single-instance app (Windows)

Use when a second running copy would cause harm: background / tray apps, anything that
registers a global hotkey (the second registration fails or steals the first one's
callback), anything that owns a port, a device or a single state file.

A named Win32 mutex is the mechanism. The OS releases it when the process dies, so a
crash never leaves a stale lock behind (unlike a hand-rolled PID or lock file).

## Dependency

```bash
uv add pywin32
```

## `core/single_instance.py`

```python
"""Single instance manager: a second launch detects the first and exits."""

from __future__ import annotations

import win32api
import win32event
import winerror

from app_logger import AppLogger


class SingleInstance:
    """Ensures only one instance runs at a time, using a named Win32 mutex."""

    def __init__(self, app_name: str) -> None:
        self.mutex_name = f"Global\\{app_name}_SingleInstance_Mutex"
        self.mutex = None
        self._is_first = False

        try:
            # pywin32 stubs mistype lpMutexAttributes as required; None is the documented
            # "default security" value.
            self.mutex = win32event.CreateMutex(None, False, self.mutex_name)  # type: ignore[arg-type]
            already_running = win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS
            self._is_first = not already_running
            if already_running:
                AppLogger.info(f"Another instance is already running (mutex: {self.mutex_name})")
            else:
                AppLogger.debug(f"First instance started (mutex: {self.mutex_name})")
        except Exception as e:
            AppLogger.error(f"Error creating mutex: {e}")
            self._is_first = True  # default to allowing startup if mutex creation fails

    def is_first_instance(self) -> bool:
        """Check if this is the first instance of the application."""
        return self._is_first

    def cleanup(self) -> None:
        """Release the mutex. Call when the application exits."""
        if self.mutex:
            try:
                # pywin32 stubs mistype the handle param as int; PyHANDLE is the real runtime type.
                win32api.CloseHandle(self.mutex)  # type: ignore[arg-type]
                AppLogger.debug("Mutex released")
            except Exception as e:
                AppLogger.error(f"Error releasing mutex: {e}")
            finally:
                self.mutex = None

    def __del__(self) -> None:
        self.cleanup()
```

## Call site

```python
def main() -> None:
    single_instance = SingleInstance(APP_NAME)
    if not single_instance.is_first_instance():
        AppLogger.info("Exiting: another instance is already running")
        sys.exit(0)

    app = QApplication(sys.argv)
    ...
    app.aboutToQuit.connect(single_instance.cleanup)
```

## Rules

- **Check first.** The check is the first statement in `main()`, before `QApplication`,
  tray icons, hotkey registration or any file is opened.
- **Keep the object alive.** Hold `single_instance` in a variable that lives as long as
  the app. If it is garbage-collected, `__del__` closes the handle and the lock is gone.
- **Release on exit.** Call `cleanup()` on shutdown — `app.aboutToQuit` in PySide6, a
  `finally` block around the main loop otherwise.
- **Stable name.** Build the mutex name from the app name constant, never from the
  install path or a version, or two copies in different folders will both start.
- **Fail open.** If creating the mutex throws, log the error and start anyway. A broken
  guard must not make the app unstartable.
- **`Global\` prefix** means one instance per machine across all user sessions. Use
  `Local\` only if each logged-in user should get their own instance.

## Optional: bring the existing window to front

For apps with a visible main window, the second launch should surface the first instead
of exiting silently. Call this from `__init__` in the `already_running` branch:

```python
import win32gui

SW_RESTORE = 9


def show_existing_window(window_title: str) -> bool:
    """Restore and focus the already-running instance's main window."""
    try:
        hwnd = win32gui.FindWindow(None, window_title)
        if not hwnd:
            AppLogger.warning(f"Could not find existing window by title: {window_title}")
            return False
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        return True
    except Exception as e:
        AppLogger.error(f"Could not activate existing window: {e}")
        return False
```

`FindWindow` matches the exact window title, so keep that title in one constant shared
with the window that sets it. Skip this for tray-only apps: there is no window to raise.
