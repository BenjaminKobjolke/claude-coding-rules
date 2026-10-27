# Version
2

Increase this version number whenever this rule file changes.

# Server-Rendered PHP Frontend Rules

These rules apply to PHP web frontends that render HTML on the server with Twig, call a separate
REST API for data, and do not own a database. They complement `COMMON_RULES.md`, `PHP_RULES.md`, and `php/APP.md`.

Pair with `PHP_RULES.md`, `php/APP.md`, `SCSS_RULES.md`, `TYPESCRIPT_RULES.md`, and `DESIGN_RULES.md` — rules there are not repeated here.

---

## Tech Stack

Typical projects use PHP 8.5 and Slim 4 for routing and middleware, Twig 3 for templates, Bootstrap 5
and Bootstrap Icons from a CDN, Guzzle 7 for API calls, PHP sessions for server-side state, and
Monolog through the project `Logger`. Compile SCSS with the Dart Sass CLI and browser TypeScript with
esbuild. Use PHPUnit, PHPStan, and PHP-CS-Fixer for tests and code quality. Pin CDN asset URLs to a
specific version and include the matching Subresource Integrity (`integrity`) hash and
`crossorigin="anonymous"` attribute.

---

## Project Structure

Keep HTTP entry, application code, templates, source assets, and generated assets in distinct places:

```text
project/
├── public/index.php
├── src/
│   ├── Controller/
│   ├── Service/
│   ├── Config/
│   ├── Middleware/
│   ├── DTO/
│   └── Twig/
├── templates/
│   ├── base/
│   ├── layouts/
│   ├── components/
│   └── pages/
├── assets/
│   ├── scss/                 # Source, compiled to css/
│   ├── css/                  # Generated output; do not edit by hand
│   ├── ts/                   # Source, bundled to js/
│   └── js/                   # Generated output; do not edit by hand
├── lang/
├── config/app.php            # Local config; keep app.php.example committed
└── tests/
    ├── Unit/
    └── Integration/
```

---

## Frontend Only — Never Change the API From Here (BINDING)

The backend API has its own repository and owns its endpoints, fields, validation, sorting, filtering,
and paging. Do not edit that backend from the frontend project. When a screen needs a missing API
capability, request it through `/feedback:write` or a linked todo, then implement against the agreed
contract. Follow `COMMON_RULES.md` → “API Clients: the API Sorts, Filters and Pages”.

---

## One API Round per Page

Load the independent data needed for a page together, for example through a Guzzle concurrent pool
behind a page loader. Do not make a detail request for every row in a list (N+1). If a page needs too
many calls, request a screen overview endpoint from the API project; see
`project_type/REST_API.md` → “Screen Overview Endpoints”. Forget session-cached lookups after a
successful mutation so later reads use current data.

---

## AbstractController

Every page controller extends the shared `AbstractController`. Its `render()` method adds shared
template context such as the current user, flash messages, and locale. Templates receive that
context; they do not fetch it themselves. Reuse its route-name-based `redirect()`, `flash()`, `t()`,
and API access helpers instead of rebuilding them in page controllers.

```php
final class CustomerController extends AbstractController
{
    public function show(Request $request, Response $response, array $args): Response
    {
        $customer = $this->api()->getCustomer((int) $args['id']);

        return $this->render($response, 'pages/customer/show.html.twig', [
            'customer' => $customer,
        ]);
    }
}
```

---

## ApiClient

`ApiClient` is the only class that makes HTTP calls. It wraps Guzzle, adds the JWT and other required
context headers from the server-side session, maps transport and API errors, and returns an
`ApiResponse` DTO containing status, success, data, metadata, and an error message. Wrap response
data in typed DTOs before it reaches controllers or templates; see `COMMON_RULES.md` → “No
Bag-of-Keys Returns at Module Boundaries”. Build pagination DTOs from API metadata, for example with
`PaginationData::fromApiMeta()`.

When the API returns 401, clear the authenticated session and redirect through the login flow. Keep
that behavior centralized in the client or its shared auth handling, not repeated in each controller.

---

## Auth and Session

Keep the JWT in the server-side PHP session. Never expose it to browser JavaScript, a readable
cookie, or `localStorage`. Configure the session cookie as `HttpOnly`, `Secure`, and `SameSite=Lax`,
and regenerate the session ID after login. Release the session lock early on requests that only read
session data, so one slow page does not serialize the user's other requests.

---

## Constants Classes

Keep API endpoint names, route names, session keys, and flash message types in constants classes in
`src/Config/`, such as `ApiEndpoints`, `RouteNames`, `SessionKeys`, and `FlashMessageTypes`.
`TranslationKeys` is defined by `PHP_RULES.md`; localization rules are in `php/APP.md`. Build links with route names through `url_for()`;
never hard-code route paths into templates or controllers.

---

## Twig

- Keep Twig `strict_variables` enabled and autoescaping on. Never apply `|raw` to API data.
- After every `.html.twig` change, run `tools/run_twig_lint.bat`. It checks syntax only, so also
  confirm that the controller supplies every variable the template reads.
- Use the project's `asset()` Twig function for assets. It must account for the deployment base path
  and append a cache-busting version (for example, a file modification time). This type-specific
  rule overrides `php/APP.md` advice to use plain relative paths: nested routes such as
  `/customers/5/edit` make relative paths resolve from the wrong directory.
- Do not add `only` to an include when the component needs shared globals.
- Share create and edit markup through a `_form` partial where their fields are the same.

---

## Forms and Mutations

Submit mutations from HTML forms using POST and validate a CSRF token in middleware. The controller
validates input into a typed object, then asks `ApiClient` to send the corresponding PUT, PATCH, or
DELETE request to the separate API. Follow `php/APP.md` → “Value Objects for `$_POST` / `$_GET` Boundaries”.
Use post/redirect/get with a flash message for the ordinary non-AJAX response.

---

## AJAX Forms With No-JS Fallback

Small forms and pages with multiple independent forms use the shared AJAX form widget, marked with
`data-ajax-form`, so submitting one form does not discard sibling form state. The controller detects
AJAX requests and returns the widget's expected JSON response. Keep the flash-and-redirect path for
users without JavaScript. Reuse shared widgets; do not add one-off fetch and submit handling per page.

---

## Assets

Never edit generated `assets/css/` or `assets/js/` files by hand. Keep styles in `assets/scss/` and
compile them with the Dart Sass CLI; this replaces the Vite build instructions in `SCSS_RULES.md` for
this project type. Keep browser code in `assets/ts/` and bundle it with esbuild into one browser
bundle. Mark Bootstrap as external in esbuild because it is loaded from the CDN.

Use a browser TypeScript config with strict checking and DOM libraries, without Bun or Node types;
esbuild emits the JavaScript, so TypeScript uses `noEmit`:

```json
{
  "compilerOptions": {
    "strict": true,
    "lib": ["DOM", "ES2022"],
    "noEmit": true
  },
  "include": ["assets/ts/**/*.ts"]
}
```

Organize TypeScript into `core/`, reusable `widgets/`, and page-specific `pages/` modules, with
`assets/ts/app.ts` as the entry point.

---

## Testing

Use unit tests for DTOs and services. Integration tests boot the Slim app and provide `ApiClient` a
Guzzle `MockHandler`, so they need neither a live API nor a database. The `run_*` batch files must
return PHPUnit's exit code; see `COMMON_RULES.md` → “Test Runner Scripts”.

This project type has no database of its own, so its integration tests use the mocked API handler
instead of the database mirror described in `php/APP.md` → “Required Batch Files”.

---

## Required Batch Files

Provide these scripts in `tools/`:

| File | Purpose |
|------|---------|
| `run_tests.bat` | Run unit tests |
| `run_integration_tests.bat` | Run integration tests |
| `run_phpstan.bat` | Run PHPStan |
| `run_cs_fixer.bat` | Check or fix PHP-CS-Fixer style |
| `run_twig_lint.bat` | Lint Twig template syntax |
| `build_css.bat` | Compile SCSS with Dart Sass |
| `watch_css.bat` | Watch and compile SCSS changes |
| `build_js.bat` | Bundle browser TypeScript with esbuild |
| `watch_js.bat` | Watch and bundle TypeScript changes |
