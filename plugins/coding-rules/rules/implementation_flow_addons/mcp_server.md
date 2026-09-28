# Version
1

Increase this version number whenever this rule file changes.

# MCP Server via OpenAPI (Optional Addon)

**Optional.** Before adding this to a project, ASK the user whether the project exposes (or
should expose) an MCP server. Only wire it into the project's `CODING_RULES.md` if they say yes.
Applies to PHP REST APIs (Slim 4, see `project_type/REST_API.md`). Reference implementations:
`tickets-api` (OAuth 2.1 + API tokens), `erp-api` (JWT only, company-bound token).

---

## Library, not hand-written tools

Use the in-house library **`xida/api-mcp`** (`dev-master`, VCS repo
`https://xida.me:3030/Intern/xida-api-mcp.git`, wraps `mcp/sdk`). Never hand-write tool
handlers. The app keeps only adapters:

| File | Role |
|------|------|
| `src/Mcp/McpConfigFactory.php` | The one place for MCP values: spec path, session dir, server name, `root_url`, Slim base-path prefix, `Authorization` header stamping, read-only / destructive / excluded operationId lists |
| `src/Mcp/BearerTokenResolver.php` | Validates the bearer exactly like `AuthMiddleware` and returns the full `Bearer <token>` header value, which the library re-stamps on every sub-request |
| `src/Mcp/McpLogger.php` | PSR-3 adapter to the project `Logger` |
| `src/Util/BasePathResolver.php` | Single owner of the Slim base path — `index.php` and the MCP sub-requests must agree (WAMP subfolder) |

Tool calls are dispatched **in-process** through the real Slim app (`InProcessDispatcher`), so
auth, tenant/company context and role guards apply unchanged. Route: `POST`/`DELETE /mcp`
behind the library's `BearerAuthMiddleware`, outside the `/api/v1` group. CORS allows
`Mcp-Session-Id` / `MCP-Protocol-Version` and exposes `Mcp-Session-Id` / `WWW-Authenticate`.

## The spec IS the tool surface (BINDING)

- Tools are compiled from `public/openapi.yaml`, generated from swagger-php attributes on
  controller methods (`tools/generate_openapi.bat` = `vendor\bin\openapi src --output
  public/openapi.yaml`). Commit the yaml. Every documented `operationId` is a live tool.
- Attributes use the **full** `/api/v1/...` path (the dispatcher uses it verbatim) and a
  camelCase `<resource><Action>` operationId: `leadsList`, `leadsInfo`, `leadsCreate`,
  `leadsUpdate`, `bankTransactionsSearch`.
- Path + query params become top-level tool arguments; the request body nests under `body`.
  Shared envelopes, parameters and request-body schemas live in `src/OpenApi/`.
- Schema classes carry a `//` comment, not a `/** */` docblock: swagger-php copies a class
  docblock into the first property's description.
- **Never a tool unless the user decided it explicitly:** credential/auth and user management,
  settings, templates, cron, AI, sends (emails, documents), money movement, and deletes. Leave
  them undocumented; `EXCLUDED_OPERATION_IDS` is for operations the REST docs need but MCP
  must not see.
- Read-only hints are an explicit GET list in `McpConfigFactory`, never a verb check, so a
  read-shaped POST is a decision.

## Locked tool list — tests

- `OpenApiTest` (no DB): generation emits no warnings, the committed yaml is fresh, and the
  operation set equals a `DOCUMENTED_OPERATIONS` constant (operationId => [method, path]). A new
  tool = a deliberate edit of that constant.
- `McpSpecParityTest` (no DB): every documented operation compiles to a tool, every parameter
  and body field survives compilation, no `format: binary` field reaches a tool without upload
  support, and the read-only list equals the documented GETs.
- `McpServerAdapterTest` (integration): `initialize` → `tools/list` → `tools/call` through the
  real `/mcp` route; a read-only role's write is a tool error; 401 + `WWW-Authenticate` without
  or with a bad token. Point the session dir at a temp folder — `FileSessionStore::gc()`
  unlinks every stale file in its directory, `.gitkeep` included.

## Tokens

- JWT-only projects: add `POST /api/v1/auth/mcp-token` (auth, no tenant context) that mints a
  long-lived JWT (config `mcp_token_lifetime`) bound to a tenant the user can access, returning
  `access_token`, `token_type`, `expires_at`, `expires_in`, `mcp_url`. Access and role are
  re-checked per request, so no revocation store is needed. The frontend shows the token once
  with a ready `claude mcp add --transport http <name> <mcp_url> --header "Authorization: Bearer
  <token>"` line.
- Browser connectors (claude.ai) need OAuth 2.1 via the library's `Oauth\` seams (tickets-api).

## Deployment

- `data/mcp-sessions/` writable (`.gitkeep` tracked, contents gitignored); `data/` writable for
  `data/mcp-tool-cache/` (gitignored, content-keyed, safe to delete).
- `root_url` config key (no trailing slash): feeds `mcp_url`, the DNS-rebinding allowlist and
  the 401 `resource_metadata` hint.
- Spec path handed to the library is an absolute **native** path; cebe's `ReferenceContext`
  rejects `X:/...` and `..` segments.
- Upload `vendor/devizzent/cebe-php-openapi`, or the first `/mcp` request fails with
  `Class "cebe\openapi\Reader" not found`.
- Document it all in the project's `docs/MCP.md` (install, tool scope, architecture, curl smoke).
