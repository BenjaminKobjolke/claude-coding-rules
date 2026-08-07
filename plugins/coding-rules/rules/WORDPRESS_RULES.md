# Version
1

Increase this version number whenever this rule file changes.

# WordPress Rules

See `COMMON_RULES.md` for rules that apply to all languages.
See `PHP_RULES.md` for general PHP rules — this file only covers WordPress-specific idioms and does not restate them.
See `WORDPRESS_THEMES.md` for building **custom blocks** when core blocks / FSE templates can't produce the design — block anatomy, the `@wordpress/scripts` build workflow, shared partials, and the pattern-seed gotcha.

These rules cover **block themes (FSE)** and **plugins**. Classic `functions.php`-driven themes are out of scope.

---

## WordPress & PHP Version

Target the current stable WordPress release. Declare the PHP requirement in the theme header (`style.css`) or plugin header:

```
Requires at least: 6.7
Requires PHP: 8.2
```

For the PHP language version itself and `composer.json`, follow `PHP_RULES.md` — do not pin a different version here.

---

## Block Theme (FSE) Structure

Start every block theme from the scaffold in [`wordpress_setup_files/block_theme/`](wordpress_setup_files/block_theme/). Copy it into the project and replace the placeholders:

```
block_theme/
├── style.css          # theme header — Theme Name, Text Domain, Requires PHP, Version
├── theme.json         # FSE settings (version 3), layout, typography, templateParts
├── templates/         # full-page templates (index.html, single.html, ...)
├── parts/             # reusable template parts (header.html, footer.html)
├── readme.txt
└── screenshot.png
```

Rules:

- **`theme.json` is the source of truth** for colors, spacing, typography, and layout. Never hardcode these in CSS when a `theme.json` setting or preset covers them.
- `theme.json` uses `"version": 3` and the matching `$schema`.
- Text Domain in `style.css` **must** equal the theme folder slug.
- Genericize before committing a starter: no real project's `Theme Name` / `Text Domain` baked in.

When the design outruns core blocks and FSE templates, build a **custom block** instead of forcing core blocks — see `WORDPRESS_THEMES.md`.

---

## Plugin Structure

Main plugin file carries the header and an `ABSPATH` guard; logic lives in a single namespaced entry class, not in the global scope:

```php
<?php
/**
 * Plugin Name: {{Plugin Name}}
 * Requires PHP: 8.2
 * Text Domain: {{plugin-slug}}
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit; // No direct file access.
}

require_once __DIR__ . '/vendor/autoload.php';

\MyVendor\MyPlugin\Plugin::instance()->boot();
```

- Every plugin file that could be reached directly starts with the `ABSPATH` guard.
- Register `register_activation_hook` / `register_deactivation_hook`; put irreversible teardown in `uninstall.php`.
- Follow the file/class layout and 300-line limit from `COMMON_RULES.md`.

---

## Hooks Over Overrides

Extend WordPress through **actions and filters** — never edit core, and never copy a core template just to change one line when a hook exists.

Prefix **every** global symbol (functions, classes, hooks, options, meta keys, script/style handles) with a project slug to avoid collisions:

```php
// Anti-pattern — unprefixed globals collide with other plugins/themes
add_action( 'init', 'register_types' );
function register_types() { /* ... */ }

// Correct
add_action( 'init', 'acme_shop_register_types' );
function acme_shop_register_types() { /* ... */ }
```

Namespaced classes count as prefixed; plain functions and string handles do not.

---

## Enqueue Assets — Never Hardcode Tags

Load scripts and styles through the enqueue API with a resolved URL and a version, so cache-busting and dependency order are handled by WordPress. No `<script>` / `<link>` tags in templates.

```php
// Theme — enqueue the COMPILED stylesheet, not a hand-written .css.
add_action( 'wp_enqueue_scripts', function () {
    wp_enqueue_style(
        'acme-main',
        get_theme_file_uri( 'build/theme/style-index.css' ),
        [],
        wp_get_theme()->get( 'Version' )
    );
} );

// Plugin
wp_enqueue_script(
    'acme-shop',
    plugins_url( 'assets/js/shop.js', __FILE__ ),
    [ 'wp-element' ],
    '1.0.0',
    true // in footer
);
```

Never build asset URLs by string-concatenating `get_stylesheet_directory_uri()` with a hand-written path when the helpers above resolve it.

**No hand-written `assets/css/main.css`.** Theme-global CSS (the chrome no single block owns — header/nav bits a template part needs, a registered block-style's rules, global button/link transitions) is **SCSS-sourced and compiled**, exactly like block styles. Plain `.css` as source is banned (see `SCSS_RULES.md`). Author it once in `src/theme/style.scss`, compile it through `@wordpress/scripts`, and enqueue the built `build/theme/style-index.css` (front end **and** `add_editor_style`). The build wiring — and the `theme.json`-first rule that keeps this sheet minimal — is in `WORDPRESS_THEMES.md` § *Theme-global styles*.

---

## Security Baseline

WordPress application of the **Security Baseline** rule in `COMMON_RULES.md`. All three apply on every request path that touches user data.

**Escape on output** (choose the context-correct function):

```php
echo esc_html( $title );
echo '<a href="' . esc_url( $link ) . '">';
printf( '<input value="%s">', esc_attr( $value ) );
echo wp_kses_post( $rich_html );
```

**Sanitize on input:**

```php
$name  = sanitize_text_field( wp_unslash( $_POST['name'] ?? '' ) );
$email = sanitize_email( wp_unslash( $_POST['email'] ?? '' ) );
```

**Nonce + capability on every state change:**

```php
// Form
wp_nonce_field( 'acme_save_settings', 'acme_nonce' );

// Handler
if ( ! current_user_can( 'manage_options' ) ) {
    wp_die( esc_html__( 'Insufficient permissions.', 'acme' ) );
}
check_admin_referer( 'acme_save_settings', 'acme_nonce' );
```

Escaping is not sanitizing: sanitize when data comes **in**, escape when it goes **out** — even data you sanitized earlier.

---

## Database

WordPress application of PHP's **No Raw SQL** rule.

- Prefer WordPress data APIs — `WP_Query`, `get_posts`, the options API (`get_option`/`update_option`), and post/user meta — over direct SQL.
- When `$wpdb` is unavoidable, **always** `$wpdb->prepare()`. Never interpolate variables into the query string.

```php
// Anti-pattern — SQL injection
$wpdb->query( "DELETE FROM {$wpdb->prefix}acme WHERE id = $id" );

// Correct
$wpdb->query(
    $wpdb->prepare( "DELETE FROM {$wpdb->prefix}acme WHERE id = %d", $id )
);
```

Table name (`$wpdb->prefix . 'acme'`) is interpolated; **values** are always `%d`/`%s`/`%f` placeholders.

---

## Localization

WordPress-native equivalent of the localization section in `PHP_RULES.md` — use WP i18n, not `php-localization`.

- Text domain equals the theme/plugin slug and is a **string literal** at every call site (the `.pot` scanner cannot read variables or constants).
- Wrap every user-facing string; combine with escaping on output.

```php
__( 'Save', 'acme' );                 // return
esc_html__( 'Save', 'acme' );         // return, escaped for HTML
esc_attr_e( 'Search', 'acme' );       // echo, escaped for attribute
/* translators: %s = user name */
printf( esc_html__( 'Hello, %s', 'acme' ), esc_html( $name ) );
```

Load the domain and ship a `languages/` folder with a `.pot` template:

```php
add_action( 'after_setup_theme', fn() => load_theme_textdomain( 'acme', get_template_directory() . '/languages' ) );
// Plugins: load_plugin_textdomain( 'acme', false, dirname( plugin_basename( __FILE__ ) ) . '/languages' );
```

---

## Logging

Reuse the single `Logger` convention from the **Centralized Logger** table in `COMMON_RULES.md` (`src/Logger.php`, thin PSR-3 wrapper). Feature code never calls `error_log`, `var_dump`, or `print_r` directly — one class, one off switch.

---

## Code Quality — WordPress Coding Standards

PHPCS + WPCS is **required** on every WordPress project — it is the lint that enforces every rule above (escaping, i18n literals, prefixing, array/spacing style). Not optional.

**Install** — run in the theme/plugin root that holds (or will hold) `composer.json`:

```
REM 1. Pre-allow the plugin FIRST. dealerdirect/phpcodesniffer-composer-installer is a
REM    Composer plugin; a plain `composer require` throws an interactive allow-plugins
REM    prompt that hangs non-interactive shells (CI, agents, this tool).
composer config --no-plugins allow-plugins.dealerdirect/phpcodesniffer-composer-installer true

REM 2. Install the standards as dev deps.
composer require --dev squizlabs/php_codesniffer wp-coding-standards/wpcs phpcompatibility/phpcompatibility-wp dealerdirect/phpcodesniffer-composer-installer
```

The installer plugin auto-registers the `WordPress` standard with PHPCS — no manual `installed_paths` step. `vendor/` is gitignored; `composer.json` + `composer.lock` are committed.

Runners and the `phpcs.xml` template live in [`wordpress_setup_files/tools/`](wordpress_setup_files/tools/) — copy them into the project's `tools/` folder and follow that folder's `README.md`.

```
tools\phpcs.bat  [path]   REM report violations (no arg = scan per phpcs.xml)
tools\phpcbf.bat [path]   REM auto-fix what is fixable
```

**When to use** — after **every feature / bugfix**, lint the changed files (`tools\phpcs.bat path\to\file.php`), auto-fix the mechanical findings with `tools\phpcbf.bat`, and lint again until clean **before commit**. This is part of the `verify:after-change` step, not a separate pass.

---

## Required Batch Files

Per the **Reusable Tooling** and **Test Runner Scripts** rules in `COMMON_RULES.md`, every WordPress project includes:

- `tools/run_tests.bat` — runs the test suite.
- `tools/phpcs.bat` — WordPress Coding Standards lint.
