# Version
1

Increase this version number whenever this rule file changes.

# Design Rules (All Languages)

See `COMMON_RULES.md` for rules that apply to all languages. These rules apply to
anything with a user interface — desktop app, web frontend, mobile app, CLI TUI.

They are about **decisions**, not about a framework. The per-stack implementation
guides are:

- `python_setup_files/MODERN_GUI.md` — PySide6 desktop apps
- `project_type/FRONTEND.md` — web SPAs (Vite, Tailwind, dark mode)

Default UI toolkits ship a *safe* look, not a good one: gradient buttons, boxed tabs,
every control the same size, no hierarchy. An interface built from defaults reads as a
debug tool no matter how good the code behind it is.

---

## Tokens, Not Values

Every color, spacing step, radius, and font size is a **named token defined once**.
Call sites reference the token; nothing hardcodes `#2B2B2B` or `13px`.

- **Anti-pattern.** A hex color appears on four screens. Changing the theme means
  finding all four, and the one you miss is the one the user sees.
- **Correct pattern.** One palette/theme module (a frozen dataclass, a CSS custom
  property block, a `ThemeData`) that every screen reads.
- This is "String Constants" and DRY applied to design. The moment a value appears
  twice, it is a token.

---

## One Accent Color

Pick **one** accent and use it only for: the selected navigation item, the focus ring,
the primary action, and progress. Everything else is a neutral.

- An interface where the accent frames the window, fills the title bar, and outlines
  every button has no accent — it has a background color.
- Semantic colors (success green, error red) are separate tokens and do **not** follow
  the accent. If a status color must match another app or a spec, comment the field
  saying so, so a theme change does not silently redefine it.
- Never encode information in color alone — pair it with a glyph, a label, or a
  position (colorblind users, grayscale printing, low-quality projectors).

---

## Neutral Ramp Before Color

A dark theme needs at least: window background, an elevated surface, a control fill,
its hover and pressed states, a border, primary text, and muted text. Most of a good
interface is that ramp; color is the exception on top of it.

Body text on the background must clear **4.5:1** contrast (3:1 for large text and for
UI borders that carry meaning). Muted text is muted, not unreadable — check it, don't
eyeball it.

---

## Hierarchy Is Type and Space, Not Boxes

Three levels are usually enough: a page heading, a muted one-line explanation, and body
or control text. Give each a token (size + weight), and build them with a **shared
factory** (`heading()` / `subheading()`), never by repeating the styling on each screen.

- Separate groups with whitespace before you separate them with a border, and with a
  border before you separate them with a filled box.
- A screen that is all boxes has no hierarchy — everything is equally important, which
  means nothing is.
- Use a consistent spacing scale (4/8/12/16/24…) rather than whatever number closed the
  gap on that one screen.

---

## Size Controls by Importance

Controls should not all be the same size, and the primary action should not be the same
weight as its neighbors. A grid of six identical giant buttons is as flat as a grid of
six identical tiny ones.

- Primary action: filled, accent.
- Secondary: outlined or flat with accent text.
- Rare actions (a custom value, an advanced group): folded away behind a toggle or a
  collapsed section — present, not prominent.

---

## Every Focusable Control Has a Visible Focus State

The moment you give a control a custom background, the toolkit's own focus ring
disappears. Re-add it explicitly, in the accent, on **every** focusable control —
buttons, fields, lists, tabs.

Keyboard users, accessibility tooling, and your own automated tests all navigate by
focus. This is not decoration; a UI with an invisible focus ring is unusable without a
mouse. Tab through the entire interface once before calling a restyle done.

---

## Never Set a Minimum Size to Fix a Layout

If content is too tall or too wide, make it **scroll or wrap** — do not pin the window.
A minimum size set to fix one screen becomes a floor every other screen inherits,
including screens the user is not looking at (tab and stack containers report their
largest child's minimum as their own).

- Wrap every page/route in a scrolling container.
- Word-wrap explanatory text; an unwrapped sentence sets the width floor.
- Then pin it with a test: assert the window resizes to something tiny, and assert the
  stylesheet contains no minimum-size rule.

---

## Own the Window Chrome

On desktop, the title bar and window frame belong to the OS and default to the user's
system accent color. A carefully themed dark app with a bright green caption bar looks
broken. Set the caption and border explicitly, and make the call a **silent no-op** on
platforms and OS versions that do not support it.

---

## Icons: Vendor a Subset, Recolor in Code

- Vendor the SVGs you actually use into the repo, with the upstream `LICENSE` and a
  header naming the set and version. Never fetch icon assets at runtime, and never add
  a whole icon-font dependency for six glyphs.
- Recolor from a palette token in code rather than committing one file per color.
- Cache by `(name, color)`.
- Keep icon sizes on the same scale as the type — an icon that is not aligned to the
  text baseline or optical center reads as a mistake.

---

## Design the Empty, Loading, and Error States

Every list has a first run. Every request fails sometimes. A screen designed only for
the happy path ships a blank rectangle to every new user.

- **Empty**: say what would be here and how to get one.
- **Loading**: keep the layout stable — never let content jump when it arrives.
- **Error**: say what failed and what to do next, in the interface, not only in a log.
- **Validation**: show it where the input is, not in a dialog. If the user can see the
  field, tell them there instead of silently falling back to a default.

---

## Follow the Platform, Then Be Consistent

Match the platform's conventions for window controls, menus, shortcuts, and dialogs
before inventing your own. Inside your app, be *ruthlessly* consistent: the same action
looks the same everywhere, the same spacing separates the same kinds of things, the
same word means the same thing on every screen.

If two of your own screens disagree, the screens are wrong — not the user.

---

## Localize From the Start

Every user-visible string goes through the translation layer with a key constant, never
a raw string at a call site. Layouts must survive a translation that is 40% longer:
wrap text, avoid fixed-width labels, and never build a sentence by concatenating
fragments — translate the whole sentence with placeholders.

---

## Verify Visually, and Automate It

A restyle is not done because the tests pass — tests do not look at the screen.

- Render each screen to an image (offscreen/headless is fine and deterministic) and
  actually look at all of them after a change.
- Check the app at its smallest supported size, not just the size it opens at.
- Automate what an image cannot assert: no minimum-size rule in the theme, a focus style
  on every control, a recolored icon that still has pixels.
- Never drive a real window with synthetic mouse clicks to capture screenshots — the
  moment focus moves, those clicks land in someone else's application.

---

## Checklist

- [ ] One token module; no color, size, or radius literal at a call site
- [ ] One accent, used for selection/focus/primary only
- [ ] Body text ≥ 4.5:1 contrast; information never carried by color alone
- [ ] Heading / subheading / body built by a shared factory
- [ ] Consistent spacing scale; whitespace before borders before boxes
- [ ] Visible focus state on every focusable control, verified by tabbing through
- [ ] Nothing sets a minimum size; content scrolls and wraps instead
- [ ] Window chrome themed, with a no-op fallback
- [ ] Icons vendored with license, recolored from tokens, cached
- [ ] Empty / loading / error / validation states designed
- [ ] All strings localized via key constants; layout survives longer translations
- [ ] Every screen rendered and looked at after the change
