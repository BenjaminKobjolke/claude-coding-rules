# Version
1

Increase this version number whenever this rule file changes.

# API Contract Repository Rules

These rules apply to a repository that holds a shared API contract as JSON and a README, with no
application code. The API produces the contract; client projects consume it as a Git submodule.

## Layout

Keep contract JSON files and `README.md` in the repository root. Do not add application code,
build steps, or version numbers. A client's submodule pointer identifies the contract version.

## Entry format

Each entry is keyed by its shared name and has a `values` list, a `direction`, and a `description`:

```json
"TodoType": {
  "values": ["implementation", "research"],
  "direction": "api_to_client",
  "description": "Todo.type"
}
```

Keep values sorted and unique. The description names where each value appears in the API.

## Direction semantics

- `api_to_client`: a client mirror must equal the contract values so clients recognize every
  value the API can send.
- `client_to_api`: a client mirror must be a subset of the contract values so the API accepts
  every value the client can send.

## Producer and consumer roles

The API is the producer. It exports the contract from its own constants, and a test checks that
the committed contract is fresh. Each client is a consumer: its tests compare its own enum mirrors
with this contract using the direction semantics above, and skip when `contract/` is not checked
out.

## Submodule usage

Clients mount this repository at `contract/` and commit pointer updates when they take a contract
change. Use `GIT: bump <name> submodule` as the pointer-bump commit message. Production code must
not read `contract/`; it is test input only.

## Change order
<!-- steps: review, code -->

Keep deployed clients compatible with every API value:

1. To add an `api_to_client` value, update the contract first, then the clients, then let the API
   emit it.
2. To add a `client_to_api` value, update the contract and API first, then let the client send it.
3. To remove a value, stop the API from using it, then remove it from the contract, then from the
   clients.
4. Never rename a value; treat a rename as an addition followed by a removal, each in its safe
   order.
5. Add a new shared entry in the same change that introduces it.

## README sync

Update the README notes in the same commit as every contract change. Keep the producer, consumers,
usage, and relevant change-order notes accurate.

## Validation

Before committing, verify that every contract JSON file is valid, every `values` list is sorted and
unique, and every `direction` is either `api_to_client` or `client_to_api`. Run the repository's
contract check script or validate the JSON with `python -m json.tool`.

## Not applicable

Language rules, `DESIGN_RULES.md`, and code analyzers do not apply because this repository has no
application code. `/analyze:setup` is not needed because there is no code for an analyzer to inspect.
