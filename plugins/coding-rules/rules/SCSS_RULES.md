# Version
1

Increase this version number whenever this rule file changes.

# SCSS/Sass Rules

See `COMMON_RULES.md` for rules that apply to all languages.
See `project_type/FRONTEND.md` for rules that apply to all frontend SPA projects.

---

## Sass Version & Module System

Use Dart Sass — the only actively maintained Sass implementation. Never use `@import`, which is
deprecated and will be removed. Use `@use` and `@forward` exclusively.

### Namespace Pattern

```scss
// _variables.scss
$color-primary: #3b82f6;
$spacing-md: 1rem;

// _mixins.scss
@use 'variables' as vars;

@mixin button-base {
  padding: vars.$spacing-md;
  background-color: vars.$color-primary;
}
```

### Forwarding

Use `@forward` in barrel files to re-export partials with a controlled public API:

```scss
// _index.scss (barrel file)
@forward 'variables';
@forward 'mixins';
```

```scss
// main.scss
@use 'index' as *;
```

---

## File Organization

Use a practical partial structure. Prefix all partials with `_` so they are not compiled independently.

```
src/scss/
├── main.scss              # Entry point — @use's all partials
├── _variables.scss        # Design tokens: colors, spacing, typography, breakpoints
├── _mixins.scss           # Reusable mixins (responsive, dark mode, etc.)
├── _reset.scss            # CSS reset / normalize
├── _base.scss             # Base element styles (body, headings, links)
├── _utilities.scss        # Utility classes (visually-hidden, clearfix, etc.)
├── components/            # Component-scoped styles
│   ├── _index.scss        # Forwards all component partials
│   ├── _button.scss
│   ├── _card.scss
│   └── _modal.scss
└── layout/                # Layout-level styles
    ├── _index.scss        # Forwards all layout partials
    ├── _header.scss
    ├── _sidebar.scss
    └── _grid.scss
```

### Entry Point

`main.scss` is the single entry point that composes all partials:

```scss
// main.scss
@use 'reset';
@use 'variables';
@use 'mixins';
@use 'base';
@use 'utilities';
@use 'components';
@use 'layout';
```

---

## Naming Conventions

### Class Names — BEM

Use Block__Element--Modifier for CSS class names:

```scss
.card { }
.card__header { }
.card__body { }
.card--featured { }
.card--featured .card__header { }
```

### Variables

Use `$category-property-variant` pattern:

```scss
$color-primary: #3b82f6;
$color-primary-light: #60a5fa;
$color-danger: #ef4444;
$font-size-sm: 0.875rem;
$font-size-base: 1rem;
$font-size-lg: 1.25rem;
$spacing-xs: 0.25rem;
$spacing-sm: 0.5rem;
$spacing-md: 1rem;
$spacing-lg: 1.5rem;
$spacing-xl: 2rem;
```

### Files

Use kebab-case for file names: `_button-group.scss`, `_nav-bar.scss`.

### Mixins & Functions

Use verb-based names for mixins and descriptive names for functions:

```scss
@mixin respond-to($breakpoint) { }
@mixin apply-dark-mode() { }
@function calculate-rem($px) { }
```

---

## Variables & Design Tokens

Centralize all design tokens in `_variables.scss`. Never hardcode color, spacing, or typography
values directly in component styles.

### Color Palette

Define a base palette with semantic aliases:

```scss
// Base palette
$gray-50: #f9fafb;
$gray-100: #f3f4f6;
$gray-900: #111827;
$blue-500: #3b82f6;
$red-500: #ef4444;
$green-500: #22c55e;

// Semantic aliases
$color-primary: $blue-500;
$color-danger: $red-500;
$color-success: $green-500;
$color-bg: $gray-50;
$color-text: $gray-900;
```

### Typography Scale

```scss
$font-family-base: system-ui, -apple-system, sans-serif;
$font-family-mono: ui-monospace, 'Courier New', monospace;

$font-size-xs: 0.75rem;
$font-size-sm: 0.875rem;
$font-size-base: 1rem;
$font-size-lg: 1.25rem;
$font-size-xl: 1.5rem;
$font-size-2xl: 2rem;

$line-height-tight: 1.25;
$line-height-base: 1.5;
$line-height-relaxed: 1.75;
```

### Breakpoint Map

```scss
$breakpoints: (
  'sm': 640px,
  'md': 768px,
  'lg': 1024px,
  'xl': 1280px,
);
```

### CSS Custom Properties for Runtime Theming

Export Sass variables as CSS custom properties when runtime switching is needed:

```scss
:root {
  --color-bg: #{$color-bg};
  --color-text: #{$color-text};
  --color-primary: #{$color-primary};
  --spacing-md: #{$spacing-md};
}
```

Use `var(--color-bg)` in component styles when the value must change at runtime (e.g., theme
switching). Use Sass variables directly when the value is fixed at build time.

---

## Nesting Rules

### Maximum 3 Levels Deep

Deep nesting creates high-specificity selectors that are hard to override and debug. Limit nesting
to 3 levels:

```scss
// Good — 2 levels
.card {
  padding: $spacing-md;

  &__header {
    font-size: $font-size-lg;
  }

  &--featured {
    border-color: $color-primary;
  }
}

// Bad — 4+ levels
.card {
  .card__header {
    .card__title {
      span {
        color: red; // too deep
      }
    }
  }
}
```

### When to Use Flat Selectors

Use flat selectors for BEM elements and modifiers instead of nesting when the block is large:

```scss
// Preferred for large blocks
.card { }
.card__header { }
.card__body { }
.card__footer { }
.card--featured { }
```

### Parent Selector (`&`)

Use `&` for BEM suffixes, pseudo-classes, and pseudo-elements — not for deeply nested descendants:

```scss
.button {
  &:hover { }
  &:focus-visible { }
  &::after { }
  &--primary { }
  &__icon { }
}
```

---

## Mixins & Functions

### When to Use Each

| Construct | Use When | Output |
|-----------|----------|--------|
| `@mixin` | Outputting CSS rules, accepting `@content` blocks | CSS declarations |
| `@function` | Computing and returning a single value | Sass value |
| `%placeholder` | Sharing identical rule sets between selectors via `@extend` | CSS (deduplicated) |

### Responsive Breakpoint Mixin

```scss
// _mixins.scss
@use 'variables' as vars;

@mixin respond-to($breakpoint) {
  $value: map-get(vars.$breakpoints, $breakpoint);
  @if $value {
    @media (min-width: $value) {
      @content;
    }
  } @else {
    @error "Unknown breakpoint: #{$breakpoint}";
  }
}
```

```scss
// Usage
.container {
  padding: $spacing-sm;

  @include respond-to('md') {
    padding: $spacing-lg;
  }
}
```

### Dark Mode Mixin

```scss
// _mixins.scss
@mixin dark-mode {
  @media (prefers-color-scheme: dark) {
    @content;
  }
}
```

```scss
// Usage
.card {
  background: var(--color-bg);
  color: var(--color-text);
}
```

### Avoid `@extend` Across Files

Only use `@extend` with placeholders defined in the same file or a directly imported partial.
Cross-file `@extend` creates unpredictable output order and bloated CSS.

---

## Dark Mode

Use OS-aware dark mode via `prefers-color-scheme`. Define theme values as CSS custom properties
and override them in the dark media query:

```scss
// _base.scss
@use 'variables' as vars;
@use 'mixins' as mix;

:root {
  --color-bg: #{vars.$color-bg};
  --color-text: #{vars.$color-text};
  --color-primary: #{vars.$color-primary};
  --color-border: #{vars.$gray-100};

  @include mix.dark-mode {
    --color-bg: #{vars.$gray-900};
    --color-text: #{vars.$gray-50};
    --color-primary: #{vars.$blue-500};
    --color-border: #{vars.$gray-900};
  }
}
```

Components then reference `var(--color-bg)` etc., and dark mode works automatically without
per-component overrides.

---

## Responsive Design

### Mobile-First

Write base styles for mobile, then add complexity at larger breakpoints using `min-width`:

```scss
.grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: $spacing-md;

  @include respond-to('md') {
    grid-template-columns: repeat(2, 1fr);
  }

  @include respond-to('lg') {
    grid-template-columns: repeat(3, 1fr);
  }
}
```

### Breakpoint Placement

Keep breakpoint overrides inside the selector they modify, not in separate media query blocks at
the bottom of the file. This keeps related styles together.

---

## Code Quality

### Stylelint

Use Stylelint with the SCSS plugin for automated linting:

```bash
npm install -D stylelint stylelint-config-standard-scss
```

### Configuration

```json
// .stylelintrc.json
{
  "extends": "stylelint-config-standard-scss",
  "rules": {
    "max-nesting-depth": 3,
    "selector-max-compound-selectors": 4,
    "scss/no-global-function-names": true,
    "no-descending-specificity": true,
    "declaration-block-no-duplicate-properties": true
  }
}
```

### package.json Script

```json
{
  "scripts": {
    "lint:scss": "stylelint 'src/**/*.scss'",
    "lint:scss:fix": "stylelint 'src/**/*.scss' --fix"
  }
}
```

---

## Integration with Build Tools

### Vite

Vite compiles SCSS natively — no plugin needed. Install Dart Sass as a dev dependency:

```bash
npm install -D sass
```

Import the entry point in your main JS/TS file or HTML:

```javascript
// main.js
import './scss/main.scss';
```

### PostCSS & Autoprefixer

Use PostCSS with Autoprefixer alongside SCSS for vendor prefixing:

```bash
npm install -D postcss autoprefixer
```

```javascript
// postcss.config.js
export default {
  plugins: {
    autoprefixer: {},
  },
};
```

When using SCSS together with Tailwind, keep Tailwind imports in a separate `app.css` and SCSS
in `src/scss/main.scss`. Both are imported in the main JS entry point.

---

## Self-Describing Classes

Implement the common "Self-Describing Classes" rule using SCSS maps to declare which fields
a component exposes for cross-cutting concerns:

```scss
// Define a component's themeable properties as a map
$card-theme-props: (
  'background': var(--color-bg),
  'border-color': var(--color-border),
  'text-color': var(--color-text),
);

// Mixin that applies all theme properties
@mixin apply-theme($props) {
  @each $prop, $value in $props {
    #{$prop}: $value;
  }
}

.card {
  @include apply-theme($card-theme-props);
}
```

This keeps the list of themed properties co-located with the component definition rather than
scattered across theme files.
