# Version
1

Increase this version number whenever this rule file changes.

# WordPress Theme Rules — Custom Blocks

See `WORDPRESS_RULES.md` for the general block-theme / FSE rules (structure, security, i18n, PHPCS).
This file covers the case that document defers: **when the stock block builder is not enough and you
have to build custom blocks**, and the patterns that keep a multi-block theme DRY and maintainable.

> Genericized throughout (prefix `acme`, block slug `acme/thing`). The patterns below were proven on
> a real three-block theme; use `acme` and adapt.

---

## When the block builder is not enough

Core blocks + FSE templates + `theme.json` cover most layouts. They **stop** covering it when the
design needs behaviour or structure core blocks can't express, e.g.:

- a panel that shows a **different image on mobile vs desktop** (not just a resized one), with a
  cropped `cover` photo and a gradient fill;
- a **numbered timeline that fills on scroll** (state driven by scroll position);
- a **coverflow carousel** (per-slide transform/opacity from distance to the active index).

Signal: you're stacking core blocks + custom CSS + wrestling block supports to fake one component.
**Stop and build a custom block** — one `acme/thing` block with its own markup, style, and (if
interactive) view script. Don't fork a core template for a one-off; don't ship a pile of core blocks
that only render correctly with a sheet of override CSS.

Keep using core blocks / plain headings for the parts that *are* expressible — a custom section can
sit next to a normal `core/heading` sibling; only the hard part needs to be the custom block.

---

## Custom block anatomy

```
src/thing/
  block.json     attributes + wires editorScript / style / render / (optional) viewScript
  index.js       registers the block, imports style.scss
  edit.js        the inspector (sidebar) form + a live ServerSideRender preview
  render.php     THE markup — front end AND editor preview (single source)
  style.scss     THE block CSS (its own stylesheet, not the theme's main.css)
  view.js        (optional) front-end interactivity
build/thing/     compiled output — COMMITTED, this is what WordPress loads
```

- **`render.php` is the single source of truth for markup.** The editor preview uses
  `ServerSideRender`, so it renders the *same* PHP — never keep a second copy of the layout in JS.
  (View-script interactivity does not run in the editor; a static preview is fine for a layout check.)
- Default content lives in `render.php` too: if the repeatable attribute (e.g. `steps[]`, `slides[]`)
  is empty, render a built-in default set so a freshly inserted block is never blank.

## The build step is mandatory

Custom blocks are compiled with **`@wordpress/scripts`** (`wp-scripts`): `src/` → `build/`.

| When | Do |
|------|-----|
| First checkout / after `package.json` changes | `tools/install.bat` (or `npm ci`) |
| After editing anything in `src/` (`render.php`, `edit.js`, `style.scss`, `block.json`) | `tools/build.bat` (or `npm run build`) |
| Live-rebuild while developing | `npm run start` |

`node_modules/` is gitignored; **`build/` is committed** so the server runs without Node. Editing
`src/` without rebuilding does nothing on the front end — the compiled `build/` copy is what loads.

## Theme-global styles (no plain `main.css`)

Some styling belongs to **no single block**: header/nav chrome a template part needs, the CSS behind
a registered block-style (`is-style-*`), global button/link transitions. It is tempting to drop it in
a hand-written `assets/css/main.css` — **don't.** Plain `.css` as source is banned (`SCSS_RULES.md`);
theme-global styles are SCSS-sourced and compiled just like block styles.

**`theme.json` first — keep this sheet small.** Anything a preset or a `styles.*` entry can express
does **not** go here:

| Want to style… | Put it in `theme.json`… |
|---|---|
| All links / buttons / headings | `styles.elements.{link,button,heading}` |
| A whole core block (nav color, gap, …) | `styles.blocks.core/<block>` |
| A color / spacing / font token | `settings` (palette, spacingSizes, fontSizes) |

The SCSS sheet is only for what `theme.json` **can't** express: a custom-drawn control (e.g. a
3-stripe hamburger built from `linear-gradient`s), pseudo-element decoration, a layout grid, a hover
`transform`.

**One entry, compiled by the same `wp-scripts` build:**

```
src/theme/
  index.js       one line: import './style.scss';   (entry stub — no block here)
  style.scss     THE theme-global CSS (presets only, no hardcoded hex)
build/theme/
  style-index.css   compiled + COMMITTED — this is what you enqueue
```

`wp-scripts` auto-detects build entries from **`block.json` only**, so a non-block folder like
`src/theme` is invisible to the default config. Register it with a `webpack.config.js` at the theme
root that spreads the default and adds the one entry — the `style.scss` import is then extracted to
`build/theme/style-index.css`, the same `style-index.css` naming blocks get:

```js
// webpack.config.js
const defaultConfig = require( '@wordpress/scripts/config/webpack.config' );

module.exports = {
	...defaultConfig,
	entry() {
		const entries =
			typeof defaultConfig.entry === 'function'
				? defaultConfig.entry()
				: defaultConfig.entry;
		return { ...entries, 'theme/index': './src/theme/index.js' };
	},
};
```

Enqueue the **built** file for the front end and the editor (so a registered block-style previews
identically in both) — never the `.scss`, never a hand-written `.css`:

```php
wp_enqueue_style( 'acme-main', get_theme_file_uri( 'build/theme/style-index.css' ), [], $ver );
add_editor_style( 'build/theme/style-index.css' );
```

After editing `src/theme/style.scss`, run `tools/build.bat` — same workflow as the blocks.

## Keep multiple blocks DRY

- **Shared PHP partials live OUTSIDE `src/`** (e.g. `inc/render-cta.php`, `inc/render-heading.php`),
  so the build never clobbers them. Blocks pull them in with
  `require get_theme_file_path( 'inc/render-cta.php' )` after setting a few `$acme_*` locals. One
  markup source for a component reused across blocks (a shared CTA, a shared heading).
- **Shared SCSS partials** (`src/shared/_cta.scss`, `src/shared/_breakpoints.scss`) are `@use`d by
  every block that needs them; a block adds a **scoped override** (`.acme-thing__cta { … }`) for its
  local variation without touching the shared source. One breakpoint token, one pill definition.
- **`theme.json` presets are the source of truth** for color / spacing / typography / gradients — no
  hardcoded hex in block SCSS. A value that genuinely has no preset becomes **one** documented CSS
  custom property / token, referenced by `var(--…)`, never a literal scattered across files.

## Interactivity (`view.js`)

- Enqueue it only when the block is on the page — declare `"viewScript"` in `block.json`; WordPress
  loads it per-block, no manual `wp_enqueue_script`.
- **CSS custom properties are the SCSS ↔ JS hand-off.** `view.js` reads `--acme-*` props set in the
  SCSS at layout time (diameter, spread, stage height…), so the look and the desktop/mobile
  difference are tuned **entirely in SCSS** — no JS edit to retune appearance. JS owns position/state;
  SCSS owns everything visual.
- Respect `prefers-reduced-motion` for genuine motion. (A pure colour crossfade is not vestibular
  motion and needs no special-case — don't over-guard.)
- **No carousel/animation library** until a hand-rolled script outgrows ~90 lines; then swap one in.

## Registration

```php
// functions.php
function acme_register_blocks() {
	register_block_type( get_theme_file_path( 'build/hero' ) );
	register_block_type( get_theme_file_path( 'build/thing' ) );
}
add_action( 'init', 'acme_register_blocks' );
```

`block.json` handles the editor script + its dependencies (from `index.asset.php`), the stylesheet,
the view script, and the render callback — no manual `wp_enqueue_*`. Register a custom inserter
category with a `block_categories_all` filter so the theme's blocks group together.

## ⚠️ The pattern-seed gotcha

Custom blocks are typically **seeded into a page** via a block pattern (`patterns/thing.php` →
`patterns/front-page-content.php`, run from an activation hook). Seeding is **idempotent** — it runs
only on a **fresh activation** when the target page doesn't exist yet.

- **Fresh site:** editing the pattern file (default heading/copy/steps) changes what gets seeded.
- **Existing site:** the page already holds a **saved copy** of the block — editing the pattern file
  does **nothing**. Change it in the **page editor** (edit the block's fields, or delete it and
  re-insert the block from the inserter).

Rule of thumb:

| Change | Where |
|--------|-------|
| Markup / default copy (fresh installs only) | the `patterns/*.php` file |
| Styling / layout | `src/thing/style.scss` + rebuild |
| This page's actual content | the block fields in the page editor |
