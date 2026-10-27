# Version
5

Increase this version number whenever this rule file changes.

# PHP Rules

See `COMMON_RULES.md` for rules that apply to all languages.

## Optional rule files

- `php/APP.md` — PHP web apps and APIs: `.htaccess`, Twig, localization, Cycle ORM, config files, DB-mirror test bats, middleware. Skip it for libraries.
- `project_type/PHP_LIBRARY.md` — Composer packages with `"type": "library"`.
- Run `/coding-rules:apply` to add them.

## PHP Version

Use PHP 8.5 for all projects. Set the requirement in `composer.json`:

```json
{
    "require": {
        "php": "^8.5"
    }
}
```

---

## Code Quality
<!-- steps: review, code -->

### PHPStan

Use PHPStan at level 5 for static analysis:

```bash
composer require --dev phpstan/phpstan
```

```neon
# phpstan.neon
parameters:
    level: 5
    paths:
        - src
```

### PHP-CS-Fixer

Use PHP-CS-Fixer with PSR-12 rules for code style:

```bash
composer require --dev friendsofphp/php-cs-fixer
```

```php
// .php-cs-fixer.php
<?php

$finder = PhpCsFixer\Finder::create()->in(__DIR__ . '/src');

return (new PhpCsFixer\Config())
    ->setRules(['@PSR12' => true])
    ->setFinder($finder);
```

Run formatting: `php vendor/bin/php-cs-fixer fix`

---

## Logging

Route all logging through one class named **`Logger`** (`src/Logger.php`), a thin PSR-3 wrapper
(e.g. over Monolog). Feature code calls `Logger`, never `echo`/`error_log`/`var_dump` or a raw
Monolog instance — this gives a single enable/level toggle and one place to change the sink.

```php
$logger->info('User loaded', ['user_id' => $id]);
$logger->error('Failed to load user', ['user_id' => $id, 'exception' => $e]);
```

---

## Upgrading to a Newer PHP Version
<!-- steps: code -->

When migrating an existing PHP codebase to a newer language version, follow the workflow in [`PHP_UPGRADE_TO_NEWER_VERSION.md`](PHP_UPGRADE_TO_NEWER_VERSION.md). High-level steps:

1. **Inventory** — scan the codebase for deprecated patterns with PHPCompatibility, file the findings as a baseline.
2. **Automate fixes** — run Rector against the target `PhpVersion::PHP_XX` with focused deprecation rules.
3. **Manual cleanup** — patch what Rector can't (bundled libraries, removed extensions, magic-method renames).
4. **Verify** — green PHPUnit suite on the new PHP binary + PHPCompatibility scan reports zero project-code issues.
5. **Smoke test** — exercise UI flows in a browser before declaring the migration done.

Templated batch runners and a Rector config live in [`php_setup_files/`](php_setup_files/). Copy them into the project's `tools/` folder and fill in the gitignored `php_upgrade_config.bat`.

---

## Wrap DB Rows and JSON Columns in Value Objects

PHP-specific application of the common rule "No Bag-of-Keys Returns at Module Boundaries".
PHP makes the bag-of-keys trap easy because every `fetch_assoc_all()`, `json_decode($col, true)`,
and `$_POST` payload starts life as `array<string, mixed>`. Stop the array from leaking past
the boundary that owns its schema.

### Repository methods return objects, not rows

```php
// Bad — caller indexes 20 string keys, silent on column rename
public function getContestDataForAdmin(int $id): ?array { ... }

// Good
public function getContestForAdmin(int $id): ?Contest { ... }
```

The repository *may* internally hold an `array<string, mixed>`, but the public method returns
a constructed object. PHPStan level 5+ then catches consumer regressions automatically when
properties change.

### List vs single is in the name and the return type

```php
public function findById(int $id): ?Thing;
/** @return Thing[] */
public function findAllForContest(int $contestId): array;
```

Never let one method return "row OR list of rows depending on input". A function whose body
does `fetch_assoc_all()` and whose name reads as singular (`getXxxValue`, `getXxxElement`) is
the exact shape that produces silent-`null` bugs at the call site.

### JSON-encoded value columns get a value object

A row's `value` column that stores `{"text":"...","fields":[...]}` JSON belongs in a
`XxxValue` class with `getText(): string`, `getFields(): array`. Decoding inline at every
call site spreads the schema across the codebase; each consumer becomes a maintenance
hazard when the JSON shape changes.

### `isset($result['key'])` on a method return is a smell

If you find yourself writing `isset($result['some_key'])` on the output of a method you
control, that method should be returning an object whose presence is signalled by `?Type`
(nullable return) and whose fields are accessed by getters. The only legitimate use of
`isset` on associative-array keys is on raw I/O input (`$_POST`, decoded external JSON) at
the boundary, before validation produces a typed object.

### Migration recipe for array-returning methods with many consumers

1. Write a characterization test against the current method that exercises representative
   inputs and locks the current outputs.
2. Add a parallel `getXxxObject()` method returning the typed class.
3. Migrate consumers one file per commit; the test stays green.
4. Delete the array-returning method once `grep` finds zero callers.

PHPStan level 5+ catches most regressions automatically once the return type changes from
`array` to `?ClassName` — leverage this rather than relying on review.

---

## Self-Describing Classes

Implement the common "Self-Describing Classes" rule using interfaces or PHP 8 attributes.

### Option A: Interface with explicit method

```php
interface Searchable
{
    /** @return string[] */
    public function getSearchableFields(): array;
}

class Customer implements Searchable
{
    public function __construct(
        public readonly string $name,
        public readonly string $email,
        public readonly string $phone,
    ) {}

    public function getSearchableFields(): array
    {
        return [$this->name, $this->email, $this->phone];
    }
}
```

### Option B: PHP 8 attribute on properties

```php
#[Attribute(Attribute::TARGET_PROPERTY)]
class Searchable {}

class Customer
{
    #[Searchable] public readonly string $name;
    #[Searchable] public readonly string $email;
    public readonly string $internalNotes; // not searchable
}

// Consumer reads attributes via ReflectionClass at bootstrap
```

Prefer the interface approach for straightforward cases. Use attributes when you need
fine-grained per-property control.

---

## Traits and Config Getters (Coupling)

See **Inject Collaborators, Don't Fold Dependencies In** in `COMMON_RULES.md` for the general
rule. In PHP the fold-in mechanism is the trait.

### `use SomeTrait` merges the trait's dependencies into the class

A `use SomeTrait` copies the trait's body — and every class it imports — into the host. Stacking
several behavior traits on one class quietly makes all of their dependencies the host's own. Prefer
a constructor-injected collaborator service for anything that carries dependencies.

```php
// Anti-pattern: five behavior traits, each pulling its own services/DTOs/constants into the class
class InvoiceDocumentController extends AbstractController
{
    use BulkUnlinkTrait;
    use DocumentDownloadTrait;
    use DocumentPreviewTrait;
    use DocumentSendTrait;
    use DocumentEmailPreviewTrait;
}

// Correct: inject one collaborator; its dependencies stay its own
class InvoiceDocumentController extends AbstractController
{
    public function __construct(private DocumentActions $documents) {}
}
```

### Replace config-getter swarms with a value object

When a trait/base declares many `abstract protected function getXxx(): string` hooks that each
subclass fills one-line-each, the constant references pile up across a dozen tiny methods. Bundle
them into one config value object (see **Use Objects for Related Values**).

```php
// Anti-pattern
protected function getSendEndpoint(): string      { return ApiEndpoints::INVOICE_SEND; }
protected function getSendSuccessKey(): string     { return TranslationKeys::INVOICE_SEND_SUCCESS; }
protected function getSendFailureRedirect(): string { return UrlPaths::INVOICES; }
// ...several more

// Correct
protected function documentSendConfig(): DocumentSendConfig
{
    return new DocumentSendConfig(
        sendEndpoint: ApiEndpoints::INVOICE_SEND,
        successKey:   TranslationKeys::INVOICE_SEND_SUCCESS,
        redirect:     UrlPaths::INVOICES,
    );
}
```

### Never `new` a service inside a method — inject it

```php
// Anti-pattern: hidden dependency, untestable
public function send(...): ResponseInterface
{
    $preparer = new EmailDataPreparer();
    $data = $preparer->prepare(...);
}

// Correct: inject EmailDataPreparer via the constructor and call the injected instance
```
