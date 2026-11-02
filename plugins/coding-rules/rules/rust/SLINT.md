# Version
1

Increase this version number whenever this rule file changes.

# Slint Desktop UI Rules (Rust)

See `RUST_RULES.md` for Rust conventions and `DESIGN_RULES.md` for visual and interaction design.
These rules apply to Rust desktop applications built with Slint.

---

## Project Structure

- Keep `.slint` components in a `ui/` directory owned by the UI crate.
- Compile the UI with `slint-build` from that crate's `build.rs`.
- Keep each component in its own `.slint` file and each file within 300 lines. Generated Rust
  modules are exempt from the source-file limit.

---

## Design Tokens

- Define shared colors, spacing, typography, and other design tokens in one Slint `global Theme`
  or `Palette` component in its own file.
- Components consume these tokens instead of hard-coding colors, dimensions, or repeated style
  values. Follow DESIGN_RULES.md's “Tokens, Not Values” guidance.

---

## Keep UI and Application Logic Separate

- Use `.slint` for layout, property bindings, and forwarding user callbacks. Put application and
  business logic in Rust.
- Connect Rust to generated globals and callbacks from one UI wiring module. Do not scatter
  `ui.set_*` calls across unrelated application code.
- Represent changing collections with Slint models such as `VecModel` or `ModelRc` rather than
  copying row data into individual UI properties.
- Run long work away from the UI thread. Send results back with APIs such as
  `slint::invoke_from_event_loop` or `Weak::upgrade_in_event_loop`, and handle a UI that has closed.
- Use `@tr()` for user-visible strings when the project supports localization.

---

## Build Time and Visual Checks

- Slint generates a large Rust module. If that generated code dominates development builds, lower
  optimization for the UI crate only in a development profile; keep release settings appropriate
  for shipping.
- Check visual changes with the screenshot approach in `DESIGN_RULES.md`, using the project's
  offscreen capture or real-window screenshot tool when available.
