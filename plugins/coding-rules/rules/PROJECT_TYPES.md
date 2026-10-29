# Version
11

Increase this version number whenever this rule file changes.

# Project Types Overview

Project-type rule files live in the `project_type/` subfolder. They complement the language
rules (`*_RULES.md`) — when setting up a project's `CODING_RULES.md`, include the matching
project-type file in addition to `COMMON_RULES.md`, `IMPLEMENTATION_FLOW.md`, and the language rules.

Each project-type file references `COMMON_RULES.md` and the relevant language rules itself.

## REST API — `project_type/REST_API.md`

PHP REST API projects. Stack: Slim 4 (PSR-7) + Cycle ORM 2.x + MySQL/MariaDB. Authentication
uses one variant in `project_type/rest_api/`:

- `rest_api/JWT_AUTH.md` for Bearer/JWT login.
- `rest_api/API_KEY_AUTH.md` for static admin and user API keys.

Covers project structure, route conventions (`/api/v1/`), `AbstractController` response
helpers, service/repository/presenter layers, auth + CORS middleware, `SyncTables`
auto-migration, `ApiTestCase` test infrastructure, endpoint documentation in
`docs/endpoints/`, Hoppscotch collections, and required `tools/*.bat` files.

Pair with `PHP_RULES.md` and `php/APP.md`.

## Python Web Service — `project_type/PYTHON_WEB_SERVICE.md`

FastAPI and similar ASGI services, including services that serve static browser assets or expose
a command-line integration. Covers route organization, request and response boundaries, errors,
configuration, optional authentication, static assets, CLI boundaries, and focused tests without
requiring a particular frontend build tool.

Pair with `PYTHON_RULES.md`. `DESIGN_RULES.md` applies when the service includes a user-facing
browser interface.

## PHP Library — `project_type/PHP_LIBRARY.md`

Framework-free Composer packages (`"type": "library"`), typically using Guzzle with PHPUnit unit
tests and live-API integration tests. Pair with `PHP_RULES.md` alone; skip `php/APP.md` and
`DESIGN_RULES.md`.

## Frontend SPA — `project_type/FRONTEND.md`

Frontend single-page applications, framework-agnostic. Covers Vite build tooling
(`base: './'` by default or per build target, dev server API proxy), Tailwind CSS with
PostCSS, and OS-aware dark mode or a user-facing theme toggle.

Pair with the framework/language rules, e.g. `SVELTE_RULES.md` and `SCSS_RULES.md`.

For PHP-rendered pages use the server-rendered type instead.

## React + Vite Apps in a pnpm Workspace

Pair `project_type/FRONTEND.md` with `TYPESCRIPT_RULES.md` and
`typescript/PNPM_WORKSPACE.md`. Add `typescript/ELECTRON.md` when the workspace
has an Electron desktop app. `DESIGN_RULES.md` applies. Do not apply
`JAVASCRIPT_RULES.md` to this setup.

## Server-Rendered PHP Frontend — `project_type/SERVER_RENDERED_FRONTEND.md`

PHP web applications that route requests and render HTML on the server, commonly with Twig. They
may use a local database, consume an API, or both; they are not REST APIs or frontend SPAs. The type
covers server-side routing, page controllers, template rendering, application configuration,
static and media assets, and deployment boundaries. For REST endpoints, use
`project_type/REST_API.md`; for a browser-rendered SPA, use `project_type/FRONTEND.md`.

Pair with `PHP_RULES.md` and `php/APP.md`. Add `DESIGN_RULES.md` because the project has a UI, and
add the rules for asset languages and tools it uses, such as `SCSS_RULES.md` or
`TYPESCRIPT_RULES.md`. Do not pair this type with the REST API or frontend SPA rules for the same
server-rendered application.

## Flutter app vs. library

Flutter libraries/plugins (pub packages whose only app is `example/`) use
`FLUTTER_RULES.md` alone. Flutter apps add `flutter/APP.md`.

## Python Desktop Host Plugin — `project_type/PYTHON_DESKTOP_PLUGIN.md`

Python extensions loaded and run inside a desktop application's plugin runtime, such as fman
plugins. Pair with `PYTHON_RULES.md`; the rules cover the host API boundary, commands and prompts,
long-running tasks, host-aware file access, settings, dependencies, and tests that can run without
the host installed. Do not apply it to a standalone Python desktop app: use `python/GUI.md` for
PySide6 applications instead.
