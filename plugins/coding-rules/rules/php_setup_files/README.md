# PHP Setup Files

Templated PHP tooling. Copy `tools/*` into your project's `tools/` folder, then:

1. `cp tools/php_upgrade_config.example.bat tools/php_upgrade_config.bat`
2. Edit `tools/php_upgrade_config.bat` — set PHP binaries (legacy + target), scan dirs, target version.
3. Add `tools/php_upgrade_config.bat` to `.gitignore` (it contains machine-specific paths).
4. Install dev deps:
   ```
   composer require --dev phpcompatibility/php-compatibility rector/rector
   ```
5. Edit `tools/rector.php` — set `withPhpVersion()`, `withPaths()`, and `withSkip()` to match your project layout.

## What's included

| File | Purpose |
|---|---|
| `tools/php_upgrade_config.example.bat` | Template for project-specific paths. All other runners source it. |
| `tools/compat-check.bat` | PHPCompatibility static scan (summary report). |
| `tools/compat-check-detail.bat` | PHPCompatibility scan (full per-file report). |
| `tools/rector.bat` | Rector runner (dry-run by default; `rector.bat process` to apply). |
| `tools/rector.php` | Rector config — edit per project. |
| `tools/tests-php.bat` | PHPUnit 11 runner. Auto-downloads `phpunit11.phar` if missing. |

See [`../PHP_UPGRADE_TO_NEWER_VERSION.md`](../PHP_UPGRADE_TO_NEWER_VERSION.md) for the full upgrade workflow these tools support.

## PHPUnit version note

The default is PHPUnit 11 (latest). For projects migrating from PHPUnit 5–7, swap the phar URL in `tests-php.bat` to `https://phar.phpunit.de/phpunit-9.phar` — see step 6 of `PHP_UPGRADE_TO_NEWER_VERSION.md` for the typical churn.
