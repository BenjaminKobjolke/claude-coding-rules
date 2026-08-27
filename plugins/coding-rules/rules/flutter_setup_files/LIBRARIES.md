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

## Everything else

`dio`, `objectbox`, `get_it`, `freezed`, `logger` and `logarte` each have a dedicated section
in [`../FLUTTER_RULES.md`](../FLUTTER_RULES.md) covering setup and the required patterns
(`ApiClient` singleton, `ObjectBoxService`, the central `AppLogger`, and so on).

See [`../FLUTTER_RULES.md`](../FLUTTER_RULES.md) for the rules these support.
