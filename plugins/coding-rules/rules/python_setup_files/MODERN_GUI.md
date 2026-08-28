# Modern PySide6 desktop GUI

How to make a PySide6 app look like a 2020s desktop app instead of a Qt demo.
Pair with `DESIGN_RULES.md` (the language-agnostic design decisions) — this file is
only the Qt-specific *how*.

Default Qt gives you Fusion's gradient buttons, boxed tabs, a caption bar in the
user's OS accent color, and no type hierarchy. That reads as a debug tool. The fix
is four small modules and about 200 lines, applied once at startup.

---

## The module split

| Module | Owns | Why separate |
|---|---|---|
| `gui/palette.py` | Color tokens — one frozen dataclass, one instance | Every color has exactly one home; no hex literal at a call site |
| `gui/stylesheet.py` | `build(tokens) -> str`, plus the object-name constants | One sheet, applied to the `QApplication`, not N per-widget sheets that drift |
| `gui/icons.py` | Vendored SVGs, tinted and cached | Icons are artwork + a recolor rule, not layout |
| `gui/window_chrome.py` | The native title bar / frame | Platform API (DWM), not Qt — keep it quarantined behind one no-op-able call |
| `gui/labels.py` | `heading()` / `subheading()` factories | The object-name + word-wrap pairing is easy to half-apply on page 4 of 4 |

`gui/theme.py` wires them together and is the single hook point:

```python
def apply_dark(app: QApplication) -> None:
    app.setStyle("Fusion")  # the native Windows style ignores the color scheme on some builds
    app.styleHints().setColorScheme(Qt.ColorScheme.Dark)
    app.setStyleSheet(stylesheet.build(DARK))
    app.setWindowIcon(icons.app_icon())
```

---

## 1. Palette — tokens, not hex literals

```python
@dataclass(frozen=True)
class Palette:
    window: str
    surface: str
    button: str
    button_hover: str
    button_pressed: str
    text: str
    text_muted: str
    accent: str
    border: str


DARK = Palette(
    window="#181818",
    surface="#222222",
    button="#2B2B2B",
    button_hover="#343434",
    button_pressed="#3A3A3A",
    text="#F5F5F5",
    text_muted="#A0A0A0",
    accent="#20C55A",   # one accent, used sparingly
    border="#383838",
)
```

Semantic colors that mean something outside the theme (a status green that must match
another app's) belong in the same dataclass but are **not** the accent and do not
follow it when the accent changes. Document that in a comment on the field.

---

## 2. Stylesheet — one sheet, built from the tokens

```python
HEADING = "Heading"
SUBHEADING = "Subheading"
SECONDARY = "Secondary"


def build(tokens: Palette) -> str:
    return f"""
QWidget {{ background-color: {tokens.window}; color: {tokens.text}; }}
QLabel  {{ background-color: transparent; }}
QLabel#{HEADING}    {{ font-size: 24px; font-weight: 600; color: {tokens.text}; }}
QLabel#{SUBHEADING} {{ font-size: 13px; color: {tokens.text_muted}; }}

QTabWidget::pane {{ border: none; }}
QTabBar::tab {{
    background-color: transparent; color: {tokens.text_muted};
    padding: 8px 14px; border: none; border-bottom: 2px solid transparent;
}}
QTabBar::tab:selected {{ color: {tokens.accent}; border-bottom: 2px solid {tokens.accent}; }}

QPushButton, QToolButton {{
    background-color: {tokens.button}; color: {tokens.text};
    border: 1px solid {tokens.border}; border-radius: 8px; padding: 8px 12px;
}}
QPushButton:hover, QToolButton:hover     {{ background-color: {tokens.button_hover}; }}
QPushButton:pressed, QToolButton:pressed {{ background-color: {tokens.button_pressed}; }}
QPushButton:focus, QToolButton:focus     {{ border-color: {tokens.accent}; }}

QGroupBox {{
    background-color: {tokens.surface}; border: 1px solid {tokens.border};
    border-radius: 10px; margin-top: 12px; padding: 14px 12px 12px 12px;
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 4px; color: {tokens.text_muted}; }}
"""
```

**Object names are constants in this module**, never string literals at call sites:

```python
label.setObjectName(stylesheet.HEADING)   # not setObjectName("Heading")
```

A typo'd literal fails silently — the widget just stays unstyled.

### Two rules that must survive every edit

1. **No `min-width` / `min-height` anywhere in the QSS.** If the window is meant to be
   draggable to any size (pages wrapped in `QScrollArea`), a single QSS minimum puts
   the floor straight back. Pin it with a test that greps the built sheet.
2. **An explicit `:focus` border on every focusable control.** Fusion's own focus ring
   disappears the moment a button gets a custom background — and with it, any hope of
   keyboard navigation.

---

## 3. Icons — vendor them, tint them, cache them

Do **not** add an icon-font dependency for six glyphs, and do not fetch at runtime.
Copy the SVGs you actually use into `assets/icons/` with the upstream `LICENSE` and a
header naming the set and version. [Lucide](https://lucide.dev) (ISC) is a good default.

```python
_ICON_DIR = PROJECT_ROOT / "assets" / "icons"
_RENDER_SIZE_PX = 128            # 2x headroom over the largest drawn size, for HiDPI
_ICON_NAME = re.compile(r"^[a-z0-9-]+$")   # a name builds a path — keep it un-climbable
_cache: dict[tuple[str, str | None], QIcon] = {}


def icon(name: str, color: str | None = None) -> QIcon:
    if not _ICON_NAME.match(name):
        raise ValueError(f"Not an icon name: {name!r}")
    key = (name, color)
    if key not in _cache:
        _cache[key] = _load(name, color)
    return _cache[key]


def _tint(image: QImage, color: str) -> QImage:
    gray = (
        image.convertToFormat(QImage.Format.Format_ARGB32)          # un-premultiply first,
        .convertToFormat(QImage.Format.Format_Grayscale8)           # or AA edges darken
        .convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
    )
    painter = QPainter(gray)
    try:
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Multiply)
        painter.fillRect(gray.rect(), color)                        # keeps shading
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
        painter.drawImage(0, 0, image)                              # restores the alpha
    finally:
        painter.end()
    return gray
```

Three gotchas, each of which costs an hour if you meet it live:

- **Qt does not resolve `currentColor`.** Replace it in the vendored file.
- **Replace it with `#ffffff`, not black.** The tint multiplies: white × green = green,
  black × anything = black. A black-stroke icon tints to an invisible icon.
- **Cache by `(name, color)`.** One file under two colors is two icons.

Untinted (`color is None`) should return `QIcon(path)` directly so Qt's SVG engine keeps
it crisp at any size; tinting rasterizes once at `_RENDER_SIZE_PX`.

---

## 4. Native title bar (Windows)

Qt styles the client area only. The caption bar and the 1px frame belong to the window
manager and otherwise render in the user's accent color — the single biggest reason a
dark app still looks wrong.

```python
_DWMWA_USE_IMMERSIVE_DARK_MODE = 20
_DWMWA_BORDER_COLOR = 34        # without this the frame keeps the OS accent color
_DWMWA_CAPTION_COLOR = 35


def apply_dark_titlebar(widget: QWidget, tokens: Palette) -> None:
    if sys.platform != "win32":
        return
    handle = int(widget.winId())
    if not handle:
        return
    _set_attribute(handle, _DWMWA_USE_IMMERSIVE_DARK_MODE, 1)
    _set_attribute(handle, _DWMWA_CAPTION_COLOR, _colorref(tokens.window))
    _set_attribute(handle, _DWMWA_BORDER_COLOR, _colorref(tokens.border))


def _colorref(hex_color: str) -> int:
    """`#RRGGBB` -> COLORREF, which is 0x00BBGGRR — byte order reversed."""
    red, green, blue = (int(hex_color.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))
    return (blue << 16) | (green << 8) | red
```

Wrap the `ctypes` call in `try/except (AttributeError, OSError)` and no-op: a caption in
the wrong color is cosmetic, never a reason to fail to open a window.

Call it from `showEvent`, **not** from your own "reveal" helper — the window needs a
native handle, and `showEvent` is the one place that fires on the first show *and* every
re-show. It is idempotent.

---

## Qt gotchas that bite a restyle

| Symptom | Cause | Fix |
|---|---|---|
| Font size ignored | A per-widget `setFont(...)` fights the QSS `font-size` | Drop the `setFont`, keep the QSS |
| Horizontal scrollbar under a button grid | `QSizePolicy.Expanding` carries no shrink flag, so the widget's own `minimumSizeHint` is a hard floor | `QSizePolicy.Policy.Ignored` horizontally, and `setMinimumSize(QSize(0, h))` for the height |
| Item colors won't restyle | `QListWidgetItem.setForeground()` is item data, not stylesheet-reachable | Read the color from the palette module in code |
| Page background wrong inside a scroll area | The viewport is a separate widget | Style the page and viewport, or let the blanket `QWidget` rule cover both |
| One page pins the whole window's minimum size | `QTabWidget`/`QStackedWidget` report their *tallest* page's minimum as their own — even a page nobody is looking at | Wrap **every** page in `QScrollArea(setWidgetResizable(True))` |
| Enter stops working on a button | A focus/press filter that checks `isinstance(w, QPushButton)` | Check `QAbstractButton` — `QToolButton` is not a `QPushButton` |

**Icon above the label** (the tile look) needs `QToolButton` with
`setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)`; `QPushButton` can only
put the icon to the left.

---

## Verifying it — screenshots without a human

Render pages offscreen and save PNGs; it is deterministic, safe, and needs no window
focus. Fonts fall back to boxes under `offscreen`, which is fine — you are checking
geometry, color, and layout, and a real screenshot confirms the type afterwards.

```python
os.environ["QT_QPA_PLATFORM"] = "offscreen"
app = QApplication([])
apply_dark(app)
window = AppWindow()
window.resize(440, 620)
window.show()
app.processEvents()
window.grab().save("page.png")
```

The same harness measures the bugs the eye argues about:

```python
print(button.minimumSizeHint(), scroll_area.horizontalScrollBar().maximum())
```

**Never drive the real window with synthetic mouse clicks** (`SetCursorPos` +
`mouse_event`) to take screenshots. The moment the window loses focus those clicks land
in whatever app is underneath.

## Tests worth writing

```python
def test_stylesheet_never_sets_a_minimum_size() -> None:
    sheet = stylesheet.build(DARK)
    assert "min-width" not in sheet and "min-height" not in sheet


def test_every_focusable_control_has_a_focus_style() -> None:
    sheet = stylesheet.build(DARK)
    for selector in ("QPushButton:focus", "QLineEdit:focus", "QListWidget:focus"):
        assert selector in sheet


def test_tinting_recolors_the_glyph_without_losing_it(app) -> None:
    image = icons.icon("clock", DARK.accent).pixmap(64, 64).toImage()
    painted = [image.pixelColor(x, y) for x in range(image.width())
               for y in range(image.height()) if image.pixelColor(x, y).alpha() > 0]
    assert painted, "the tinted icon came out empty"
    assert any(c.green() > c.red() for c in painted), "tint did not take"
```

Use a session-scoped `QApplication` fixture in `tests/integration/conftest.py` with
`QT_QPA_PLATFORM=offscreen`, and make theme setup tolerate being applied to an
already-existing `QApplication`.

---

## Checklist

- [ ] `palette.py` holds every color; no hex literal outside it
- [ ] One application-wide stylesheet, built from the palette
- [ ] Object names are constants in `stylesheet.py`
- [ ] No `min-width`/`min-height` in the QSS, pinned by a test
- [ ] Explicit `:focus` style on every focusable control
- [ ] Icons vendored with their `LICENSE`, tinted, cached, white-stroke source
- [ ] `setWindowIcon` once on the `QApplication`
- [ ] Dark caption **and** border via DWM, from `showEvent`, no-op off Windows
- [ ] Every page wrapped in a `QScrollArea`
- [ ] Heading/subheading built by a shared factory, not repeated per page
- [ ] Offscreen render checked for each page after the change
