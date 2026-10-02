# Version
1

Increase this version number whenever this rule file changes.

# Python Desktop GUI (PySide6)

Applies on top of `PYTHON_RULES.md` when the project has a PySide6 desktop interface.

## GUI Framework

For **desktop GUI** applications use **PySide6** (Qt for Python). Always install the
latest version — do not pin an old one:

```bash
uv add pyside6
```

This is separate from the web template engine in `python/WEB_TEMPLATES.md`: Jinja2 renders web HTML,
PySide6 builds native desktop windows. Pick by app type.

### Make it look modern

Default Qt reads as a debug tool: gradient buttons, boxed tabs, a caption bar in the
user's OS accent color, no type hierarchy. Follow
[`python_setup_files/MODERN_GUI.md`](python_setup_files/MODERN_GUI.md) — the palette /
stylesheet / icons / window-chrome module split, the vendored-and-tinted icon recipe,
the Qt gotchas that break a restyle (size policies, per-widget fonts, minimum-size
floors, focus rings), and how to screenshot pages offscreen to verify it.

The design decisions behind it — tokens, one accent, hierarchy, focus states, empty and
error states — are language-independent and live in `DESIGN_RULES.md`.

---
