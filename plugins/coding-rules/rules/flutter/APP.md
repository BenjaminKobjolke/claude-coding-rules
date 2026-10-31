# Version
3

Increase this version number whenever this rule file changes.

# Flutter App Rules

Applies on top of `FLUTTER_RULES.md` when the project is a Flutter app (it has `lib/main.dart` and builds an APK/app bundle).

---

## Localization
<!-- steps: review, code -->

Use the `flutter_i18n_translations` library for multi-language support:
https://github.com/BenjaminKobjolke/flutter-i18n-translations

### Installation

Add to `pubspec.yaml`:

```yaml
dependencies:
  flutter_i18n_translations:
    git:
      url: https://github.com/BenjaminKobjolke/flutter-i18n-translations.git
```

Then run:

```bash
fvm flutter pub get
```

### Directory Structure

```
project/
├── assets/
│   └── i18n/
│       ├── en.json         # English (default)
│       ├── de.json         # German
│       └── languages.json  # Language metadata
├── lib/
│   ├── config/
│   │   ├── constants.dart
│   │   └── translation_keys.dart
│   └── main.dart
└── pubspec.yaml
```

### Configure Assets

In `pubspec.yaml`:

```yaml
flutter:
  assets:
    - assets/i18n/
```

### Translation File Format

Create `assets/i18n/en.json`:

```json
{
  "app": {
    "name": "My Application",
    "welcome": "Welcome, {name}!"
  },
  "nav": {
    "dashboard": "Dashboard",
    "settings": "Settings",
    "logout": "Logout"
  },
  "auth": {
    "login_title": "Login",
    "signin_subtitle": "Sign in to access your dashboard",
    "error": {
      "auth_failed": "Authentication failed. Please try again.",
      "rate_limited": "Too many attempts. Please try again later."
    }
  },
  "common": {
    "cancel": "Cancel",
    "save": "Save",
    "delete": "Delete",
    "edit": "Edit"
  }
}
```

Create `assets/i18n/languages.json`:

```json
{
  "en": "English",
  "de": "Deutsch"
}
```

### Initialization

In `main.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_i18n_translations/flutter_i18n_translations.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize localization
  final localizationService = LocalizationService();
  final languageCode = await determineSystemLanguage();
  await localizationService.load(languageCode);
  AppLocalizations.init(localizationService);

  runApp(const MyApp());
}
```

### Usage in Widgets

```dart
import 'package:flutter_i18n_translations/flutter_i18n_translations.dart';
import 'package:myapp/config/translation_keys.dart';

class MyWidget extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Simple translation
        Text(AppLocalizations.tr(TK.appName)),

        // With parameters
        Text(AppLocalizations.tr(TK.appWelcome,
          params: {'name': 'John'}
        )),

        // Get current language
        Text('Current: ${AppLocalizations.currentLanguage}'),
      ],
    );
  }
}
```

---

---

## Translation Key Naming Convention
<!-- steps: review, code -->

Use dot notation with logical grouping:

```
section.subsection.key

app.name               - Application info
nav.dashboard          - Navigation items
auth.login_title       - Authentication related
auth.error.auth_failed - Nested error messages
common.save            - Reusable UI elements
```

---

---

## Translation Keys as Constants
<!-- steps: review, code -->

Using raw strings like `AppLocalizations.tr('nav.dashboard')` is error-prone. Create a `TK` class with all keys as constants for IDE autocomplete and compile-time checking.

Create `lib/config/translation_keys.dart`:

```dart
// lib/config/translation_keys.dart
class TK {
  TK._();

  // App
  static const String appName = 'app.name';
  static const String appWelcome = 'app.welcome';

  // Navigation
  static const String navDashboard = 'nav.dashboard';
  static const String navSettings = 'nav.settings';
  static const String navLogout = 'nav.logout';

  // Auth
  static const String authLoginTitle = 'auth.login_title';
  static const String authSigninSubtitle = 'auth.signin_subtitle';
  static const String authErrorAuthFailed = 'auth.error.auth_failed';
  static const String authErrorRateLimited = 'auth.error.rate_limited';

  // Common
  static const String commonCancel = 'common.cancel';
  static const String commonSave = 'common.save';
  static const String commonDelete = 'common.delete';
  static const String commonEdit = 'common.edit';
}
```

Usage:

```dart
import 'package:myapp/config/translation_keys.dart';

// Instead of:
AppLocalizations.tr('nav.dashboard');

// Use:
AppLocalizations.tr(TK.navDashboard);
```

### Benefits

- IDE autocomplete for all translation keys
- Compile-time error if constant doesn't exist
- Easy to find all usages of a key
- Refactoring support

### Detecting unused or missing keys

Every Flutter project that uses the `TK` pattern **must** ship tooling that
detects all of the following:

1. TK constants whose i18n path does not exist (broken at runtime).
2. TK constants with no callers (dead Dart code).
3. i18n leaves with no TK constant pointing at them (orphan translations).
4. Raw `AppLocalizations.tr('literal')` calls that bypass the TK class.

Reference implementation: `tools/check_translation_keys.dart` +
`tools/check_translation_keys.bat`, shipped in `../flutter_setup_files/tools/`.
Run the audit whenever a TK constant or i18n key is added or removed, and
do not consider the change complete while the audit reports any issue. The
`--fix` flag auto-substitutes matchable raw literals **and** auto-creates
TK constants for raw literals that already have a matching i18n leaf;
remaining "broken" entries (raw literal whose i18n leaf is missing too)
must be resolved by hand.

Copy the whole set — the three scripts below plus `translation_key_audit.dart`
and the `.bat` wrappers. Only two constants in `check_translation_keys.dart`
are per-project: `_topKeyToClass` (top-level i18n key → owning `TK*` class)
and `_packageName`.

Companion tooling lives next to the audit script:

- `translation_key_audit.dart` — the shared detector every script imports.
  Layout, TK parsing, and the caller scan live here so a pruner can never
  drift from the audit and delete keys the audit considers live.
- `prune_unused_translation_keys.dart` — deletes dead TK constants from
  `lib/config/translation_keys/tk_*.dart`. Safe because the audit
  guarantees zero references. Drops only the declaration lines, leaving the
  rest of the file byte-identical.
- `prune_orphan_i18n_leaves.dart` — removes i18n leaves no caller
  references (TK or raw literal). When `tools/attributes_to_remove.json`
  exists, removed paths are merged into it so a translator batch can strip
  them from locale files the script does not own; projects without that
  batch never create the file.
- `split_translation_keys.dart` — when the project's `TK` class grows past
  ~500 lines, split it into one `TKModule` class per top-level i18n key
  group with a barrel re-export. The split keeps every existing
  `TK.foo`-style call site valid after a one-shot codemod.

Two detection rules exist because a naive audit reports false positives on
both, and a pruner acting on them destroys working code:

- **`...Prefix` constants.** A constant whose name ends in `Prefix` holds a
  partial path completed at runtime — `tr('${TKStats.weekStatusPrefix}$s')`.
  It is treated as matching any leaf below its value, so it is not "missing"
  and the leaves it reaches are not orphans.
- **The `_tr` wrapper.** Widgets commonly define
  `String _tr(String key) => AppLocalizations.tr(key);` and call `_tr(...)`.
  The raw-literal scan matches both spellings; matching only
  `AppLocalizations.tr` makes category 4 blind to most of the codebase.

Both i18n layouts are auto-detected at startup — modular
(`assets/i18n/modules.json` + `assets/i18n/<module>/<locale>.json`) and
single-file (`assets/i18n/<locale>.json`). Locales come from
`assets/i18n/languages.json`.

---

---

## Language Switching
<!-- steps: review, code -->

```dart
// Get available languages
final languages = AppLocalizations.getAvailableLanguages(); // ['de', 'en']

// Get language display name
final displayName = AppLocalizations.getLanguageName('de'); // "Deutsch"

// Switch language
await localizationService.load('de');
// Rebuild UI (e.g., restart app or use state management)
```

### Persisting Language Choice

```dart
import 'package:shared_preferences/shared_preferences.dart';

Future<void> changeLanguage(String languageCode) async {
  final prefs = await SharedPreferences.getInstance();
  await prefs.setString('language', languageCode);
  await localizationService.load(languageCode);
}

// On app start
final prefs = await SharedPreferences.getInstance();
final savedLanguage = prefs.getString('language');
final languageCode = savedLanguage ?? await determineSystemLanguage();
```

---

---

## Adding New Languages
<!-- steps: review, code -->

1. Copy `assets/i18n/en.json` to `assets/i18n/de.json`
2. Translate all values (keep keys identical)
3. Update `assets/i18n/languages.json`:

```json
{
  "en": "English",
  "de": "Deutsch"
}
```

---

---

## Project Structure

Standard Flutter mobile project structure:

```
project/
├── android/                    # Android platform files
├── ios/                        # iOS platform files
├── assets/
│   ├── i18n/                   # Translation files
│   └── images/                 # Image assets
├── lib/
│   ├── config/
│   │   ├── app_config.dart     # API URLs, timeouts
│   │   ├── constants.dart      # App constants
│   │   └── translation_keys.dart
│   ├── models/                 # Data models & ObjectBox entities
│   ├── repositories/           # Data access (ObjectBox CRUD)
│   ├── services/
│   │   ├── api_client.dart     # Dio HTTP client singleton
│   │   └── objectbox_service.dart  # ObjectBox initialization
│   ├── screens/                # Full-screen widgets
│   ├── widgets/                # Reusable widgets
│   ├── objectbox.g.dart        # Generated ObjectBox code
│   ├── objectbox-model.json    # Generated ObjectBox model
│   └── main.dart
├── test/                       # Unit and widget tests
├── tools/                      # Build scripts
│   ├── run_tests.bat
│   ├── build_debug.bat
│   └── build_release.bat
├── .fvmrc                      # FVM Flutter version
├── pubspec.yaml
├── install.bat
├── update.bat
└── README.md
```

---

---

## Project Setup Scripts

For projects that ship a Windows desktop installer, follow the optional
[Windows release guide](../flutter_setup_files/WINDOWS_RELEASES.md). It is not a
requirement for mobile-only projects.

Copy the setup batch files from the `../flutter_setup_files/` folder bundled with the
coding-rules plugin (next to this rules file).

### install.bat

Initial project setup:

- Checks if FVM is installed
- Runs `fvm install` to install Flutter version
- Runs `fvm flutter pub get` to install dependencies
- Runs tests to verify setup

### update.bat

Update all dependencies:

- Updates dependencies with `fvm flutter pub upgrade`
- Runs `fvm flutter analyze` for linting
- Runs tests to verify compatibility

### tools/build_debug.bat

Build debug APK:

- Runs `fvm flutter build apk --debug`
- Shows output location

### tools/build_release.bat

Build release APK:

- Runs `fvm flutter build apk --release`
- Shows output location

### Usage

```bash
# First time setup
install.bat

# Run tests
tools\run_tests.bat

# Build debug APK
tools\build_debug.bat

# Build release APK
tools\build_release.bat

# Update dependencies
update.bat
```

---

---

## App Icons

Whenever icons are involved — setting up a new project's launcher icon, replacing
existing art, adding a notification icon, or debugging one that renders wrong —
**read [`../flutter_setup_files/ICONS.md`](../flutter_setup_files/ICONS.md) first.**

Every Android app ships an **adaptive icon**: the launcher chooses its mask shape,
the app controls the foreground and background colour, and a legacy-only icon may
get a launcher-drawn plate — often a white circle.

House style is a **solid black background with simple white line art**. The guide
covers why (an adaptive icon's background layer must be opaque, so transparent is
not an option), the source-art layout, the `flutter_launcher_icons` config, and
the separate white-on-transparent notification icon Android needs — pointing a
notification at the launcher icon renders a featureless white blob in the status
bar.

Each project records its own paths and wiring in `docs/ICONS.md`.

---

---

## Local Demo Accounts and Screenshots

Use the `automated-application-screenshots` tool and its Flutter connector for screenshots and live screen iteration. Configure `tools/create_media/<app>.json` with a `live` block. Register screenshot screens in `lib/demos/live_screen_registry.dart` by name; use `name@section` for a target inside a screen. Register every new screen and tap-only state in the same change.

Copy the launcher kit from [`../flutter_setup_files/demo_screenshots/`](../flutter_setup_files/demo_screenshots/) and follow its README. The launcher seeds a fresh account on every app launch through the API demo seed route ([REST API Rules](../project_type/REST_API.md) → “Automated Client Test Accounts and Fixtures”), verifies identity through `/auth/me`, and passes `--dart-define=DEMO_ACCOUNT_TOKEN`. Never store the token. Do not add a separate setup script or stored token; the only one-time setup is the local API flag and `DEMO_ADMIN_PASSWORD` in ignored `tools/config.bat`.

Read `API_SERVER_URL` only outside release builds (`kReleaseMode ? live : String.fromEnvironment('API_SERVER_URL', defaultValue: live)`); release builds always use production. Allow cleartext HTTP only in `android/app/src/debug/AndroidManifest.xml`. The launcher refuses non-loopback API URLs. The Android emulator reaches the host computer at `10.0.2.2`.

Record setup, screen names and required seed states in `docs/DEMOS_RECORD.md`.

---

---

## Standard App Dependencies

```yaml
dependencies:
  flutter:
    sdk: flutter

  # Localization
  flutter_i18n_translations:
    git:
      url: https://github.com/BenjaminKobjolke/flutter-i18n-translations.git

  # HTTP
  dio: ^5.9.0

  # Database
  objectbox: ^5.1.0

  # Utilities
  path_provider: ^2.1.0
  path: ^1.9.0
  shared_preferences: ^2.2.0

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^3.0.0

  # ObjectBox code generation
  objectbox_generator: ^5.1.0
  build_runner: ^2.4.0
```

---

---

## Sensitive Data (.env)

Never commit API keys, secrets, or credentials to version control. Use `.env` files for sensitive values:

1. Add `flutter_dotenv` to `pubspec.yaml`:

```yaml
dependencies:
  flutter_dotenv: ^5.1.0
```

2. Create a `.env` file in the project root:

```
API_KEY=your_secret_key_here
API_SECRET=your_secret_here
```

3. Add `.env` to `.gitignore`:

```
.env
```

4. Load in `main.dart`:

```dart
import 'package:flutter_dotenv/flutter_dotenv.dart';

void main() async {
  await dotenv.load(fileName: ".env");
  // Access values: dotenv.env['API_KEY']
  runApp(const MyApp());
}
```

5. Provide a `.env.example` file (committed) with placeholder values so other developers know which keys are required.

---

---

## Required Batch Files

Every app must include these batch files:

- `install.bat` - In the root directory, initial project setup
- `update.bat` - In the root directory, update dependencies
- `tools/build_debug.bat` - Builds debug APK
- `tools/build_release.bat` - Builds release APK

---

---

## State Management (Cubit)
<!-- steps: review, code -->

Use **Cubit** from the `flutter_bloc` package for state management. Cubit is the recommended approach for all Flutter projects.

### Why Cubit?

- **Simpler than BLoC**: No events, just methods that emit states
- **Predictable**: Clear separation between UI and business logic
- **Testable**: Easy to unit test state changes
- **Scalable**: Works for simple screens and complex apps alike
- **Less boilerplate**: Compared to full BLoC pattern

### Installation

```yaml
dependencies:
  flutter_bloc: ^8.1.0
  equatable: ^2.0.5  # For state comparison
```

```bash
fvm flutter pub get
```

### Basic Example

**State class** (`lib/cubits/counter_state.dart`):

```dart
import 'package:equatable/equatable.dart';

class CounterState extends Equatable {
  final int count;
  final bool isLoading;

  const CounterState({
    this.count = 0,
    this.isLoading = false,
  });

  CounterState copyWith({int? count, bool? isLoading}) {
    return CounterState(
      count: count ?? this.count,
      isLoading: isLoading ?? this.isLoading,
    );
  }

  @override
  List<Object?> get props => [count, isLoading];
}
```

**Cubit class** (`lib/cubits/counter_cubit.dart`):

```dart
import 'package:flutter_bloc/flutter_bloc.dart';
import 'counter_state.dart';

class CounterCubit extends Cubit<CounterState> {
  CounterCubit() : super(const CounterState());

  void increment() {
    emit(state.copyWith(count: state.count + 1));
  }

  void decrement() {
    emit(state.copyWith(count: state.count - 1));
  }

  Future<void> loadFromApi() async {
    emit(state.copyWith(isLoading: true));
    // Simulate API call
    await Future.delayed(const Duration(seconds: 1));
    emit(state.copyWith(count: 42, isLoading: false));
  }
}
```

**Usage in Widget**:

```dart
import 'package:flutter_bloc/flutter_bloc.dart';
import '../cubits/counter_cubit.dart';
import '../cubits/counter_state.dart';

class CounterScreen extends StatelessWidget {
  const CounterScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocProvider(
      create: (_) => CounterCubit(),
      child: const CounterView(),
    );
  }
}

class CounterView extends StatelessWidget {
  const CounterView({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Counter')),
      body: BlocBuilder<CounterCubit, CounterState>(
        builder: (context, state) {
          if (state.isLoading) {
            return const Center(child: CircularProgressIndicator());
          }
          return Center(
            child: Text('Count: ${state.count}'),
          );
        },
      ),
      floatingActionButton: Column(
        mainAxisAlignment: MainAxisAlignment.end,
        children: [
          FloatingActionButton(
            onPressed: () => context.read<CounterCubit>().increment(),
            child: const Icon(Icons.add),
          ),
          const SizedBox(height: 8),
          FloatingActionButton(
            onPressed: () => context.read<CounterCubit>().decrement(),
            child: const Icon(Icons.remove),
          ),
        ],
      ),
    );
  }
}
```

### Project Structure

```
lib/
├── cubits/
│   ├── counter_cubit.dart
│   ├── counter_state.dart
│   ├── auth_cubit.dart
│   └── auth_state.dart
├── screens/
│   └── counter_screen.dart
└── main.dart
```

### Key Patterns

- **One Cubit per feature/screen**: Keep cubits focused
- **Immutable states**: Always use `copyWith` pattern
- **Equatable**: Use for efficient state comparison
- **BlocProvider**: Provide cubits at the widget level
- **BlocBuilder**: Rebuild UI when state changes
- **BlocListener**: Handle side effects (navigation, snackbars)

---

---

## HTTP Communication (Dio)
<!-- steps: review, code -->

Use Dio for all HTTP communication.

### Installation

```bash
fvm flutter pub add dio
```

Add to `pubspec.yaml`:

```yaml
dependencies:
  dio: ^5.9.0
```

### API Client Singleton

Create `lib/services/api_client.dart`:

```dart
import 'package:dio/dio.dart';
import 'package:myapp/config/app_config.dart';

class ApiClient {
  ApiClient._();

  static final Dio _dio = Dio(
    BaseOptions(
      baseUrl: AppConfig.apiBaseUrl,
      connectTimeout: AppConfig.requestTimeout,
      receiveTimeout: AppConfig.requestTimeout,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    ),
  );

  static Dio get instance => _dio;
}
```

### Usage Example

```dart
import 'package:myapp/services/api_client.dart';

class UserService {
  final Dio _dio = ApiClient.instance;

  Future<Map<String, dynamic>> getUser(int id) async {
    final response = await _dio.get('/users/$id');
    return response.data;
  }

  Future<Map<String, dynamic>> createUser(Map<String, dynamic> data) async {
    final response = await _dio.post('/users', data: data);
    return response.data;
  }
}
```

### Error Handling

```dart
import 'package:dio/dio.dart';

Future<void> fetchData() async {
  try {
    final response = await ApiClient.instance.get('/data');
    // Handle success
  } on DioException catch (e) {
    switch (e.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.receiveTimeout:
        // Handle timeout
        break;
      case DioExceptionType.badResponse:
        final statusCode = e.response?.statusCode;
        // Handle HTTP errors (400, 401, 404, 500, etc.)
        break;
      case DioExceptionType.connectionError:
        // Handle no internet
        break;
      default:
        // Handle other errors
        break;
    }
  }
}
```

### Mobile Data Budget (BINDING)

An app that polls keeps downloading on every tick even when the server answer did not change, and
holds its data in memory only. The server half of this contract is
`project_type/REST_API.md` -> "Response Size and Mobile Data"; these are the client half.

- **Ask the API for exactly what the screen shows.** Load a screen's initial API data with one
  call, reusing a list or detail operation when sufficient and requesting an overview endpoint
  when several datasets are needed. Never call a detail endpoint once per list item (N+1). Read
  slim lists (`fields=slim`), filter server-side, fetch full detail only when a detail screen
  opens, and send the last offset for growing logs and append. If the API lacks the required
  slim/overview/offset endpoint or a sort, filter or paging parameter, request it from the API
  project instead of filtering client-side.
- **Lists are paged and sorted by the API.** `COMMON_RULES.md` -> "API Clients: the API Sorts,
  Filters and Pages" is binding here. Build the list with `ListView.builder`, request the next
  page (`limit`/`offset`) when the last rows scroll into view, and start again at the first page
  when the sort order or a filter changes. A sort menu sends the `sort` parameter; it never
  reorders the rows held in memory. Page state lives in the provider, not in the widget.
  See `project_type/REST_API.md` -> "Screen Overview Endpoints" (an app-only project may not
  install `REST_API.md`, so the client rule stays here).
- **Conditional GET in the client.** A Dio interceptor in the `ApiClient` singleton — registered
  with `_dio.interceptors.add(EtagInterceptor(box))` the same way `IN_APP_DEBUGGER.md` adds
  the Logarte interceptor (switch the inline `_dio` above to its `_createDio()` form) — stores
  `ETag` + body per request URL in an ObjectBox entity (`etag`, `body`; `## Database (ObjectBox)` above is already a
  standard dependency, so no cache package is added), sends `If-None-Match` on the next `GET`, and
  treats `304` as "use the cached body". Echo the tag **verbatim**, including a `-gzip` suffix. A
  `304` must not trigger "new data" side effects (sounds, notifications, animations). On a network
  failure serve the cache but forget the tag. `validateStatus` must accept `304` — Dio's default
  accepts only `2xx`, so a `304` would otherwise surface as an error:

  ```dart
  class EtagInterceptor extends Interceptor {
    EtagInterceptor(this._box);
    final Box<CachedResponse> _box; // ObjectBox entity: id, url, etag, body

    CachedResponse? _cached(String url) {
      final query = _box.query(CachedResponse_.url.equals(url)).build();
      try {
        return query.findFirst();
      } finally {
        query.close();
      }
    }

    @override
    void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
      final tag = _cached(options.uri.toString())?.etag;
      if (tag != null && options.method == 'GET') {
        options.headers['If-None-Match'] = tag; // verbatim, -gzip suffix included
      }
      handler.next(options);
    }

    @override
    void onResponse(Response response, ResponseInterceptorHandler handler) {
      final url = response.requestOptions.uri.toString();
      if (response.statusCode == 304) {
        final cached = _cached(url)!;              // a 304 carries no body
        response.statusCode = 200;
        response.headers.value('etag', cached.etag); // restore the tag for the next call
        response.data = jsonDecode(cached.body);
      } else if (response.statusCode == 200 && response.headers.value('etag') != null) {
        _box.put(CachedResponse(
            url: url, etag: response.headers.value('etag')!, body: jsonEncode(response.data)));
      }
      handler.next(response);
    }

    @override
    void onError(DioException err, ErrorInterceptorHandler handler) {
      final cached = _cached(err.requestOptions.uri.toString());
      if (cached == null || err.response != null) {
        handler.next(err);
        return;
      }
      _box.remove(cached.id); // forget the tag: the next call fetches without If-None-Match
      handler.resolve(Response(
          requestOptions: err.requestOptions, statusCode: 200, data: jsonDecode(cached.body)));
    }
  }
  ```
- **gzip comes free.** `dart:io`'s `HttpClient` (Dio's default adapter on mobile) sends
  `Accept-Encoding: gzip` and decompresses the response; never disable it.
- **Polling is foreground-only and bounded.** Every timer/poll loop checks
  `WidgetsBinding.instance.lifecycleState == AppLifecycleState.resumed` before each fetch, stops on
  pause/dispose, and has an overall timeout. Inject `bool Function() isForeground` so a test can
  drive the lifecycle. User-settable refresh intervals live in `AppConfig` (`FLUTTER_RULES.md` → `Centralize configuration`) with a
  data-safe minimum (15 s) and default (30 s); clamp stored values below the minimum. Screen-awake/
  kiosk modes still count as foreground, so the minimum matters.
- **Resume reloads only what is visible.** On `resumed`, reload the current tab plus any cheap
  overview; mark the other tabs stale and let them reload in their own `onSelected`.
- **Images: disk cache + thumbnails.** Cache image bytes on disk keyed by image id under
  `path_provider`'s cache directory (`path_provider` is already a standard dependency;
  `LIBRARIES.md` lists no image-cache package, so add none), size-capped — the bytes never change.
  Use a thumbnail for list/preview and fetch full size only when the image is opened. A
  memory-only cache refetches on every screen open.
- **Measure.** Android Settings -> Apps -> <app> -> Mobile data splits foreground and background
  usage; a high background share means a poller ignores the lifecycle.
- **Test it:** the interceptor (no tag on the first call, tag sent after `200`, `304` returns the
  cached body, a network failure serves the cache and clears the tag); a poller skips fetches while
  backgrounded and resumes; the interval clamp.

---

---

## Database (ObjectBox)
<!-- steps: review, code -->

Use ObjectBox for local persistence.

### Installation

Add to `pubspec.yaml`:

```yaml
dependencies:
  objectbox: ^5.1.0

dev_dependencies:
  objectbox_generator: ^5.1.0
  build_runner: ^2.4.0
```

Run:

```bash
fvm flutter pub get
fvm dart run build_runner build
```

### Entity Example

Create `lib/models/user.dart`:

```dart
import 'package:objectbox/objectbox.dart';

@Entity()
class User {
  @Id()
  int id = 0;

  String name;
  String email;

  @Property(type: PropertyType.date)
  DateTime createdAt;

  User({
    this.id = 0,
    required this.name,
    required this.email,
    DateTime? createdAt,
  }) : createdAt = createdAt ?? DateTime.now();
}
```

### ObjectBox Initialization

Create `lib/services/objectbox_service.dart`:

```dart
import 'package:path_provider/path_provider.dart';
import 'package:path/path.dart' as p;
import '../objectbox.g.dart';

class ObjectBoxService {
  ObjectBoxService._();

  static Store? _store;

  static Store get store {
    if (_store == null) {
      throw Exception('ObjectBox not initialized. Call init() first.');
    }
    return _store!;
  }

  static Future<void> init() async {
    if (_store != null) return;

    final dir = await getApplicationDocumentsDirectory();
    final dbPath = p.join(dir.path, 'objectbox');
    _store = await openStore(directory: dbPath);
  }

  static void close() {
    _store?.close();
    _store = null;
  }
}
```

Initialize in `main.dart`:

```dart
void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize ObjectBox
  await ObjectBoxService.init();

  // Initialize localization
  // ...

  runApp(const MyApp());
}
```

### Basic CRUD Operations

```dart
import 'package:myapp/models/user.dart';
import 'package:myapp/services/objectbox_service.dart';
import '../objectbox.g.dart';

class UserRepository {
  final Box<User> _box = ObjectBoxService.store.box<User>();

  // Create or Update
  int put(User user) {
    return _box.put(user);
  }

  // Get by ID
  User? get(int id) {
    return _box.get(id);
  }

  // Get all
  List<User> getAll() {
    return _box.getAll();
  }

  // Delete
  bool delete(int id) {
    return _box.remove(id);
  }

  // Query
  List<User> findByName(String name) {
    final query = _box.query(User_.name.equals(name)).build();
    final results = query.find();
    query.close();
    return results;
  }
}
```

---

---

## In-App Debugger (Logarte)
<!-- steps: review, code -->

For debugging network requests and viewing logs directly on the device, use Logarte.

See the detailed integration guide: [In-App Debugger Documentation](IN_APP_DEBUGGER.md)

**Requirements:**
- Must be accessible from the Settings screen
- Must be enable/disable via `AppConfig.enableLogarte`

**Key features:**
- Network request logging (automatic with Dio interceptor)
- Navigation event logging
- Searchable log viewer
- Password protection for release builds
- Log sharing and export

---

---

## Dependency Injection

Use `GetIt` for service location and dependency injection. Register services at app startup and
retrieve them via `GetIt.instance`. This keeps services decoupled and testable.

---

---

## Respect System Insets (SafeArea)

Screen-level content must never render underneath the system UI — the status bar,
the notch/cutout, or the bottom navigation/gesture bar. Otherwise bottom controls
(a Save button, an FAB, the last list item) sit partly behind the Android nav bar
and are hard or impossible to tap.

- **Wrap the `Scaffold` `body` in a `SafeArea`** for any screen whose content can
  reach a screen edge — especially scrollable bodies (`ListView`, `SingleChildScrollView`,
  `Column` with a bottom button). The `AppBar` already handles the top inset; the
  bottom inset is the one that bites.

  ```dart
  // Anti-pattern: bottom button scrolls under the nav bar
  body: ListView(padding: const EdgeInsets.all(16), children: [...]),

  // Correct: SafeArea insets the scroll view above the system bars
  body: SafeArea(
    child: ListView(padding: const EdgeInsets.all(16), children: [...]),
  ),
  ```

- `EdgeInsets` padding is **not** a substitute — a hardcoded padding value does not
  track the device's actual inset (varies by phone, gesture vs button nav, landscape).
- **Don't double-inset.** A `Scaffold` `appBar` already consumes the top inset; if you
  keep `SafeArea` defaults (`top: true`) under an `AppBar` it's harmless (inset is
  already zero there), but don't also add manual top padding on top of it.
- For a body behind a keyboard, `Scaffold.resizeToAvoidBottomInset` (default `true`)
  handles the keyboard; `SafeArea` handles the persistent system bars. They are
  separate concerns — keep both defaults on unless you have a reason not to.
- Full-bleed content (a background image, an edge-to-edge map) is the deliberate
  exception: opt out per-edge (`SafeArea(bottom: false, ...)`) rather than dropping
  `SafeArea` entirely, so only the intended edge bleeds.

---
