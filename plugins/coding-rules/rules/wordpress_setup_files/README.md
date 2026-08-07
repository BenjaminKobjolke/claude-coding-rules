# WordPress Setup Files

Copy-in templates for WordPress projects (block themes + plugins). See [`../WORDPRESS_RULES.md`](../WORDPRESS_RULES.md) for the rules these support.

## Block theme starter

`block_theme/` is a genericized FSE (block) theme scaffold. To start a theme:

1. Copy `block_theme/` into `wp-content/themes/your-theme/`.
2. In `style.css`, replace `{{THEME_NAME}}` and `{{textdomain}}`, set `Version`, and set `Requires PHP` to match the project.
3. Rename `readme.txt`'s placeholders and replace `screenshot.png`.
4. Keep the text domain identical to the theme folder slug.

## Tooling

Copy `tools/*` into the project's `tools/` folder, then:

1. Install dev deps:
   ```
   REM Pre-allow the plugin FIRST — else composer throws an interactive allow-plugins
   REM prompt that hangs non-interactive shells (CI, agents).
   composer config --no-plugins allow-plugins.dealerdirect/phpcodesniffer-composer-installer true

   composer require --dev squizlabs/php_codesniffer wp-coding-standards/wpcs phpcompatibility/phpcompatibility-wp dealerdirect/phpcodesniffer-composer-installer phpunit/phpunit
   ```
   (`dealerdirect/phpcodesniffer-composer-installer` auto-registers the WPCS + PHPCompatibilityWP standards with PHPCS — no manual `installed_paths` step. Confirm current package names before running; some may have moved to the `phpcsstandards/*` vendor.)
2. Edit `tools/phpcs.xml` — set the scan `<file>` path(s), the `text_domain` and `prefixes` (replace `acme`), and `testVersion` to match `Requires PHP`.
3. For plugin/integration tests, install the WordPress test suite (see the run_tests.bat header).

## What's included

| File | Purpose |
|---|---|
| `block_theme/` | Genericized FSE block-theme starter (`theme.json` v3, `templates/`, `parts/`, `style.css`). |
| `tools/phpcs.xml` | PHPCS ruleset — WordPress standard + WP I18n + PrefixAllGlobals + PHPCompatibilityWP. Edit per project. |
| `tools/phpcs.bat` | PHPCS runner (report violations). |
| `tools/phpcbf.bat` | PHPCBF runner (auto-fix fixable violations). |
| `tools/run_tests.bat` | PHPUnit runner (composer-installed). |
