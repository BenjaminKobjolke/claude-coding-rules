# Version
1

Increase this version number whenever this rule file changes.

# Python Localization

Applies on top of `PYTHON_RULES.md` when the project has translations.

## Localization

Use the `python-localization` library for multi-language support:
https://github.com/BenjaminKobjolke/python-localization

### Installation (uv)

#### Option A (recommended): Add as dependency to the project

```bash
uv add "git+https://github.com/BenjaminKobjolke/python-localization.git"
```

#### Option B: Install into the current environment (without adding to project deps)

```bash
uv pip install "git+https://github.com/BenjaminKobjolke/python-localization.git"
```

### Directory Structure

```
project/
├── lang/
│   ├── en.json    # English (default)
│   ├── de.json    # German
│   └── fr.json    # French
├── app/
└── templates/
```

### Translation File Format

Create `lang/en.json` with nested structure:

```json
{
  "nav": {
    "dashboard": "Dashboard",
    "settings": "Settings",
    "logout": "Logout"
  },
  "auth": {
    "login_title": "Login",
    "signin_subtitle": "Sign in to access your dashboard",
    "error": {
      "auth_failed": "Authentication failed. Please try again.",
      "rate_limited": "Too many attempts. Please try again later."
    }
  },
  "flash": {
    "success": {
      "saved": "Changes saved successfully.",
      "deleted": "Item deleted successfully."
    },
    "error": {
      "not_found": "Item not found.",
      "invalid_id": "Invalid ID."
    }
  },
  "common": {
    "cancel": "Cancel",
    "save": "Save",
    "delete": "Delete",
    "edit": "Edit"
  }
}
```

### Python Setup

#### Container Integration

Add a method to your DI container:

```py
# app/container.py
from pathlib import Path

# Adjust import to the real package name of your library
# from python_localization import Localization

class Container:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self._localization = None

    def get_localization(self):
        if self._localization is None:
            self._localization = Localization(
                driver="json",
                lang_dir=str(self.base_dir / "lang"),
                default_lang="en",
                fallback_lang="en",
            )
        return self._localization
```

#### Controller Helper

Add translation helper to your base controller:

```py
# app/web/base_controller.py
class BaseController:
    def __init__(self, container):
        self.container = container

    def get_localization(self):
        return self.container.get_localization()

    def t(self, key: str, params: dict[str, object] | None = None) -> str:
        return self.get_localization().t(key, params or {})
        # or .translate(...) / .lang(...), depending on your library
```

Usage in controllers:

```py
from app.i18n.keys import TK

# Simple translation
self.add_flash("success", self.t(TK.FLASH_SUCCESS_SAVED))

# With placeholders
self.add_flash("info", self.t("messages.welcome", {":name": user.name}))
```

---

## Jinja2 Integration

### Add the `t()` Function

Where you configure Jinja2:

```py
# app/web/templates.py
from jinja2 import Environment, FileSystemLoader
from app.i18n.keys import TK

def create_env(localization, templates_dir: str) -> Environment:
    env = Environment(loader=FileSystemLoader(templates_dir), autoescape=True)

    def t(key: str, params: dict[str, object] | None = None) -> str:
        return localization.t(key, params or {})

    env.globals["t"] = t
    env.globals["TK"] = TK
    return env
```

### Usage in Templates

Simple translations:

```html
<h1>{{ t(TK.NAV_DASHBOARD) }}</h1>
<button>{{ t(TK.COMMON_SAVE) }}</button>
<a href="/logout">{{ t(TK.NAV_LOGOUT) }}</a>
```

With placeholders (define in JSON as `:placeholder`):

```json
{
  "messages": {
    "welcome": "Hello, :name!",
    "items_count": "You have :count items"
  }
}
```

```html
<p>{{ t("messages.welcome", {":name": user.name}) }}</p>
<p>{{ t("messages.items_count", {":count": items|length}) }}</p>
```

Conditional content:

```html
{% if error == "auth_failed" %}
  {{ t("auth.error.auth_failed") }}
{% elif error == "rate_limited" %}
  {{ t("auth.error.rate_limited") }}
{% endif %}
```

In attributes:

```html
<a href="/back" title="{{ t('common.back') }}">
  <i class="icon-back"></i>
</a>

<button onclick="return confirm('{{ t('confirm.delete') }}')">
  {{ t('common.delete') }}
</button>
```

---

## Translation Key Naming Convention

Use dot notation with logical grouping:

```
section.subsection.key

nav.dashboard            - Navigation items
auth.login_title         - Authentication related
flash.success.saved      - Flash messages by type
flash.error.not_found
form.label.name          - Form labels
form.placeholder.email   - Form placeholders
form.validation.required - Validation messages
common.save              - Reusable UI elements
errors.404.title         - Error pages
```

---

## Translation Keys as Constants

Using raw strings like `t("nav.dashboard")` is error-prone. Create a `TK` class with all keys as constants for IDE autocomplete and refactoring safety.

Create `app/i18n/keys.py`:

```py
# app/i18n/keys.py
class TK:
    # Navigation
    NAV_DASHBOARD = "nav.dashboard"
    NAV_SETTINGS = "nav.settings"
    NAV_LOGOUT = "nav.logout"

    # Auth
    AUTH_LOGIN_TITLE = "auth.login_title"
    AUTH_ERROR_AUTH_FAILED = "auth.error.auth_failed"

    # Flash messages
    FLASH_SUCCESS_SAVED = "flash.success.saved"
    FLASH_ERROR_NOT_FOUND = "flash.error.not_found"

    # Common
    COMMON_CANCEL = "common.cancel"
    COMMON_SAVE = "common.save"
```

Usage in controllers:

```py
from app.i18n.keys import TK
self.add_flash("success", self.t(TK.FLASH_SUCCESS_SAVED))
```

Usage in templates:

```html
{{ t(TK.NAV_DASHBOARD) }}
```

### Benefits

* IDE autocomplete for all translation keys
* Refactoring support
* Easy to find all usages of a key
* Fewer typos / runtime missing-key bugs

---

## Adding New Languages

1. Copy `lang/en.json` to `lang/de.json`
2. Translate all values (keep keys identical)
3. Change language in configuration:

```py
self._localization = Localization(
    driver="json",
    lang_dir=str(self.base_dir / "lang"),
    default_lang="de",
    fallback_lang="en",
)
```

---
