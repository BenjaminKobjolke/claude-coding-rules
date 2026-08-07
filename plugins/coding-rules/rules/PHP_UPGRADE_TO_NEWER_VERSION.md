# Upgrading to a Newer PHP Version

Methodology for migrating an existing PHP codebase from an older PHP version to a newer target (e.g., 7.4 → 8.5). Generic workflow — adapt directory names and tooling versions to your project. For a worked example, see ax-suite-contest's `docs/PHP_8_UPGRADE.md` (PHP 7.4 → 8.5, 2026-05).

## Goal

Move a project's PHP runtime to a newer language version with no behavioral regressions, the smallest possible diff, and a documented audit trail. The upgrade is complete when:

- The new PHP binary runs the full PHPUnit suite green.
- `PHPCompatibility` static scan reports **zero** issues in project code (vendored libs may have runtime-guarded noise — document each exception).
- A browser smoke test of the primary user flows produces a clean error log.

## Tool stack

| Tool | Role | Notes |
|---|---|---|
| `phpcompatibility/php-compatibility` | Static scan for version-incompatible patterns. | **Pinned at 9.3.5 today.** The scanner itself crashes on PHP 8+ (`vsprintf` strict types), so the runner must invoke it under PHP 7.4 even when scanning code targeted at PHP 8.5. Watch for the 10.x release. |
| `rector/rector` (^2.x) | Automated AST-level fixes. | Configure with `->withPhpVersion(PhpVersion::PHP_XX)` and **named rules only**. `withPhpSets()` rewrites too aggressively — start narrow, add rules when deprecation notices surface in tests. |
| `phpunit/phpunit` | Verification. | PHPUnit 11 for greenfield. PHPUnit 9 if the existing suite uses PHPUnit 5–7 (less migration churn — see step 6 below). |

## Process

### 1. Baseline scan

```
tools\compat-check.bat <target-version>
```

Save the summary as `claude-plans/<project>-inventory.md`. Categorize findings into three buckets:

- **Project code** — must be fixed.
- **Vendored libs** — patch or delete (see step 7).
- **Upstream noise** — issues inside well-known templating/SDK libraries that can only be silenced by a library upgrade.

### 2. Bump the Composer floor

```json
{
    "require": {
        "php": ">=8.5"
    }
}
```

Set to the lowest version that must be supported. If you support a range (8.1 → 8.5), the floor stays at 8.1 even when targeting 8.5 — the goal is forward compatibility.

### 3. Pick Rector rules

Start with these three. Add more only as deprecation notices surface during testing.

- `NullToStrictStringFuncCallArgRector` (PHP 8.1) — null passed to internal string funcs.
- `Utf8DecodeEncodeToMbConvertEncodingRector` (PHP 8.2) — `utf8_encode` / `utf8_decode` removal.
- `ExplicitNullableParamTypeRector` (PHP 8.4) — implicit-nullable parameter deprecation.

### 4. Run Rector

```
tools\rector.bat            REM dry-run, preview diff
tools\rector.bat process    REM apply
```

Always dry-run first. Inspect the diff: Rector occasionally rewrites code in ways the author wouldn't (over-eager `(string)` casts in tight loops, etc.). Add specific files/dirs to the `withSkip()` list if needed.

### 5. Manual fixes

Categories Rector won't touch:

| Pattern | Fix |
|---|---|
| Removed extensions (`mcrypt`, `ereg`) | Replace with OpenSSL / PCRE. Delete dead libs that only loaded for one ext. |
| PHP4-style ctors (`function ClassName(...)`) | Rename to `__construct`. `phpcbf` can do this in bulk for some patterns. |
| `${var}` interpolation (deprecated PHP 8.2) | Convert to `{$var}`. Bulk-fixable via `phpcbf` with the `Squiz.Strings.DoubleQuoteUsage` sniff. |
| `implode($arr, $glue)` (removed) | Reorder to `implode($glue, $arr)`. |
| Call-time pass-by-reference (`func(&$x)`) | Remove `&` at call site; `&` belongs in the function signature, not the call. |
| `(integer)` / `(boolean)` long casts | Shorten to `(int)` / `(bool)`. |
| `each()` (removed PHP 8) | Replace with `foreach` or `key()/current()/next()`. |

### 6. PHPUnit migration (if needed)

Going from PHPUnit 5–7 to PHPUnit 9, expect this churn:

- `PHPUnit_Framework_TestCase` → `PHPUnit\Framework\TestCase`
- `setUp()` / `tearDown()` → add `: void` return type
- `assertRegExp` → `assertMatchesRegularExpression`
- `assertContains` / `assertNotContains` on strings → `assertStringContainsString` / `assertStringNotContainsString`
- `@expectedException` annotation → `$this->expectException(X::class)`
- `phpunit.xml` schema bump to 9.3

In `tests/bootstrap.php`, suppress `E_DEPRECATED | E_USER_DEPRECATED` if upstream libraries (Smarty 3.x, etc.) emit notices you can't fix.

For PHPUnit 9 → 11, the most common churn is `@dataProvider` annotation → `#[DataProvider]` attribute and stricter null-return-type enforcement.

### 7. Vendored libraries

**Every bundled lib that's loaded (autoloaded or required) on every request must parse cleanly on the new PHP, even if its code path is never executed.** PHP parses the whole file at include time.

Common offenders and treatment:

- **PHPExcel** — superseded by PhpSpreadsheet. Usually safe to delete if the project already uses PhpSpreadsheet.
- **Smarty 3.x** — patch or upgrade to 5. 3.1.48 loads on PHP 8.5 but emits implicit-nullable deprecations.
- **Facebook PHP SDK 2011 / similar dead SDKs** — fix `implode` argument order, otherwise the file fails to parse.
- **FirePHP** — replace with `error_log()`-based logger. FirePHP doesn't run on PHP 8.
- **Filemanager (ResponsiveFilemanager)** — needs JSON.php PHP4 ctor rename, `${var}` → `{$var}`, `(integer)` → `(int)`, call-time pass-by-reference removal.
- **Securimage** — needs the curly-brace-array-access (`$x{0}` → `$x[0]`) fix in 3 spots.

Document every patched lib in `docs/PHP_X_UPGRADE.md` so the next engineer knows what's been touched and why.

### 8. Re-scan

```
tools\compat-check.bat <target>
```

Project code should be at zero. Acceptable to leave vendored noise that's **runtime-guarded** (e.g., mcrypt-only code behind `function_exists('mcrypt_create_iv')` that falls back to OpenSSL). Document each exception in the upgrade notes.

## Verification

```
tools\tests-php.bat              REM PHPUnit green on new PHP binary
tools\rector.bat                 REM dry-run clean
tools\compat-check.bat <target>  REM zero project-code issues
```

Browser smoke checklist — customize per app, but cover at minimum:

- [ ] Login + main dashboard
- [ ] Primary CRUD flow end-to-end (create → edit → delete)
- [ ] File upload / export (any binary I/O path)
- [ ] Email send (any external service integration)
- [ ] `php_errors.log` clean of project-code deprecations after the smoke session

## Common pitfalls

- **PHPCompatibility 9.3.5 itself doesn't run on PHP 8.** Keep an old PHP binary installed (PHP 7.4 works) just to host the scanner. The `PHP_LEGACY_EXE` setting in `php_upgrade_config.bat` exists for this reason.
- **Rector's `withPhpSets()` is too aggressive.** Stick with named rules until tests catch genuine deprecations.
- **Smarty 3.x emits ~12 implicit-nullable deprecations** under PHP 8.4+. Suppression in `tests/bootstrap.php` is the practical short-term fix; long-term, upgrade to Smarty 5.
- **Bundled SDKs (Facebook, FirePHP, Filemanager) often need manual edits.** They parse but don't run cleanly — and parse errors block the whole request.
- **`composer.json` `"php"` constraint affects PHP-CS-Fixer behavior.** PHP-CS-Fixer warns when run on a newer PHP than the project's declared floor; this is informational, not an error.
- **Don't trust `phpcs --report=summary` for the final sign-off.** Use `--report=full` (the `compat-check-detail.bat` runner) so you can read each finding and decide what's acceptable.

## Templated runners

See [`php_setup_files/tools/`](php_setup_files/tools/) for ready-to-copy batch wrappers. Workflow per project:

1. Copy `php_setup_files/tools/*` into the project's `tools/` folder.
2. `cp tools/php_upgrade_config.example.bat tools/php_upgrade_config.bat` and fill in PHP binary paths + project scan dirs.
3. Add `tools/php_upgrade_config.bat` to `.gitignore`.
4. `composer require --dev phpcompatibility/php-compatibility rector/rector`.
5. Edit `tools/rector.php` — set `withPhpVersion()`, `withPaths()`, `withSkip()` for the project layout.
