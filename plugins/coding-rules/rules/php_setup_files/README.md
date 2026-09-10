# PHP Setup Files

Templated PHP tooling. Two independent kits:

## Fast test suite (any Slim + Cycle API)

See [`FAST_TESTS.md`](FAST_TESTS.md). Copy `tools/tests.bat`, `tools/run_tests.bat`,
`tools/run_integration_tests.bat` verbatim and `tools/get_live_db.bat` with its
`__PLACEHOLDERS__` replaced; `tests/TestSuiteSplitTest.php` is optional.

| File | Purpose |
|---|---|
| `FAST_TESTS.md` | The recipe: local DB mirror, schema cached per process, `XDEBUG_MODE=off`, unit/integration split. |
| `tools/tests.bat` | Full runner: pulls the mirror, runs phpunit, writes `tools/_last_test_run.log`, exits with phpunit's code. |
| `tools/run_tests.bat` | `--testsuite unit`, no DB pull (offline). |
| `tools/run_integration_tests.bat` | `--testsuite integration`, pulls first. |
| `tools/get_live_db.bat` | Non-interactive live → local copy via `sqlbackup --copy --force`. Template with placeholders. |
| `tests/TestSuiteSplitTest.php` | Guards the hand-maintained `phpunit.xml` suite lists (needed when DB-backed tests live outside `tests/Api`). |

## PHP version upgrade

Copy `tools/*` into your project's `tools/` folder, then:

1. `cp tools/php_upgrade_config.example.bat tools/php_upgrade_config.bat`
2. Edit `tools/php_upgrade_config.bat` — set PHP binaries (legacy + target), scan dirs, target version.
3. Add `tools/php_upgrade_config.bat` to `.gitignore` (it contains machine-specific paths).
4. Install dev deps:
   ```
   composer require --dev phpcompatibility/php-compatibility rector/rector
   ```
5. Edit `tools/rector.php` — set `withPhpVersion()`, `withPaths()`, and `withSkip()` to match your project layout.

| File | Purpose |
|---|---|
| `tools/php_upgrade_config.example.bat` | Template for project-specific paths. All other runners source it. |
| `tools/compat-check.bat` | PHPCompatibility static scan (summary report). |
| `tools/compat-check-detail.bat` | PHPCompatibility scan (full per-file report). |
| `tools/rector.bat` | Rector runner (dry-run by default; `rector.bat process` to apply). |
| `tools/rector.php` | Rector config — edit per project. |
| `tools/tests-php.bat` | PHPUnit 11 **phar** runner for legacy projects without composer-installed phpunit. Auto-downloads `phpunit11.phar`. Unrelated to the composer-based `tests.bat` above. |

See [`../PHP_UPGRADE_TO_NEWER_VERSION.md`](../PHP_UPGRADE_TO_NEWER_VERSION.md) for the full upgrade workflow these tools support.

### PHPUnit version note

The default is PHPUnit 11 (latest). For projects migrating from PHPUnit 5–7, swap the phar URL in `tests-php.bat` to `https://phar.phpunit.de/phpunit-9.phar` — see step 6 of `PHP_UPGRADE_TO_NEWER_VERSION.md` for the typical churn.
