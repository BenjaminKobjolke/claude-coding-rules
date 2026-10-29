# Version
2

Increase this version number whenever this rule file changes.

# Python Web Service Rules (FastAPI / ASGI)

See `COMMON_RULES.md` and `PYTHON_RULES.md` for rules that apply across languages and Python
projects. These rules add web-service guidance for FastAPI and similar ASGI frameworks; they do
not prescribe one framework, frontend stack, or authentication model.

## Route organization

- Keep route declarations thin. Parse the request, call a focused service or domain function, and
  translate its result into an HTTP response. Keep business rules out of route functions.
- Group related endpoints into framework routers or equivalent modules by resource or capability.
  Keep application construction and router registration in one clear entry point.
- Keep framework-specific request and response types at the HTTP boundary. Pass validated domain
  values into services so those services can be tested without constructing web requests.
- Use the framework's dependency mechanism for shared request-scoped resources and injected
  collaborators. Avoid hidden module-level mutable state.

## Request and response boundaries

- Define typed request models for bodies, query parameters, and path values. Use Pydantic or the
  framework's equivalent validation instead of repeating manual checks in route handlers.
- Validate constraints that shape the domain at the boundary, then keep domain invariants in the
  domain layer as well. Do not treat successful parsing as proof that every business rule holds.
- Declare response models or equivalent schemas for public endpoints. Return only intended public
  fields; do not serialize persistence models or internal objects directly.
- Test malformed input, missing values, and invalid domain states with stable status codes and
  useful, non-sensitive error details.

## Error handling and logging

- Use the framework's exception handlers or one shared error translation layer to produce a
  consistent error response shape. Map known domain errors to appropriate client statuses and
  let unexpected failures remain server errors.
- Do not catch broad exceptions in each route to return success-shaped defaults. Log unexpected
  failures once at the shared boundary with request context, then return a safe response without
  stack traces, credentials, or internal implementation details.
- Follow the centralized `AppLogger` and structured logging guidance in `PYTHON_RULES.md`.
  Include a request or correlation identifier when the service has one.

## Configuration and secrets

- Keep service settings in one typed settings object, loaded from environment variables or the
  deployment's secret store. Pass settings to application construction and the collaborators that
  need them instead of reading the process environment throughout route code.
- Provide a safe local example for required settings. Never commit real credentials, and never
  include secrets in error responses, logs, or diagnostic endpoints.
- Configure bind address, port, external URLs, CORS origins, and debug behavior per environment;
  do not assume a developer machine or deployment-specific value in code.
- Fail during startup with a clear configuration error when a required setting is absent or
  invalid. Avoid silently enabling debug behavior or permissive origins in production.

## Authentication and authorization

- Choose authentication to fit the service's actual callers: for example, an existing identity
  provider, signed tokens, service credentials, or no authentication for a deliberately public
  service. Do not add a login system by default when the service has no protected operations.
- For an intentionally unauthenticated service, document that choice and test that public routes
  stay reachable without credentials. Still validate inputs, apply resource limits where needed,
  and avoid exposing administrative or diagnostic operations publicly.
- When authentication is enabled, centralize credential verification in framework dependencies or
  middleware, and enforce authorization at the operation that owns the protected resource.
- Treat authentication and authorization as separate checks. Test missing, invalid, and
  insufficient credentials, including routes that must remain public.

## Static browser assets

- A service may serve HTML, stylesheets, scripts, and other static files through its ASGI app.
  Mount or serve only an explicit asset directory and use paths that remain inside it.
- Keep browser assets usable with the project's existing delivery approach. Serving static files
  does not require a separate frontend framework, package manager, or frontend build tool.
- Apply appropriate cache headers to versioned assets. Avoid caching personalized responses or
  embedding server secrets in files sent to the browser.
- If the browser interface grows into a separate frontend application, select frontend rules for
  that work in addition to this service rule.

## Command-line integration

- Keep command-line parsing and process exit behavior in a CLI entry point, separate from ASGI
  startup and route modules. Share service operations through ordinary Python functions or
  injected collaborators, not by making the CLI issue requests to its own server.
- Give commands explicit arguments and exit codes. Keep terminal output and prompts in the CLI
  boundary, and make non-interactive use possible for automation.
- Test command behavior without starting a network listener. Inject or patch external effects,
  and assert exit codes, output, and the service operation invoked.

## Focused tests

- Use pytest and the ASGI framework's in-process test client for route tests; unit tests for
  domain behavior should not start a server or use the network.
- Cover successful and invalid requests, response shape and status, and shared error responses.
- Test public routes without credentials and protected routes with missing, invalid, and valid
  credentials, plus authorization failures where applicable.
- Test CLI argument parsing and outcomes independently of ASGI startup and network access.
- Keep fixtures isolated and fast. Use temporary directories for files and explicit test settings
  so tests do not depend on developer credentials, environment state, or a running service.
