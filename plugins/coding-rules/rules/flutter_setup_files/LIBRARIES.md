# Version
1

# Flutter Libraries

The approved third-party libraries for Flutter projects. **Check this file before implementing
any new feature** — if a library here already covers the job, use it instead of hand-rolling or
introducing an alternative.

Adding something new? Confirm the version with the user first (see
[`../COMMON_RULES.md`](../COMMON_RULES.md) → "Confirm Dependency Versions"), then add it to the
table below with a reference implementation, so the next project picks it up automatically.

## What's included

| Library | Version | Use for |
|---|---|---|
| `flutter_i18n_translations` | git (`main`) | Multi-language support — the house localization package |
| `flutter_bloc` + `equatable` | `^9.1.1` / `^2.1.0` | State management (Cubit) |
| `get_it` | `^9.2.1` | Dependency injection / service location |
| `dio` | `^5.11.0` | HTTP communication |
| `objectbox` + `objectbox_generator` | `^5.1.0` | Local database persistence |
| `freezed` + `json_serializable` | `^4.0.0` / `^6.14.1` | Immutable models and JSON serialization |
| `logger` | `^2.7.0` | Logging backend behind the central `AppLogger` |
| `fl_chart` | `^1.2.0` | Charts — line, bar, pie |
| `logarte` | latest | In-app network/log debugger |
| `shared_preferences` | `^2.5.5` | Small key/value settings storage |
| `flutter_dotenv` | `^5.1.0` | `.env` secrets loading (only when secrets exist) |
| `flutter_screen_recording` | `^2.0.25` | Native screen recording (MediaProjection / ReplayKit) — used by the `automated_screenshot_connector` demo host |
| `mobile_scanner` | `^7.4.2` | Camera QR / barcode scanning — Android, iOS, macOS, web only (no Windows/Linux) |

Versions are the last confirmed-good constraints. Verify against pub.dev before pinning a new
project — do not assume.

## Charts — `fl_chart`

The standard charting library. Covers line, bar and pie/donut charts; no separate library for
any of those.

```yaml
dependencies:
  # Charts
  fl_chart: ^1.2.0
```

Reference implementations (line chart with a day/week/month/year switcher, bar chart, donut):

- `turbo-habits-app/lib/widgets/habits/habit_history_chart.dart`
- `turbo-habits-app/lib/widgets/statistics/weekday_bar_chart.dart`
- `turbo-habits-app/lib/widgets/statistics/status_pie_chart.dart`
- `block-screen-app/lib/widgets/history/chart_tab.dart`

House conventions for charts:

- No shared chart theme or base class. Each chart styles itself from
  `Theme.of(context).colorScheme` (`primary`, `tertiary`, `outlineVariant`, and
  `inverseSurface`/`onInverseSurface` for tooltips) and `textTheme.labelSmall` for axis labels.
- X axis is **index-based** (`FlSpot(i, value)`), not timestamp-based. Recover the date in the
  title and tooltip callbacks via `buckets[value.toInt()].start`.
- Aggregate into zero-filled buckets **outside** the widget, in a pure testable function — the
  widget receives ready-made buckets and stays presentational.
- Cap bottom-axis labels at ~6 (`max(1, (buckets.length / 6).ceil())`) so custom ranges never
  produce overlapping labels.
- Keep axis labels locale-neutral and numeric (`26.8.`, `8.26`, `2026`) — charts must not pull
  in `intl`.

## Localization — `flutter_i18n_translations`

https://github.com/BenjaminKobjolke/flutter-i18n-translations

The only approved localization approach. Do **not** use `intl`, `flutter_localizations`, or
`.arb`/`gen_l10n` — see [`../FLUTTER_RULES.md`](../FLUTTER_RULES.md) → "Localization" for the
full setup, the `TK` constants convention, and the key-audit tooling in `tools/`.

## State management — `flutter_bloc`

Cubit only (no events, no full BLoC). States are immutable, `Equatable`, and use `copyWith`.
See [`../FLUTTER_RULES.md`](../FLUTTER_RULES.md) → "State Management (Cubit)".

## Screen recording — `flutter_screen_recording`

Used by the Flutter connector of `automated-application-screenshots` (network demo mode) to
record one mp4 per demo on the device. Pins `flutter_foreground_task ^9.1.0`; an app already on
`flutter_foreground_task ^11` needs `dependency_overrides: flutter_foreground_task: ^11.0.1`
(same Dart API, verified in `block-screen-app`). Android 14+ asks for consent before every
recording. Reference: `automated-application-screenshots-flutter-connector/lib/src/screen_recorder.dart`.

## QR scanning — `mobile_scanner`

Scan QR codes with the device camera. The first use is adding friends by scanning a profile QR
code.

```yaml
dependencies:
  # QR scanning
  mobile_scanner: ^7.4.2
```

Supported platforms: Android, iOS, macOS and web. There is no Windows or Linux implementation.
On desktop builds, gate the scan entry point by platform (hide the button) and keep a manual
code-entry fallback, as the reference does.

Camera permissions and setup:

- **Android:** the plugin's manifest declares `android.permission.CAMERA`, which is merged
  automatically. The runtime permission prompt appears when the scanner starts.
- **iOS:** add `NSCameraUsageDescription` to `ios/Runner/Info.plist`; without it, the app crashes
  when the scanner starts.
- **macOS:** add `NSCameraUsageDescription` to `Info.plist` and
  `com.apple.security.device.camera` to both entitlement files.
- **Web:** camera access requires a secure context (HTTPS or localhost).
- Handle `permissionDenied` and other `MobileScannerException`s with a localized message instead
  of showing a blank preview.

House conventions:

- Use a full-screen scanner screen that returns the scanned value to its caller with
  `Navigator.pop`.
- Validate the value before acting and show a hint for invalid codes.
- Reuse the existing submit path instead of creating a parallel one.

Reference implementations from GoRabbits App:

- `turbo-habits-app/lib/screens/friends/friend_qr_scanner_screen.dart` — scanner screen.
- `turbo-habits-app/lib/widgets/friends/add_friend_dialog.dart` — platform-gated entry point.

## Everything else

`dio`, `objectbox`, `get_it`, `freezed`, `logger` and `logarte` each have a dedicated section
in [`../FLUTTER_RULES.md`](../FLUTTER_RULES.md) covering setup and the required patterns
(`ApiClient` singleton, `ObjectBoxService`, the central `AppLogger`, and so on).

See [`../FLUTTER_RULES.md`](../FLUTTER_RULES.md) for the rules these support.
