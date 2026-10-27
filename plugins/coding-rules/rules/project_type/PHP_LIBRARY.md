# Version
1

Increase this version number whenever this rule file changes.

# PHP Library Rules (Composer Packages)

These rules apply to framework-free Composer packages with `"type": "library"`. Pair with
`PHP_RULES.md` only. Never apply `php/APP.md` or `DESIGN_RULES.md` to a library.
See `COMMON_RULES.md` for rules that apply to all languages.

---

## Package Layout

Declare the package type and PSR-4 namespaces in `composer.json`. Keep implementation in `src/`,
unit tests in `tests/Unit/`, and live-service integration tests in `tests/Integration/`. Register
the test namespace with `autoload-dev`. A reusable library has no `public/`, `.htaccess`,
`templates/`, or `config/database.php`.

```json
{
  "type": "library",
  "autoload": {"psr-4": {"Vendor\\Package\\": "src/"}},
  "autoload-dev": {"psr-4": {"Vendor\\Package\\Tests\\": "tests/"}}
}
```

## Public API Surface and Semantic Versioning

Everything in the package namespace is public API unless marked `@internal`. Mark internal
classes and methods explicitly, and declare classes `final` unless consumers are meant to extend
them. Treat removing or renaming a public class, method, or constant; adding a required parameter;
narrowing accepted parameter types; widening return types; or changing thrown exception types as a
backward-compatibility break that requires a major version. Additive public features are minor
versions; backward-compatible fixes are patch versions. Keep a `CHANGELOG.md` entry for each
release.

## Exceptions Are Public Contract

Define one package marker interface or base exception and ensure every exception escaping the
library implements or extends it. Use specific subclasses for API errors (including HTTP status
and API error code), transport errors, and invalid input. Catch and wrap Guzzle or PSR transport
exceptions, preserving the original as `previous`; do not let dependency exceptions leak through
the public API. Add `@throws` documentation to every public method that can throw.

```php
abstract class ShortlinksException extends RuntimeException {}

final class TransportException extends ShortlinksException {}
```

## Injectable HTTP Client

Inject the HTTP client through the constructor. Type it as PSR-18
`Psr\Http\Client\ClientInterface` when the library only needs the standard client contract;
Guzzle 7 implements PSR-18. Use `GuzzleHttp\ClientInterface` only when the public implementation
needs Guzzle-specific options. Provide a named static factory for the default client configuration;
never instantiate an HTTP client inside an operation method. Unit tests inject Guzzle's
`MockHandler` and `HandlerStack`, then assert the request that was sent.

## Configuration Comes From the Caller

Accept a typed configuration value object containing settings such as base URL, API key, and
timeout. The library does not read files, environment variables, or process globals; the
application that uses it owns configuration and secret storage. Keep a default base URL in one
named constant so callers can override it through the value object.

## Logging and Errors in a Library

This section overrides the `Logger` class and central error-handler requirements in the general
PHP rules for libraries. Accept an optional PSR-3 `LoggerInterface`, defaulting to `NullLogger`,
and never configure Monolog or a logging sink. Throw the documented package exceptions and let the
calling application decide how to handle or log them.

## Minimal Runtime Dependencies

Keep `require` limited to PHP, the HTTP client, and PSR interfaces used by the public API. Keep
PHPUnit, PHPStan, and PHP-CS-Fixer in `require-dev`; do not require a web framework. Choose
consumer-friendly caret constraints broad enough for compatible releases (for example,
`^7.8` for a supported dependency range), and confirm dependency versions against the package's
version policy before adding or changing them.

## Tests

Configure `phpunit.xml` with separate `unit` and `integration` suites. Unit tests make no network
calls and use an injected mocked HTTP client. Integration tests call the live API using a dedicated
test account, read credentials from gitignored `tests/integration.config.php` copied from a
committed `tests/integration.config.php.example`, skip with `markTestSkipped()` when the local
config is missing, and delete any resources they create. These tests need no database mirror.

Provide these focused runners in `tools/`; each shows PHPUnit progress, captures its exit code
immediately and returns it unchanged:

```bat
@echo off
vendor\bin\phpunit --testsuite unit --debug
set TESTRESULT=%ERRORLEVEL%
exit /b %TESTRESULT%
```

```bat
@echo off
vendor\bin\phpunit --testsuite integration --debug
set TESTRESULT=%ERRORLEVEL%
exit /b %TESTRESULT%
```

Do not add `pause`, output redirection, or a database-mirror `tests.bat`.

## README Usage Examples

Document installation with `composer require`. When the package is not on Packagist, include the
Composer VCS `repositories` entry and the package name consumers should require. Give a runnable
example for every public entry point, plus an example that catches the package exception type, and
show how to run both test suites. Examples must use the real public API and be updated in the same
change as that API.
