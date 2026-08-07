# In-App Debugger (Logarte) - Integration Guide

Use [Logarte](https://pub.dev/packages/logarte) for debugging network requests and viewing logs directly on the device.

## Features

- **Network Request Logging**: All API calls are automatically logged via Dio interceptor
- **Navigation Logging**: Screen navigation events are logged
- **Log Viewer**: Searchable debug console
- **Share Logs**: Share individual requests or export all logs
- **Password Protection**: Protect console access in release builds

---

## Requirements

1. **Settings Access**: The debug console must be accessible from the app's Settings screen
2. **Config Toggle**: Must be enable/disable via `AppConfig.enableLogarte`

---

## Integration Steps

### 1. Add Dependencies

```yaml
dependencies:
  logarte: ^1.0.0
  share_plus: ^7.0.0
```

Run:

```bash
fvm flutter pub get
```

### 2. Add Config Toggle

In `lib/config/app_config.dart`:

```dart
class AppConfig {
  AppConfig._();

  // ... other config values

  /// Enable Logarte in-app debugger (set to false for production releases).
  static const bool enableLogarte = true;

  /// Password for Logarte console (only used in release mode).
  static const String logartePassword = '1234';
}
```

### 3. Create Logarte Service

Create `lib/services/logarte_service.dart`:

```dart
import 'package:flutter/foundation.dart';
import 'package:logarte/logarte.dart';
import 'package:share_plus/share_plus.dart';
import '../config/app_config.dart';

final Logarte logarte = Logarte(
  password: AppConfig.logartePassword,
  ignorePassword: kDebugMode, // Skip password in debug mode
  onShare: (String content) =>
      SharePlus.instance.share(ShareParams(text: content)),
  onExport: (String allLogs) =>
      SharePlus.instance.share(ShareParams(text: allLogs)),
  disableDebugConsoleLogs: false,
);

bool get isLogarteEnabled => AppConfig.enableLogarte;
```

### 4. Add Dio Interceptor

In your API client (e.g., `lib/services/api_client.dart`):

```dart
import 'package:logarte/logarte.dart';
import 'logarte_service.dart';

class ApiClient {
  ApiClient._();

  static final Dio _dio = _createDio();

  static Dio _createDio() {
    final dio = Dio(
      BaseOptions(
        baseUrl: AppConfig.apiBaseUrl,
        // ... other options
      ),
    );

    // Add Logarte interceptor if enabled
    if (isLogarteEnabled) {
      dio.interceptors.add(LogarteDioInterceptor(logarte));
    }

    return dio;
  }

  static Dio get instance => _dio;
}
```

### 5. Add Navigator Observer

In `lib/main.dart`:

```dart
import 'package:logarte/logarte.dart';
import 'services/logarte_service.dart';

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      // ... other properties
      navigatorObservers: isLogarteEnabled
          ? [LogarteNavigatorObserver(logarte)]
          : [],
    );
  }
}
```

### 6. Add Settings Menu Item

In your Settings screen:

```dart
import '../services/logarte_service.dart';
import '../config/app_config.dart';

class SettingsScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Settings')),
      body: ListView(
        children: [
          // ... other settings

          // Debug Console (only show if enabled)
          if (AppConfig.enableLogarte)
            ListTile(
              leading: Icon(Icons.bug_report),
              title: Text('Debug Console'),
              subtitle: Text('View network requests and logs'),
              onTap: () => logarte.openConsole(context),
            ),
        ],
      ),
    );
  }
}
```

---

## Release Builds

For production releases:

1. Set `AppConfig.enableLogarte = false`
2. The debugger will be completely disabled
3. No menu item will appear in Settings
4. No interceptors will be added

If you need debugging in release builds (e.g., for beta testing), keep `enableLogarte = true` and rely on the password protection.

---

## Optional Features

### Floating Debug Button

Attach a floating button for quick access (useful during development):

```dart
@override
void initState() {
  super.initState();
  if (isLogarteEnabled) {
    logarte.attach(context: context, visible: true);
  }
}
```

### Magic Tap (Hidden Activation)

Enable 10-tap hidden activation on any widget:

```dart
LogarteMagicalTap(
  logarte: logarte,
  child: Text('App Version 1.0'),
)
```

### Custom Logging

```dart
// Simple log
logarte.log('Something happened');

// Log with stack trace
try {
  throw Exception('Error');
} catch (e, s) {
  logarte.log(e, stackTrace: s);
}

// Log database/storage operations
logarte.database(
  target: 'language',
  value: 'en',
  source: 'SharedPreferences',
);
```
