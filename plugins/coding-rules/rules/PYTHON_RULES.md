# Version
8

Increase this version number whenever this rule file changes.

# Python Rules (uv)

See `COMMON_RULES.md` for rules that apply to all languages.

## Optional rule files

- `python/WEB_TEMPLATES.md` — web templates with Jinja2 or Flask.
- `python/GUI.md` — PySide6 desktop interface.
- `python/LOCALIZATION.md` — translated content.
- `python/RELEASE.md` — release tooling.
- `python/INSTALLER.md` — Windows installer.
- `python/DATABASE.md` — SQLAlchemy database.

Run `/coding-rules:apply` to add one when the project gains it.

## Recipes

Ready-made implementations for recurring features. They are **not** copied into the
project — they live in the `coding-rules` plugin under `rules/python/recipes/`. Read the
matching recipe in full before implementing the feature, and follow it instead of
inventing a new approach.

- `python/recipes/SINGLE_INSTANCE.md` — prevent a second instance of the app from starting.

## CLI Menus

For **interactive command-line** applications, never hand-roll a menu out of `input()`
and printed option lists. Use **`pick`** — an arrow-key menu with a selection
indicator, scrolling for long lists, and optional multiselect — on its **blessed**
backend:

```bash
uv add "pick[blessed]"
```

**Always pass `backend="blessed"`.** `pick`'s default curses backend breaks on Windows
the moment the program runs a child that inherits the console — a `git` call, a build
step, anything streaming its output live. From then on curses stops translating the
arrow keys for the rest of the process: the keys still arrive, but as raw `ESC [ A`
sequences that `pick` ignores, so every later menu draws and then accepts nothing. It
looks like a hang and it is sticky — re-initialising curses does not recover it, and
neither does restoring the console mode. Only never letting the child touch the console
(capturing its output, which costs live streaming) or decoding the sequences avoids it.
blessed decodes them, so subprocesses keep the console and their live output.

### Wrap it — one menu helper per project

Never import `pick` at more than one call site. Wrap it in a single helper class
(e.g. `menu.py` / `UserChoicesHandler`) so keyboard handling, the indicator style,
and Ctrl-C behavior are defined once:

```py
# src/<pkg>/menu.py
import sys
from pick import pick


def show_menu(
    options: list[str],
    title: str,
    indicator: str = "*",
    default_index: int = 0,
) -> int:
    """Show an arrow-key menu; return the selected index. Ctrl-C exits."""
    try:
        _, index = pick(
            options=options,
            title=title,
            indicator=indicator,
            default_index=default_index,
            backend="blessed",  # never the curses default: see above
        )
        return index
    except KeyboardInterrupt:
        sys.exit(1)
```

### Keep option labels and actions in step

The menu returns an **index**, not a parsed letter. Build the label list and a parallel
list of typed action values (enum members — see "Prefer Type-Safe Values") in the same
place, so an option can never be shown without a handler:

```py
options: list[str] = []
actions: list[MenuAction] = []
options.append("Commit"); actions.append(MenuAction.COMMIT)
if repo.has_untracked:
    options.append("Add all"); actions.append(MenuAction.ADD_ALL)
options.append("Cancel"); actions.append(MenuAction.CANCEL)

action = actions[show_menu(options, title)]
```

### Testing

`pick` needs a real terminal, so tests must not call it. Patch the project's wrapper
(`show_menu`) — not `pick` itself — and assert on the option labels it was handed:

```py
monkeypatch.setattr("<pkg>.menu.show_menu", lambda options, title, **kw: 0)
```

Keep a non-interactive path for every menu (a CLI flag, or auto-select when there is a
single option) so the program stays scriptable and testable without a TTY. Have the
wrapper refuse outright when `sys.stdin`/`sys.stdout` is not a TTY: without a console the
menu blocks on a key that can never arrive, which reads as a freeze rather than an error.

Because the tests patch the wrapper, nothing in the suite ever drives a real menu — so
also keep a small manual script (`tools/menu_smoke.py` + a `.bat`) that opens a menu, runs
a subprocess inheriting the console, then opens another menu. That second menu is exactly
what the curses backend breaks, and only a human at a terminal can see it.

---

## Project Setup Scripts

Copy the setup batch files from the `python_setup_files/` folder bundled with the
coding-rules plugin (next to this rules file).

### install.bat

Initial project setup:

- Checks if `uv` is installed
- Creates virtual environment via `uv sync --all-extras`
- Runs tests to verify setup

### update.bat

Update all dependencies:

- Updates lock file with `uv lock --upgrade`
- Syncs updated dependencies
- Runs linting checks (`ruff`, `mypy`)
- Runs tests to verify compatibility

### tools/run_tests.bat

Run the test suite:

- Runs `pytest tests/ -v` with verbose output
- Shows pass/fail summary
- Projects that split unit/integration point it at `tests/unit`

### tools/run_integration_tests.bat

Run the integration test suite:

- Runs `pytest tests/integration -v`
- Same uv check + summary as run_tests.bat

### Usage

```bash
# First time setup
install.bat

# Run tests
tools\run_tests.bat

# Update dependencies
update.bat
```

---

# Essential Additional Rules (must-have)

## 1) Use `pyproject.toml` as the single source of truth

No scattered config files. Keep tooling config in `pyproject.toml` (and commit `uv.lock`).

Recommended baseline:

* Python version pinned (e.g. `>=3.11,<3.13`)
* Dependencies managed via `uv add ...`
* Lockfile committed: `uv.lock`

---

## 2) Enforce formatting + linting + type checking in CI

Minimum toolchain:

```bash
uv add --dev ruff mypy
```

Rules:

* Ruff handles lint + formatting (replace black/isort/flake8).
* MyPy (or pyright) for typing.
* CI must run: `ruff check`, `ruff format --check`, `mypy`.

---

## 3) Require type hints on public APIs

Rule of thumb:

* All public functions/classes/methods: typed parameters + return types.
* Use `typing` well: `Sequence`, `Mapping`, `Protocol`, `TypedDict`, `Literal` when helpful.
* Avoid `Any` unless you have a boundary (I/O, third-party libs).

---

## 4) Centralize configuration with environment-driven settings

No “magic values” in code. Use a single settings module with env overrides.

```py
# app/config/settings.py
from dataclasses import dataclass
import os

@dataclass(frozen=True)
class Settings:
    env: str = os.getenv("APP_ENV", "dev")
    debug: bool = os.getenv("DEBUG", "0") == "1"
    default_lang: str = os.getenv("DEFAULT_LANG", "en")
```

Everything reads from `Settings`, not directly from `os.getenv()` scattered around.

---

## 5) Tests are mandatory, fast, and isolated

Use pytest:

```bash
uv add --dev pytest
```

Rules:

* Unit tests for core logic.
* No network in unit tests.
* Use tmp dirs / fixtures; no reliance on developer machine state.
* Run tests in CI on every push.

---

## 6) Use `spec=` with MagicMock to catch interface mismatches

`MagicMock` without `spec` accepts **any** attribute, even non-existent ones:

```python
# BAD - No interface validation
mock = MagicMock()
mock.nonexistent_attribute = "test"  # Silently works
mock.typo_method()                   # Also works - won't catch bugs!
```

**Always use `spec=ClassName`** to validate against the real interface:

```python
# GOOD - Validates against real class
from unittest.mock import MagicMock
from mylib import EmailMessage

mock = MagicMock(spec=EmailMessage)
mock.nonexistent = "test"  # AttributeError - catches the bug!
```

### Common Pitfall: Mocking Methods vs Attributes

If the real class has a **method**, mock it as a method:

```python
# Real class has: def get_body(self) -> str
class EmailMessage:
    def get_body(self) -> str:
        return "content"

# WRONG - Creates fake attribute that doesn't exist
mock = MagicMock()
mock.body = "test"  # EmailMessage has no .body attribute!

# CORRECT - Mock the actual method
mock = MagicMock(spec=EmailMessage)
mock.get_body.return_value = "test"
```

### Quick Reference

```python
from unittest.mock import MagicMock, patch

# Mock with spec (recommended)
mock_obj = MagicMock(spec=RealClass)

# Mock method return value
mock_obj.method_name.return_value = "value"

# Mock method to raise exception
mock_obj.method_name.side_effect = ValueError("error")

# Mock property (use PropertyMock)
from unittest.mock import PropertyMock
type(mock_obj).prop_name = PropertyMock(return_value="value")

# Patch with spec
with patch("module.ClassName", spec=RealClass) as mock_cls:
    mock_cls.return_value.method.return_value = "value"
```

---

## 7) Required Batch Files

Every project must include these batch files:

* `start.bat` - In the root directory, starts the application
* `tools/run_tests.bat` - Runs the test suite

---

## Async Patterns

Use `asyncio` for I/O-bound tasks (network requests, file I/O, database queries). Avoid blocking
calls (`time.sleep`, synchronous HTTP) in async contexts — they block the entire event loop.

---

## Validation

Use Pydantic for request and data validation at API boundaries. Define models for incoming data
and let Pydantic handle type coercion and error reporting.

---

## Structured Logging

Use `structlog` or the `logging` module with JSON formatters — not `print()`. Configure a
centralized logging setup that all modules use consistently.

Route all logging through one class named **`AppLogger`** (`app_logger.py`) that wraps
`structlog`/`logging`. Feature code calls `AppLogger`, never `logging.getLogger(...)` or
`print()` directly — this gives a single enable/level toggle without touching call sites.

---

## Self-Describing Classes

Implement the common "Self-Describing Classes" rule using a Protocol/ABC or dataclass field
metadata.

### Option A: Protocol with abstract method

```python
from typing import Protocol


class Searchable(Protocol):
    def get_searchable_fields(self) -> list[str]: ...


class Customer:
    def __init__(self, name: str, email: str, phone: str) -> None:
        self.name = name
        self.email = email
        self.phone = phone

    def get_searchable_fields(self) -> list[str]:
        return [self.name, self.email, self.phone]
```

### Option B: Dataclass field metadata

```python
from dataclasses import dataclass, field, fields

SEARCHABLE = "searchable"


@dataclass
class Customer:
    name: str = field(metadata={SEARCHABLE: True})
    email: str = field(metadata={SEARCHABLE: True})
    internal_notes: str = field(default="", metadata={SEARCHABLE: False})


def get_searchable_values(obj: object) -> list[str]:
    return [getattr(obj, f.name) for f in fields(obj) if f.metadata.get(SEARCHABLE)]
```

Prefer the Protocol approach for simple cases. Use dataclass metadata when you need declarative
per-field control without writing boilerplate methods.
