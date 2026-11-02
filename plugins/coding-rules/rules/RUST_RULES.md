# Version
1

Increase this version number whenever this rule file changes.

# Rust Rules (Cargo Workspace)

See `COMMON_RULES.md` for rules shared by all languages. These rules add Rust-specific guidance.

---

## Toolchain and Edition

- Pin an exact Rust channel in `rust-toolchain.toml` and include the `rustfmt` and `clippy` components.
- Declare `edition` and `rust-version` once in `[workspace.package]`; crates inherit them with
  `edition.workspace = true` and `rust-version.workspace = true`.
- Keep the committed `rustfmt.toml` at the Cargo workspace root and format with `cargo fmt --all`.

---

## Cargo Workspace Layout

- The workspace root may be below the repository root, such as `src/`. Run Cargo commands from
  that directory, or pass `--manifest-path <workspace>/Cargo.toml`. Tool batch files must do the
  same, using `pushd` and restoring the directory before they exit.
- For multi-crate workspaces, declare `members = ["crates/*"]` and use resolver `"3"` with the
  2024 edition.
- Declare third-party and internal crate dependencies once in `[workspace.dependencies]`; member
  crates use `dep.workspace = true`. Keep path dependencies there too.
- Give each crate one clear responsibility, such as core types, IO, UI, server, or CLI. Keep binary
  crates thin and put reusable behavior in library crates.
- Put heavy or platform-specific dependencies behind an opt-in Cargo feature. Add a short manifest
  comment explaining the cost or platform constraint, and keep default features lean.
- Put machine-specific paths and tool locations in environment variables or local configuration,
  never in committed `.cargo/config.toml`. Shared Cargo config may hold portable aliases.

---

## Formatting and Linting

- Run `cargo fmt --all` with the committed workspace `rustfmt.toml`; CI and analysis use
  `cargo fmt --all -- --check`.
- Define shared policy in `[workspace.lints.rust]` and `[workspace.lints.clippy]`. Every member
  crate opts in with `[lints] workspace = true`.
- Use `cargo clippy --workspace --all-targets -- -D warnings` as the workspace analyzer, while
  respecting intentional workspace lint allowances.
- An `#[allow]` or `#[expect]` names the lint. Prefer `#[expect(clippy::lint_name, reason = "…")]`
  so the compiler warns if the exception stops being needed.

---

## Documentation Comments

- Add `//!` crate and module documentation that explains what the module owns and why.
- Add `///` documentation to every public item. With `missing_docs = "warn"` and Clippy warnings
  denied, an undocumented public item fails analysis.
- Keep examples in doc comments executable as doc tests when practical.

---

## Error Handling

- Library crates expose typed errors, usually with `thiserror`; keep one error enum at each crate or
  module boundary where callers need to distinguish failures.
- Reserve `anyhow`-style errors for binaries, command-line glue, and tests. Add context as errors
  cross an application boundary.
- Use `?` to propagate errors. Do not add new public `Result<_, String>` APIs or silently discard
  errors with `let _ =`.
- Do not use `unwrap()`, `expect()`, or `panic!` in non-test code unless a proven invariant makes
  failure impossible. Document the invariant; for `expect`, state why it holds in the message.

---

## Logging

- Use the `log` or `tracing` facade already used by the workspace; choose `tracing` for a new
  workspace. Do not switch an existing project between facades as part of unrelated work.
- Initialize the backend and level once from `app_logger.rs` in the binary crate's `init()`.
- Use structured fields when the selected facade supports them. Do not use `println!` or
  `eprintln!` for logs. A stdio protocol server keeps stdout for protocol messages and logs to
  stderr through the configured logger.

---

## Mapping Common Rules to Rust

- Apply the 300-line limit to each `.rs` file. Split modules using `foo.rs` with a sibling `foo/`
  directory; do not add `mod.rs` solely as a directory entry point. Generated code and generated
  Slint modules are exempt. Keep tests beside small modules or move larger integration tests into
  `tests/`.
- A Rust “class” is a struct and its `impl` blocks. Apply the god-class guidance to each type:
  watch public method count, collaborator fields, and unrelated responsibilities.
- Inject collaborators through constructors, using generics bounded by a trait or references and
  boxes such as `&dyn Trait` and `Box<dyn Trait>`. Define a trait near the code that consumes it.
  Avoid global mutable state and service singletons.
- Put related settings in one `Config` struct, deserialize it (for example with `serde`), and
  validate it when loading. Keep shared string constants in a `consts.rs` or `constants` module.
- Prefer newtypes and enums over bare `String` or numeric identifiers. Use exhaustive `match`
  expressions so adding a variant exposes every consumer that needs an update.
- For self-describing data, let the type expose its own fields through a trait method, for example
  `fn searchable_fields() -> &'static [&'static str]`.

---

## Ownership and API Style

- Borrow at call sites instead of cloning unnecessarily. Prefer `&str`, `&[T]`, and
  `impl AsRef<Path>` parameters when the function does not need ownership.
- Add no `unsafe` block without a nearby `// SAFETY:` comment that explains the invariant upheld.
- Avoid webs of `Rc<RefCell<…>>` when clearer ownership or message passing can express the design.

---

## Tests
<!-- steps: review, code -->

- Put unit tests in `#[cfg(test)] mod tests` beside the code. Put crate integration tests in that
  crate's `tests/` directory. Use injected traits to provide fakes for external collaborators.
- `tools/run_tests.bat` runs `cargo test --workspace --lib --bins` and then
  `cargo test --workspace --doc` so unit, binary, and doc tests are covered.
- `tools/run_integration_tests.bat` runs `cargo test --workspace --test "*"`.
- `tools/run_analysis.bat` runs `cargo fmt --all -- --check`, then
  `cargo clippy --workspace --all-targets -- -D warnings`; stop at and return the first failure.
- Each batch file changes to the workspace root first. Capture `%ERRORLEVEL%` immediately after
  each Cargo command, return its nonzero value, and do not use `pause`, output redirection, or a
  command chain that masks the Cargo exit code.
- Copy these scripts to `rust_setup_files/tools/` only after they have been proven in a real Rust
  project.

---

## Dependencies

- Follow COMMON's dependency version check against crates.io and respect the workspace's
  `rust-version` and target platforms.
- Commit `Cargo.lock` for applications and workspaces that contain binaries. Libraries may follow
  their ecosystem's lockfile policy.
