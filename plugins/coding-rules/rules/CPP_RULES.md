# Version
1

Increase this version number whenever this rule file changes.

# C++ Rules (C++17, Win32 / COM, CMake)

See `COMMON_RULES.md` for rules that apply to all languages.

---

## Language Standard & Compiler Flags

Use C++17 or newer, with extensions disabled. Set compiler options and Windows macros centrally in CMake, not in individual source files.

```cmake
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
target_compile_options(app PRIVATE /W4 /WX /permissive- /utf-8)
target_compile_definitions(app PRIVATE UNICODE _UNICODE WIN32_LEAN_AND_MEAN NOMINMAX)
```

Keep target-specific settings on the target that needs them. Do not weaken warnings to silence a finding without documenting why.

---

## Project Structure

Keep the entry point thin; business logic belongs in modules, not `wmain`, `wWinMain` or a window procedure.

```text
project/
├── CMakeLists.txt
├── CMakePresets.json
├── src/
│   ├── main.cpp
│   ├── Module.h
│   └── Module.cpp
├── tests/                 # unit tests
│   └── integration/       # integration tests
├── tools/                 # build and test .bat files
├── build/                 # generated; gitignored
└── README.md
```

`main.cpp` parses arguments, calls modules and maps the result to an exit code. Keep generated build output out of source control.

---

## Headers & Sources

- Use `#pragma once`; headers declare and `.cpp` files define.
- Include what you use. Forward-declare types when that safely avoids a header dependency.
- Never put `using namespace` in a header.
- Put each class in a matching `ClassName.h` / `ClassName.cpp` pair unless a small, tightly related type belongs with its owner.

---

## RAII & Ownership

- Do not use naked `new` or `delete`. Prefer `std::unique_ptr`; use `std::shared_ptr` only when ownership is genuinely shared.
- A raw pointer or reference is non-owning. Make ownership clear in the type and API.
- Wrap every OS handle in an RAII type, such as `wil::unique_handle` or a small unique handle with the correct deleter. Cleanup must run on every exit path.
- Prefer the rule of zero: compose RAII members instead of writing resource-management special members.

---

## COM

- Hold COM interface pointers in `Microsoft::WRL::ComPtr<T>` or `wil::com_ptr`; do not call `AddRef` or `Release` manually at call sites.
- Pair `CoInitializeEx` / `OleInitialize` with the matching uninitialize call on the same thread, using one RAII scope guard.
- A class implementing a COM interface must implement `IUnknown` correctly, including `QueryInterface` and a thread-safe reference count, or use `Microsoft::WRL::RuntimeClass`.
- Wrap ownership of memory returned by COM or Win32 APIs (`CoTaskMemFree`, `ReleaseStgMedium`, `GlobalFree`) so the matching release runs on every path.

---

## Error Handling

- Check every `HRESULT` with `FAILED()` or an equivalent helper; do not ignore API results.
- Choose one error style at each module boundary. Internal code may throw a project exception that carries the `HRESULT` and context.
- Never allow an exception to cross a COM method, a window procedure or `main`; catch there and convert it to an `HRESULT` or exit code.
- Read `GetLastError()` immediately after the failing call, before another API call can overwrite it.
- Use named constants for process exit codes.

---

## Const-Correctness & Types

- Prefer `const` locals, `const&` parameters for inputs, and `const` member functions when they do not modify object state.
- Use `constexpr` for compile-time constants; centralize strings as required by `COMMON_RULES.md`.
- Prefer `enum class`, `std::optional` for an optional value, and `std::filesystem::path` for paths.
- Do not use C-style casts. Choose `static_cast`, `const_cast` or `reinterpret_cast` only when its specific semantics are intended.

---

## Wide Strings & Unicode

- Use Win32 `W` APIs and `std::wstring` / `std::wstring_view` internally.
- Convert UTF-8 and UTF-16 only at boundaries, through one conversion helper using `MultiByteToWideChar` / `WideCharToMultiByte`.
- Use `wmain` for wide command-line arguments, or `CommandLineToArgvW` when parsing the process command line directly; release its allocation with RAII and `LocalFree`.

---

## Windows & Message Loop

- Use one registered window class per window type. Keep its procedure limited to dispatching to member handlers; store and retrieve `this` through `GWLP_USERDATA` at `WM_NCCREATE`.
- Check `GetMessageW` for both `-1` (error) and `0` (quit) before dispatching messages.
- Declare PerMonitorV2 DPI awareness in the application manifest.
- Own windows and GDI objects with RAII. Keep blocking work off the UI thread.

---

## Logging

Use `AppLogger` (`AppLogger.h` / `AppLogger.cpp`) as the only logging entry point. It wraps the chosen sink (`OutputDebugStringW`, stderr or a file) and owns the level and enable switch. Feature code does not call output APIs directly.

---

## Configuration & Input Validation

Gather related options in one configuration struct and validate them at the boundary. Treat command-line arguments, dropped paths and clipboard data as untrusted input.

---

## Testing

- Keep testable logic in plain C++ classes without Win32 types where practical. Put Win32 and COM access behind small interfaces so unit tests can use fakes.
- Use GoogleTest through CMake `FetchContent`, pin a release tag, and confirm the dependency version with the user before adding it.
- Register tests with `enable_testing()` and `gtest_discover_tests`. Put unit tests in `tests/`; put real COM/OLE or filesystem integration tests in `tests/integration/` and label them `integration` in CTest.

---

## Static Analysis & Formatting

Build with MSVC `/W4 /WX /permissive-`. Run MSVC Code Analysis (`/analyze`) through `tools/analyze.bat`, using a separate CMake preset or option. When installed, also support `clang-tidy`; keep a committed `.clang-format` when formatting is configured.

---

## CMake & Build Scripts

- Use out-of-source builds in the gitignored `build/` directory and provide `CMakePresets.json` for supported configurations.
- Locate Visual Studio's bundled CMake with `vswhere`, falling back to `cmake` on `PATH`. Keep that selection logic in one shared script used by all tool scripts.
- `tools/build.bat` configures and builds Release by default; an optional `Debug` argument selects Debug. Return CMake's exit code.
- `tools/run_tests.bat` builds, then runs `ctest --test-dir build -C <cfg> --output-on-failure -LE integration` with one line per test while running.
- `tools/run_integration_tests.bat` does the same with `-L integration`.
- Both test scripts capture `%ERRORLEVEL%` immediately after CTest and `exit /b` with that value.
- `tools/analyze.bat` builds with `/analyze` and uses `clang-tidy` when available; findings produce a non-zero exit code.
- Do not use `pause` or redirect test output to a temporary file. After these scripts are proven in a project, copy them to `cpp_setup_files/tools/` for reuse.

---

## Self-Describing Classes

When consumers need to inspect a class's searchable fields, have the class expose them, for example through a pure virtual `searchableFields() const` returning `std::vector<std::wstring_view>`. Consumers iterate that contract instead of maintaining their own field list.
