# Version
16

Increase this version number whenever this rule file changes.

# Flutter Rules (FVM + Mobile)

See `COMMON_RULES.md` for rules that apply to all languages.

## Optional rule files

- `flutter/APP.md` — Flutter apps: localization, Cubit, Dio, ObjectBox, Logarte, app icons, project structure and APK build scripts. Skip it for library/plugin packages.
- Run `/coding-rules:apply` to add it when the project is an app.

## Core principles

1. Flutter's core principle: Composition over inheritance - small, focused widgets
2. Testability: Each widget can be tested in isolation
3. Single Responsibility: One widget = one job
4. Reusability: Components can be used elsewhere
5. Readability: Smaller files (~100-200 lines) are easier to maintain
6. Follow SOLID principles (Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion)

## Documentation Comments
<!-- steps: review, code -->

Use `///` doc comments on all public classes, methods, and properties:

```dart
/// Service responsible for user authentication.
class AuthService {
  /// Attempts to log in with the given [email] and [password].
  ///
  /// Returns the authenticated [User] on success.
  /// Throws [AuthException] if credentials are invalid.
  Future<User> login(String email, String password) async {
    // ...
  }
}
```

Rules:
- Every public class, method, and property must have a `///` comment
- Use `[paramName]` to reference parameters in doc comments
- Keep descriptions concise; one sentence for simple members
- Do not use `//` block comments for documentation

---

## When to Use `part` / `part of`

Prefer normal `import` / `export` for all hand-written code. Do **not** use `part`
to split large classes, organize features into folders, or share utilities — it
hides dependencies, weakens encapsulation (all `part` files share one private
scope), and makes refactoring harder.

Use `part` only when:

1. **Code generation requires it** — the common modern case. Generators emit into
   `*.g.dart` / `*.freezed.dart` files included via `part`:

   ```dart
   import 'package:json_annotation/json_annotation.dart';

   part 'user.g.dart';

   @JsonSerializable()
   class User {
     final String name;
     User(this.name);
     factory User.fromJson(Map<String, dynamic> json) => _$UserFromJson(json);
     Map<String, dynamic> toJson() => _$UserToJson(this);
   }
   ```

   Applies to `freezed`, `json_serializable`, `objectbox` (`objectbox.g.dart`), and
   similar — see the JSON Serialization section and, for apps, the ObjectBox section in
   `flutter/APP.md`.

2. **One tightly-coupled library** (rare) — several files that genuinely form a
   single library and must share library-private (`_`) members.

| Scenario                                   | Use `part`? |
| ------------------------------------------ | ----------- |
| Application / widget code                  | No          |
| Splitting a large class across files       | No          |
| Organizing features or modules             | No          |
| Generated files (`freezed`, `*.g.dart`)    | Yes         |
| One tightly-coupled library impl           | Sometimes   |

Rule of thumb: **if you write the code, use imports/exports; if a generator
requires it, use `part`.**

---

## Mixins

Mixins share behavior across classes that do **not** share an inheritance chain.
Reach for a mixin only when composition (a plain helper class injected via `GetIt`,
or a field) does not fit — Flutter favors composition over inheritance, and a
mixin is a form of inheritance.

### Rules

1. **Use the `mixin` keyword, never a `class` as a mixin.** A `mixin` cannot be
   instantiated or extended, which documents intent and prevents misuse. Use
   `mixin class` only in the rare case a type must serve as both — never by default.

2. **Constrain with `on` whenever the mixin depends on a host type.** This both
   restricts where the mixin can be applied and grants typed access to the host's
   members. Prefer `mixin AnalyticsLogging on State` over an unconstrained mixin
   that assumes a `context`.

3. **Keep mixins stateless.** All `part`/mixin members live in the host's scope, so
   a mutable field in a mixin silently couples to — and can collide with — the
   host's fields. If state is unavoidable, prefix fields with `_`, document the
   ownership, and keep it to one field.

4. **One capability per mixin (single responsibility).** A mixin named for a
   behavior (`Disposable`, `Validatable`) is good; a `UtilsMixin` grab-bag is not.

5. **Name by capability**, ending in `-able` or with a `Mixin` suffix, matching the
   existing `SearchableMixin` convention. Be consistent within a project.

6. **Only call `super.method()` when the `on` constraint guarantees it exists.**
   Mixins are linearized left-to-right; later mixins override earlier ones. Know the
   apply order when overriding lifecycle methods (e.g. `initState`/`dispose`).

7. **Mark host-only members `@protected`** and give every public member a `///`
   doc comment, per the Documentation Comments rules.

8. **Do not use a mixin to share code that could be a standalone service.** If the
   behavior owns state or has dependencies, make it a class and inject it with
   `GetIt` — see Dependency Injection.

Legit Flutter framework mixins — `TickerProviderStateMixin`,
`AutomaticKeepAliveClientMixin`, `WidgetsBindingObserver` — model all of the above:
host-constrained, behavior-focused, named by capability.

### When to use a mixin vs. the alternative

| Need                                                    | Use                          |
| ------------------------------------------------------- | ---------------------------- |
| Share stateless behavior across unrelated classes       | `mixin`                      |
| Add behavior that needs a specific host (`State`, etc.) | `mixin ... on HostType`      |
| Share behavior that owns state or dependencies          | Class + `GetIt` (composition)|
| Define a contract only (no implementation)              | `abstract interface class`   |
| Reuse one widget's look/structure                       | Compose widgets, not a mixin |

Rule of thumb: **a mixin adds behavior, not state.** If you find yourself storing
data in a mixin, it should probably be a class you inject instead.

---

## Flutter Version Management
<!-- steps: code -->

Use FVM (Flutter Version Manager) for all projects. Create `.fvmrc` in the project root:

```json
{
  "flutter": "3.44.0"
}
```

Latest verified stable as of 2026-05-26. Confirm with `fvm releases --channel stable` for new projects.

All Flutter commands should be prefixed with `fvm`:

```bash
fvm flutter pub get
fvm flutter run
fvm flutter build apk
```

---

## Approved Libraries

Before implementing any new feature, **check
[`flutter_setup_files/LIBRARIES.md`](flutter_setup_files/LIBRARIES.md)** — it lists the approved
third-party libraries, their confirmed versions, and a reference implementation for each.

- If a listed library already covers the job, use it. Do not hand-roll an equivalent and do not
  introduce a competing package for the same concern.
- If nothing listed covers it, choose the version as `COMMON_RULES.md` → "Confirm Dependency
  Versions" describes (latest compatible stable, ask only on a real tradeoff), then add the
  library to `LIBRARIES.md` with a pointer to the first real implementation, so the next project
  picks it up automatically.

This is the same "check before you build" rule as `COMMON_RULES.md` → "Reusable Tooling",
applied to dependencies instead of scripts.

---

## Pin Android Dependencies Declared as Version Ranges
<!-- steps: review, code -->

Some plugins' Android SDKs declare dependencies as **version ranges** (seen: OneSignal Android
SDK 5.10.0 via `onesignal_flutter` 5.6.10). For a range Gradle must list the available versions
on Google Maven (`dl.google.com`) and caches that list for only 24 hours; an exact version
resolves from the local Gradle cache with no network. A build with range-declared dependencies
therefore needs Google Maven to answer about once a day. When it does not, the release build
fails in `:app:mergeReleaseNativeLibs` with `Could not resolve ...{require [...]}` and
`Repository Google is disabled due to earlier error below` — with no code change and every
artifact already cached.

**The app's Gradle build forces every range-declared Android module to the version it already
resolves to.**

Find the ranges, from `android/`:

```bash
gradlew :app:dependencies --configuration releaseRuntimeClasspath --console=plain
```

- Every `{require [...]}` line is a range (a bare `[1.0, 2.0)` or `1.+` request is the same
  thing); the version after `->` is the one to pin.
- The command exits 0 even when resolution fails. `FAILED` lines are the signal, never the
  exit code.
- Add `--offline` to read the report from the Gradle cache while Google Maven does not answer.

Pin them in `android/build.gradle.kts`, as its own block after the `allprojects { repositories
{ ... } }` block:

```kotlin
// OneSignal 5.10.0 declares these as version ranges. Gradle re-lists a range on Google Maven
// once its 24-hour cache expires, so the build failed whenever dl.google.com did not answer,
// although every artifact was already cached. Forcing the versions the ranges resolved to
// removes that request. force also holds a module down, so after upgrading onesignal_flutter
// or any plugin that needs one of these: remove this block, run
// `gradlew :app:dependencies --configuration releaseRuntimeClasspath`, and pin what each
// `{require [...]}` line resolves to.
allprojects {
    configurations.configureEach {
        resolutionStrategy.force(
            "com.google.firebase:firebase-messaging:24.0.0",
            "androidx.work:work-runtime:2.8.1",
        )
    }
}
```

A Groovy `android/build.gradle` takes the same block with single-quoted strings and no
trailing comma.

Rules:

- **Pin what the range resolves to in this app, never a version copied from another app.**
  Other plugins can raise a module above the declaring plugin's range (seen: `androidx.browser`
  at 1.9.0 through `url_launcher_android`, above OneSignal's `[1.0.0, 1.3.99]`).
- **Use `resolutionStrategy.force`, not `eachDependency`.** Replacing only the range requests
  through `eachDependency` still sends a request to `dl.google.com`.
- **The pins carry a comment** naming the declaring plugin and version, why the pins exist, and
  how to re-derive them, as in the example.
- **Re-derive after upgrading** the declaring plugin or any plugin that needs a pinned module:
  a forced version also holds the module down. Remove the block, run the report, pin again.
- The pins remove only the daily version lookup. A library that was never downloaded (after a
  package or Flutter upgrade) still needs Google Maven once.

---

# Essential Rules

## 1) Use `pubspec.yaml` as the single source of truth
<!-- steps: review, code -->

Keep all dependencies and configuration in `pubspec.yaml`.

Recommended baseline:

- Flutter/Dart SDK version constraints
- Dependencies managed via `fvm flutter pub add ...`
- Lock file committed: `pubspec.lock`

---

## 2) Enforce linting and formatting
<!-- steps: review, code -->

Use the standard Flutter analyzer:

```bash
fvm flutter analyze
fvm dart format lib/
```

Configure `analysis_options.yaml`:

```yaml
include: package:flutter_lints/flutter.yaml

linter:
  rules:
    prefer_const_constructors: true
    prefer_const_declarations: true
    avoid_print: true
```

---

## 3) Centralize configuration

No "magic values" in code. Use a config class:

```dart
// lib/config/app_config.dart
class AppConfig {
  AppConfig._();

  static const String apiBaseUrl = 'https://api.example.com';
  static const Duration requestTimeout = Duration(seconds: 30);
  static const bool debugMode = true;
}
```

---

## 4) Logging & Error Handling

### Logging

Never use `print()` for logging. Use `dart:developer` or the `logger` package:

```dart
import 'dart:developer' as developer;

// Simple log
developer.log('User loaded successfully', name: 'UserService');

// Log with error
developer.log('Failed to load user', name: 'UserService', error: e, stackTrace: stackTrace);
```

Or with the `logger` package:

```yaml
dependencies:
  logger: ^2.0.0
```

```dart
import 'package:logger/logger.dart';

final logger = Logger();

logger.d('Debug message');
logger.i('Info message');
logger.w('Warning message');
logger.e('Error message', error: e, stackTrace: stackTrace);
```

#### Central Logger Class

Route all logging through one class named **`AppLogger`** (`app_logger.dart`). Never call
`print()`, `developer.log`, or the `logger` package directly from feature code — only
`AppLogger` wraps them. This gives a single enable/level toggle (e.g. `AppConfig.logLevel`)
without touching call sites.

```dart
AppLogger.d('Debug message');
AppLogger.i('User loaded', name: 'UserService');
AppLogger.e('Failed to load user', error: e, stackTrace: stackTrace);
```

### Error Handling

- Use try-catch for all async and critical operations
- Display user-friendly error messages in the UI (never show raw exceptions)
- Log errors with context (class name, method name, relevant parameters)

```dart
Future<void> loadUser(int userId) async {
  try {
    final user = await _userService.getUser(userId);
    emit(state.copyWith(user: user));
  } catch (e, stackTrace) {
    AppLogger.e('Failed to load user $userId', error: e, stackTrace: stackTrace);
    // Map the exception to this package's error representation.
  }
}
```

---

## 5) Tests are mandatory

Use Flutter test framework:

```bash
fvm flutter test
```

Rules:

- Unit tests for services and business logic
- Widget tests for UI components
- No network in unit tests (use mocks)
- Run tests in CI on every push

---


### tools/run_tests.bat

Run the test suite:

- Runs `fvm flutter test --reporter expanded` directly, so one line per test
  appears while the tests run and the script captures flutter test's own exit code
- Shows pass/fail summary based on that captured exit code, then `exit /b`s with it
- Never redirect the run into a temp file and print it afterwards: the script is
  then silent for the whole run and a hanging test looks like a slow suite
- If you add noise filtering for third-party log spam, filter live with the
  PowerShell line from the comment in the bat (it ends in `exit $LASTEXITCODE`) -
  never pipe `fvm flutter test` straight into `findstr`. The pipe's exit code
  becomes the filter's exit code, not flutter test's, so a real failure can
  silently read as a pass (or vice versa). `findstr` also has a ~8191-char
  line-length limit and errors on long lines.

## JSON Serialization

Use `freezed` + `json_serializable` for type-safe API models. This generates immutable data
classes with `fromJson`/`toJson` methods, `copyWith`, and equality out of the box.

---

## Widget Rebuild Optimization

Minimize unnecessary widget rebuilds to maintain smooth performance:

- Use `const` constructors wherever possible
- Extract subtrees into separate widgets to limit rebuild scope
- Avoid building large widget trees inside a single `build` method
- Use `BlocSelector` or `BlocBuilder` with `buildWhen` to rebuild only when relevant state changes

---

## Never Let a Widget Take Infinite Height in a Scroll View

A scroll view hands its children **unbounded** constraints on the scroll axis
(`maxHeight: infinity`). Greedy widgets resolve that by taking everything they are
offered, so a widget that is correct inside a `Column` becomes an infinite-height
child inside a `ListView`.

The damage lands on a **different widget than the buggy one**: once a child reports
infinite height, the list stops laying out and *every sibling below it is never
built*. Those siblings produce no exception, no log, and no error widget — they
simply do not exist. You end up reading the missing widget's code, which is correct.

The greedy widgets, and what they do under unbounded constraints:

| Inside a scroll view | Result |
|---|---|
| `Row(crossAxisAlignment: CrossAxisAlignment.stretch)` | children sized to `maxHeight` → **infinite** |
| `height: double.infinity`, `SizedBox.expand` | infinite |
| `Expanded` / `Flexible` / `Spacer` in a vertical parent | error |
| `ListView` / `GridView` without `shrinkWrap: true` | error |

```dart
// Anti-pattern: fine in a Column, fatal in a ListView — and it silently
// deletes every sibling below it.
Row(
  crossAxisAlignment: CrossAxisAlignment.stretch,
  children: [Expanded(child: _Card()), Expanded(child: _Card())],
)

// Correct: IntrinsicHeight bounds the row, equal-height children preserved
IntrinsicHeight(
  child: Row(
    crossAxisAlignment: CrossAxisAlignment.stretch,
    children: [Expanded(child: _Card()), Expanded(child: _Card())],
  ),
)
```

Rules:

- **Only a `Row` is at risk from `stretch`.** A `Column`'s cross axis is horizontal,
  which is bounded — `CrossAxisAlignment.stretch` on a `Column` is fine.
- **Bound it explicitly**: `IntrinsicHeight`, a fixed `SizedBox(height:)`, or
  `AspectRatio`. Prefer `IntrinsicHeight` when children must match heights.
- **Run every new screen once in a debug build before shipping a release APK.**
  Debug asserts on this by name — `BoxConstraints forces an infinite height` — and
  points at the offending widget. Release strips the assert and the failure goes
  completely silent, which is what makes this class of bug expensive.
- **Widget-test the composition, not just the widget.** Pump the widget in a
  `ListView` *with a sibling after it* and assert both a finite height and that the
  sibling was built. A widget tested alone passes while the screen is broken.

  ```dart
  await tester.pumpWidget(MaterialApp(home: Scaffold(
    body: ListView(children: const [MyRow(), Text('below')]),
  )));
  expect(tester.takeException(), isNull);
  expect(tester.getSize(find.byType(MyRow)).height.isFinite, isTrue);
  expect(find.text('below'), findsOneWidget); // never built if MyRow is infinite
  ```

- **Suspect the siblings' constraints before the missing widget's own code.** A
  widget that renders nothing and logs nothing is usually a victim, not the cause.
- The default `ErrorWidget` sizes to `constraints.biggest`, so a *crash* in a list
  child produces the same infinite blank block. A custom `ErrorWidget.builder` with a
  bounded height and the exception text turns that into a visible, readable failure.

---

## Self-Describing Classes

Implement the common "Self-Describing Classes" rule using an abstract class or mixin.

```dart
abstract class Searchable {
  /// Returns a map of field name to field value for all searchable fields.
  Map<String, String> getSearchableFields();
}

class Customer implements Searchable {
  final String name;
  final String email;
  final String phone;

  const Customer({required this.name, required this.email, required this.phone});

  @override
  Map<String, String> getSearchableFields() {
    return {'name': name, 'email': email, 'phone': phone};
  }
}
```

Alternatively, use a mixin when classes already have an inheritance hierarchy
(follow the [Mixins](#mixins) rules):

```dart
mixin SearchableMixin {
  Map<String, String> getSearchableFields();
}
```

---

## Mixins, Widgets, and Injected Services (Coupling)

Reinforces core principle #1 (Composition over inheritance) and
**Inject Collaborators, Don't Fold Dependencies In** in `COMMON_RULES.md`.

- **`with SomeMixin` folds the mixin's dependencies into the widget/class.** Stacking behavior
  mixins spreads their imports across the host. Prefer a child widget or an injected service
  (get_it / Provider / Riverpod) for anything that carries dependencies; keep mixins for small,
  dependency-free behavior.
- **A god `build()` method is a coupling sink.** A widget whose `build()` wires many services and
  passes values down through several constructor layers (prop-drilling) depends on everything it
  drills through. Extract child widgets, and pass a single config object or read shared state via
  `InheritedWidget` / a provider instead of threading many parameters.

```dart
// Anti-pattern: one widget builds everything and drills props through 3 layers
// Correct: extract InvoiceHeader / InvoiceActions child widgets; inject services via provider,
//          pass an InvoiceViewConfig value object instead of a dozen constructor params
```
