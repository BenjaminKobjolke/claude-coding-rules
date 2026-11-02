# Version
1

Increase this version number whenever this rule file changes.

# MCP Server over stdio (Rust, Optional Addon)

**Optional. Ask the user whether the project exposes or should expose an MCP server over stdio
before adding this addon.** For a PHP HTTP/OpenAPI MCP server, use `mcp_server.md` instead. Apply
this addon only when the user opts in.

---

## Server Boundary

- Put the MCP server in one dedicated crate. Keep it as a thin adapter over the application's API
  crate; tool handlers should call the same request and validation logic as the app.
- Use stdio transport with stdout reserved exclusively for protocol messages. Send diagnostics and
  application logs to stderr through the project's logger.
- Generate tool input schemas from the API request types with `schemars`, behind an optional
  `schema` Cargo feature when schema generation is not needed by every build. Do not maintain a
  second, hand-written JSON schema for the same request.
- Treat each tool as an API request and preserve the API's authorization, validation, and error
  semantics.

---

## Tool Exposure

- Keep the exposed tool names in an explicit allowlist. Adding a tool is a deliberate change to that
  list; do not expose every API operation by discovery alone.
- Exclude destructive, credential, and settings operations by default. Add one only after an
  explicit user decision, following the same exposure decision as `mcp_server.md`.
- Keep read-only annotations in a separate explicit list. Mark a tool read-only only when its
  behavior cannot mutate application state.

---

## Tests and Installation

- Add a unit test that locks the tool-name allowlist so every new tool requires a deliberate test
  update.
- Add a schema-parity test proving every API request field appears in its generated tool input
  schema.
- Add an integration test under the crate's `tests/` directory. Spawn the server and exercise
  `initialize`, `tools/list`, and `tools/call` over pipes; verify stdout contains only protocol
  responses.
- Document installation with `claude mcp add <name> -- <binary> --mcp`, and describe the server's
  tool scope in `docs/MCP.md`.
