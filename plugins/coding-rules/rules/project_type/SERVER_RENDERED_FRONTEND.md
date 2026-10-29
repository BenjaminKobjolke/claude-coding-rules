# Version
3

Increase this version number whenever this rule file changes.

# Server-Rendered PHP Frontend Rules

These rules apply to PHP web applications that route requests and render HTML on the server,
commonly with Twig. The application owns page rendering and may use a local database, call one or
more APIs, or do both. It is neither a REST API project nor a browser-rendered single-page app.

It covers server-side routing, route names, template rendering, application configuration, static
and media assets, and deployment boundaries.

Pair with `COMMON_RULES.md`, `PHP_RULES.md`, and `php/APP.md`. Add `DESIGN_RULES.md` for its user
interface and add rules for asset languages or build tools the project actually uses, such as
`SCSS_RULES.md` or `TYPESCRIPT_RULES.md`.

---

## Request Routing and Controllers

- Keep the web server's document root on the public directory. Route requests through one front
  controller when the framework requires it; keep route declarations in the framework's routing
  configuration rather than duplicating path checks across controllers.
- Give routes stable names and generate links and redirects from those names. Keep URL paths,
  HTTP methods, middleware, and controller actions explicit and consistent.
- Keep controllers as the boundary that translates an HTTP request into application work and a
  response. Put domain decisions and persistence in existing services and repositories; do not
  put SQL, API transport, or business workflows in route declarations or templates.
- Validate path, query, form, and uploaded-file input at the request boundary. Convert accepted
  input into typed values before passing it to application services.
- Use POST/redirect/GET for ordinary form submissions. Protect state-changing requests with CSRF
  tokens and the framework's method and authorization checks.

---

## Rendering with Twig

- Keep Twig autoescaping enabled and strict variable checks on outside production if the framework
  supports that split. Never mark user-provided or externally sourced content as raw HTML without
  an explicit sanitization boundary.
- Controllers or page services assemble the data a page needs and pass it as template context.
  Templates render that context; they do not query a database or make network requests.
- Put shared page structure and reusable fragments in base layouts and components. Keep
  page-specific markup in page templates, and share form markup through partials when create and
  edit forms have the same fields.
- Keep presentation and localization in templates and translation resources. Put decisions that
  affect permissions, prices, or persisted state in application code.
- Use the project's URL and asset helpers to build links. Avoid hand-joining relative paths, which
  resolve differently from nested routes or an application deployed below a URL prefix.

---

## Application Configuration and State

- Load environment-specific values through the project's central configuration layer. Commit an
  example configuration that names required keys, but never commit secrets or machine-specific
  values.
- Keep authentication and session state server-side where possible. Configure session cookies as
  `HttpOnly`, `Secure` in HTTPS environments, and an appropriate `SameSite` mode; regenerate the
  session identifier after authentication changes.
- Apply authorization on the server for every protected page and mutation. Hiding a link or button
  is not access control.
- Store durable application data through the project's existing repository or ORM conventions.
  A local database is optional; do not add a database mirror solely because a page consumes an API.

---

## Data Sources and API Consumers

Use the application's existing service and repository boundaries for local data. When a page needs
data from an external or separately owned API, keep HTTP calls in the shared API client or adapter,
and map responses to typed values before they reach controllers or templates.

The following guidance applies only when the application consumes a separate API:

- Keep API transport, authentication headers, error mapping, and response decoding in the shared
  client. Never expose server credentials or bearer tokens to browser JavaScript.
- Request the independent data needed for a page together where practical; avoid a detail request
  for every row in a rendered list.
- Follow the API's paging, sorting, and filtering contract. Request a missing capability from the
  API owner instead of rebuilding a complete collection in the PHP frontend.
- On authentication expiry, clear invalid server-side session state and use the application's
  login flow. Keep this behavior centralized rather than repeating it in page controllers.

---

## Static and Media Assets

- Keep source assets separate from generated bundles. Edit source styles and scripts, and use the
  project's build command to produce generated CSS and JavaScript.
- Generate asset URLs through the shared asset helper so the deployment base path and cache-busting
  version are handled consistently. Do not hard-code root-relative URLs when the app may be mounted
  under a prefix.
- Serve only intended public assets from the document root. Keep source files, configuration,
  uploaded originals, and other private data outside it unless they are deliberately published.
- Validate media uploads by size, allowed content type, and file content. Generate server-side
  filenames, prevent executable uploads, and store private media outside the public directory with
  access controlled by the application.
- Use stable cache headers for fingerprinted static assets. Ensure deployment publishes the
  generated files referenced by the rendered pages.

---

## Deployment Boundary

- Treat the web server and application as separate configuration boundaries: document the public
  document root, front-controller fallback, PHP runtime requirements, and any required rewrite or
  proxy settings.
- Keep secrets and environment-specific configuration on the target environment. Verify required
  configuration at startup and fail with a useful server-side message rather than rendering a
  partially configured page.
- Build frontend assets before release and deploy the matching generated files with the PHP code.
  Do not edit generated bundles by hand.
- Run database migrations as an explicit deployment step only when the application owns a database.
  Keep API migrations and deployments in the API project's release process.
- Document writable runtime directories, uploaded media handling, cache clearing, and safe release
  rollback where they apply. Do not make the entire application tree writable by the web server.

---

## Tests

- Test route registration, controller responses, template rendering, validation, and authorization
  at the narrowest useful level.
- Use temporary databases or the project's database test setup when exercising persistence. Stub
  external API clients so tests do not depend on a live service.
- Include integration coverage for the application's request-to-render path and for its error
  responses. Keep the test runner's exit code intact in project scripts.
