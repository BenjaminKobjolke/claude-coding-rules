# Version
2

Increase this version number whenever this rule file changes.

# Project Types Overview

Project-type rule files live in the `project_type/` subfolder. They complement the language
rules (`*_RULES.md`) — when setting up a project's `CODING_RULES.md`, include the matching
project-type file in addition to `COMMON_RULES.md`, `AI_RULES.md`, and the language rules.

Each project-type file references `COMMON_RULES.md` and the relevant language rules itself.

## REST API — `project_type/REST_API.md`

PHP REST API projects. Stack: Slim 4 (PSR-7) + Cycle ORM 2.x + Firebase JWT + MySQL/MariaDB.
Covers project structure, route conventions (`/api/v1/`), `AbstractController` response
helpers, service/repository/presenter layers, auth + CORS middleware, `SyncTables`
auto-migration, `ApiTestCase` test infrastructure, endpoint documentation in
`docs/endpoints/`, Hoppscotch collections, and required `tools/*.bat` files.

Pair with `PHP_RULES.md`.

## Frontend SPA — `project_type/FRONTEND.md`

Frontend single-page applications, framework-agnostic. Covers Vite build tooling
(`base: './'`, dev server API proxy), Tailwind CSS with PostCSS, and OS-aware dark mode.

Pair with the framework/language rules, e.g. `SVELTE_RULES.md` and `SCSS_RULES.md`.
