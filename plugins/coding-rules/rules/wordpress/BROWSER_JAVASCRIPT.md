# Version
2

Increase this version number whenever this rule file changes.

# WordPress Browser JavaScript Rules

## Scope

These rules cover hand-written JavaScript that WordPress themes (classic or block) and plugins load in the browser, on the front end or in wp-admin. Pair this file with `COMMON_RULES.md`, `WORDPRESS_RULES.md`, and `PHP_RULES.md`. Do not apply `JAVASCRIPT_RULES.md`; it covers Bun and Node command-line applications.

Block editor scripts and block `view.js` files built with `@wordpress/scripts` follow `WORDPRESS_THEMES.md` for their build and block conventions. The rules below still apply to their JavaScript code.

## Files and Loading

- Keep one script file per feature under the theme or plugin's `assets/js/`; admin scripts may live under `admin/assets/js/`.
- Use kebab-case names matching the WordPress script handle: `acme-listing.js` is registered with the `acme-listing` handle.
- Load scripts only through `wp_register_script()` and `wp_enqueue_script()`. Declare every dependency (`jquery`, `wp-i18n`, `wp-api-fetch`, and so on), set a version for cache invalidation, and load in the footer or defer execution. On WordPress 6.3 and later, use the `strategy` argument when appropriate.
- Enqueue a script only on pages that need it. Use front-end conditional tags and, in admin, `$hook_suffix` to scope it.
- Never add `<script>` tags or inline JavaScript to templates. Follow `WORDPRESS_RULES.md` → “Enqueue Assets”.

## No Build by Default

Write classic scripts that browsers can run as committed. Do not add npm dependencies or a bundler unless the project already has an `@wordpress/scripts` build.

Commit third-party libraries as released, in their own folder. Keep `*.min.js` vendor files unchanged and exclude them from DRY checks, linting, and code analysis.

## Scope and Globals

Wrap each file in an IIFE or a jQuery ready callback and use strict mode. Do not create implicit globals:

```js
(function ($) {
  'use strict';

  // Feature code stays inside this scope.
})(jQuery);
```

Code shared by files belongs on one project-prefixed namespace object, initialized in a registered shared handle:

```js
window.acme = window.acme || {};
```

Scripts that use that shared object must declare the shared handle as a dependency.

## Data from PHP

Pass server values such as request URLs, nonces, settings, and user-facing strings with `wp_localize_script()` or `wp_add_inline_script()`. Use one project-prefixed object per handle, such as `acmeListing`. Never hardcode a site URL or echo PHP into a `.js` file.

Read the localized object once at the top of the file through a `normalizeXxx()` boundary function. Coerce each value explicitly and provide a safe default:

```js
function normalizeListingConfig(value) {
  const config = value && typeof value === 'object' ? value : {};

  return {
    ajaxUrl: typeof config.ajaxUrl === 'string' ? config.ajaxUrl : '',
    nonce: typeof config.nonce === 'string' ? config.nonce : '',
    loadError: typeof config.loadError === 'string' ? config.loadError : ''
  };
}

const CONFIG = normalizeListingConfig(window.acmeListing);
```

## AJAX and REST Requests

Use `admin-ajax.php` with an `action` and nonce, or the REST API through `wp.apiFetch` or `fetch` with an `X-WP-Nonce`. Server-side nonce, capability, and sanitization checks remain in PHP as required by `WORDPRESS_RULES.md` → “Security Baseline”.

Every request must handle failure: show an error state, restore disabled controls, and never swallow an error with an empty `catch` or `.fail()`. User-facing error text must come from the localized config or a WordPress translation such as `wp.i18n.__()`; an empty normalization fallback must not be displayed. Guard controls against double submission while a request is pending.

```js
const SELECTOR = Object.freeze({ form: '[data-acme-listing-form]' });

$(document).on('submit.acme', SELECTOR.form, function (event) {
  event.preventDefault();

  const $form = $(this);
  const $submit = $form.find('[type="submit"]');
  if ($submit.prop('disabled')) return;

  $submit.prop('disabled', true);
  fetch(CONFIG.ajaxUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8' },
    body: new URLSearchParams({ action: 'acme_load_listings', nonce: CONFIG.nonce })
  })
    .then((response) => {
      if (!response.ok) throw new Error('Request failed.');
      return response.json();
    })
    .then(renderListings)
    .catch(() => showListingError(CONFIG.loadError))
    .finally(() => $submit.prop('disabled', false));
});
```

Keep user-facing error text in the localized object or WordPress translations.

## DOM Safety

- Never insert server or user strings with jQuery `.html()`, `innerHTML`, or `insertAdjacentHTML`. Use `.text()` / `textContent` and create elements through DOM APIs.
- Encode values placed in URL components with `encodeURIComponent()`.
- Namespace jQuery events (for example, `click.acme`) and use delegated handlers for elements added dynamically.
- Keep selectors and action names in constants rather than scattering string literals through handlers.

## Localization

Do not hardcode user-facing strings in scripts. Pass them through the localized object, or use `wp.i18n.__()` with the `wp-i18n` dependency and `wp_set_script_translations()` for the script. Keep the text-domain argument a literal string, as required by `WORDPRESS_RULES.md` → “Localization”.

## Logging

Use the one shared logger described in `COMMON_RULES.md`: register an `acme-logger` handle that exposes `acme.logger` with `debug`, `info`, `warn`, and `error` methods. Set its level from PHP using `WP_DEBUG`. Calls to `console.*` belong only in that logger file; shipped feature scripts must not call `console.log` or the console directly.

## Naming and Constants

- Use `camelCase` for functions and variables, `PascalCase` for classes, and `UPPER_SNAKE_CASE` for module constants.
- Keep feature constants at the top of the file that owns the feature.
- Use `Object.freeze()` for enum-like objects.

## Testing

Keep DOM wiring thin and put behavior in small pure functions on the namespace object. If the project already has a JavaScript test runner, test those functions with it; do not add a runner solely for these scripts.

For every change, check the affected page in a browser: confirm the feature works, a failed request shows its error state, and the console has no errors. An agent may use `agent-browser` on a local or test site.

## Code Analysis

When the project uses cli-code-analyzer, copy the JavaScript scripts from `javascript_setup_files/tools/` as described in `JAVASCRIPT_RULES.md` → rule 6. Set `LANGUAGE=javascript`, keep the local config gitignored, and exclude vendor and minified files from analysis.
