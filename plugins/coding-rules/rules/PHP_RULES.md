# Version
1

Increase this version number whenever this rule file changes.

# PHP Rules

See `COMMON_RULES.md` for rules that apply to all languages.

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

## Web Server & Asset Paths

### `.htaccess` — Redirect to Public Folder

Place a root `.htaccess` that rewrites all requests into the `public/` directory:

```apache
RewriteEngine On
RewriteRule ^$ public/ [L]
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule ^(.+)$ public/$1 [L]
```

Expected directory structure:

```
project/
├── .htaccess              # Root rewrite (above)
├── assets/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
├── public/
│   └── index.php          # Application entry point
├── src/
├── templates/
└── vendor/
```

### Asset Paths in Templates

**Always use plain relative paths** for assets — never `../assets/...` or absolute `/assets/...`.

```html
<!-- Correct -->
<link rel="stylesheet" href="assets/css/style.css">
<script src="assets/js/app.js"></script>

<!-- Wrong — breaks when URL is http://localhost/project-name/ -->
<link rel="stylesheet" href="../assets/css/style.css">

<!-- Wrong — breaks when app is in a subfolder -->
<link rel="stylesheet" href="/assets/css/style.css">
```

Why plain relative paths work: `RewriteCond %{REQUEST_FILENAME} !-f` checks if the file exists on disk. Since `assets/css/style.css` exists as a real file, the rewrite is skipped and Apache serves it directly. `../` breaks because the browser resolves it relative to the current URL before the request reaches the server (e.g. `http://localhost/project-name/` + `../assets/...` resolves to `http://localhost/assets/...` which doesn't exist).

---

## Template Engine

Keep PHP, HTML, CSS, and JS separated.
This means using a template engine.

Use Twig 3:
```bash
composer require twig/twig
```

Do not put JS code into templates. Use separate `.js` files.

## Localization

Use the php-localization library for multi-language support:
https://github.com/BenjaminKobjolke/php-localization.git

### Installation

Add to `composer.json`:
```json
{
    "repositories": [
        {
            "type": "vcs",
            "url": "https://github.com/BenjaminKobjolke/php-localization.git"
        }
    ],
    "require": {
        "xida/php-localization": "*"
    }
}
```

Then run:
```bash
composer update xida/php-localization
```

### Directory Structure

```
project/
├── lang/
│   ├── en.json    # English (default)
│   ├── de.json    # German
│   └── fr.json    # French
├── src/
└── templates/
```

### Translation File Format

Create `lang/en.json` with nested structure:
```json
{
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
    "flash": {
        "success": {
            "saved": "Changes saved successfully.",
            "deleted": "Item deleted successfully."
        },
        "error": {
            "not_found": "Item not found.",
            "invalid_id": "Invalid ID."
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

### PHP Setup

#### Container Integration

Add a method to your DI Container:
```php
use PhpLocalization\Localization;

class Container
{
    private ?Localization $localization = null;

    public function getLocalization(): Localization
    {
        if ($this->localization === null) {
            $this->localization = new Localization([
                'driver' => 'json',
                'langDir' => $this->baseDir . '/lang/',  // trailing slash required
                'defaultLang' => 'en',
                'fallBackLang' => 'en',
            ]);
        }
        return $this->localization;
    }
}
```

#### Controller Helper

Add translation helper to your base controller:
```php
use PhpLocalization\Localization;

abstract class AbstractController
{
    protected function getLocalization(): Localization
    {
        return $this->container->getLocalization();
    }

    protected function t(string $key, array $params = []): string
    {
        return $this->getLocalization()->lang($key, $params);
    }
}
```

Usage in controllers:
```php
// Simple translation
$this->addFlash('success', $this->t('flash.success.saved'));

// With placeholders
$this->addFlash('info', $this->t('messages.welcome', [':name' => $user->name]));
```

### Twig Integration

#### Add the `t()` Function

In your TwigFactory or wherever you configure Twig:
```php
use Twig\TwigFunction;
use PhpLocalization\Localization;

public function create(Localization $localization): Environment
{
    $twig = new Environment($loader, [...]);

    // Add translation function
    $twig->addFunction(new TwigFunction('t', function (string $key, array $params = []) use ($localization) {
        return $localization->lang($key, $params);
    }));

    return $twig;
}
```

#### Usage in Templates

Simple translations:
```twig
<h1>{{ t('nav.dashboard') }}</h1>
<button>{{ t('common.save') }}</button>
<a href="/logout">{{ t('nav.logout') }}</a>
```

With placeholders (define in JSON as `:placeholder`):
```json
{
    "messages": {
        "welcome": "Hello, :name!",
        "items_count": "You have :count items"
    }
}
```

```twig
<p>{{ t('messages.welcome', {':name': user.name}) }}</p>
<p>{{ t('messages.items_count', {':count': items|length}) }}</p>
```

Conditional content:
```twig
{% if error == 'auth_failed' %}
    {{ t('auth.error.auth_failed') }}
{% elseif error == 'rate_limited' %}
    {{ t('auth.error.rate_limited') }}
{% endif %}
```

In attributes:
```twig
<a href="/back" title="{{ t('common.back') }}">
    <i class="icon-back"></i>
</a>

<button onclick="return confirm('{{ t('confirm.delete') }}')">
    {{ t('common.delete') }}
</button>
```

### Translation Key Naming Convention

Use dot notation with logical grouping:
```
section.subsection.key

nav.dashboard          - Navigation items
auth.login_title       - Authentication related
flash.success.saved    - Flash messages by type
flash.error.not_found
form.label.name        - Form labels
form.placeholder.email - Form placeholders
form.validation.required - Validation messages
common.save            - Reusable UI elements
errors.404.title       - Error pages
```

### Translation Keys as Constants

Using raw strings like `t('nav.dashboard')` is error-prone. Create a `TranslationKeys` class with all keys as constants for IDE autocomplete and compile-time error checking.

#### Create `src/Config/TranslationKeys.php`

```php
<?php

namespace App\Config;

final class TranslationKeys
{
    // Navigation
    public const NAV_DASHBOARD = 'nav.dashboard';
    public const NAV_SETTINGS = 'nav.settings';
    public const NAV_LOGOUT = 'nav.logout';

    // Auth
    public const AUTH_LOGIN_TITLE = 'auth.login_title';
    public const AUTH_ERROR_AUTH_FAILED = 'auth.error.auth_failed';

    // Flash messages
    public const FLASH_SUCCESS_SAVED = 'flash.success.saved';
    public const FLASH_ERROR_NOT_FOUND = 'flash.error.not_found';

    // Common
    public const COMMON_CANCEL = 'common.cancel';
    public const COMMON_SAVE = 'common.save';
}
```

#### Add as Twig Global

In TwigFactory, add TranslationKeys as a global:
```php
use App\Config\TranslationKeys;

$twig->addGlobal('TK', new TranslationKeys());
```

#### Usage in Controllers

```php
use App\Config\TranslationKeys as TK;

// Instead of:
$this->addFlash('success', $this->t('flash.success.saved'));

// Use:
$this->addFlash('success', $this->t(TK::FLASH_SUCCESS_SAVED));
```

#### Usage in Templates

```twig
{# Instead of: #}
{{ t('nav.dashboard') }}

{# Use: #}
{{ t(TK.NAV_DASHBOARD) }}
```

#### Benefits

- IDE autocomplete for all translation keys
- Compile-time error if constant doesn't exist
- Easy to find all usages of a key
- Refactoring support

### Adding New Languages

1. Copy `lang/en.json` to `lang/de.json`
2. Translate all values (keep keys identical)
3. Change language in configuration:

```php
$this->localization = new Localization([
    'driver' => 'json',
    'langDir' => $this->baseDir . '/lang/',
    'defaultLang' => 'de',  // Changed to German
    'fallBackLang' => 'en', // Falls back to English if key missing
]);
```

### Reference

Full documentation: https://github.com/BenjaminKobjolke/php-localization/blob/master/README.md

---

## Database: Cycle ORM Relations & Query Builder

### No Raw SQL

**Never use raw SQL or DBAL direct queries.** Always use Cycle ORM relations and the query builder. Raw SQL causes bugs when entity columns change — every SELECT must be manually updated. ORM relations automatically include all fields.

### Defining Relations (PHP 8 Attributes)

Always define entity relationships using Cycle ORM relation attributes. Use `fkCreate: false` and `indexCreate: false` when indexes already exist or FK constraints are not desired.

```php
use Cycle\Annotated\Annotation\Relation\BelongsTo;
use Cycle\Annotated\Annotation\Relation\HasOne;
use Cycle\Annotated\Annotation\Relation\HasMany;
```

#### BelongsTo (child stores FK to parent)

```php
// Required parent (non-nullable FK)
#[BelongsTo(target: BankAccount::class, innerKey: 'bank_account_id', fkCreate: false, indexCreate: false)]
public ?BankAccount $bankAccount = null;

// Optional parent (nullable FK)
#[BelongsTo(target: Category::class, innerKey: 'category_id', nullable: true, fkCreate: false, indexCreate: false)]
public ?Category $category = null;
```

**Key parameters:** `target` (parent class), `innerKey` (FK column in this entity), `nullable` (default false), `fkCreate` (create DB constraint, default true), `indexCreate` (create index, default true).

The existing column property (e.g., `public int $bankAccountId`) must remain — Cycle ORM uses both the column and the relation property.

#### HasOne (parent owns one child; child stores FK)

```php
#[HasOne(target: Expense::class, outerKey: 'bank_transaction_id', nullable: true, fkCreate: false, indexCreate: false)]
public ?Expense $expense = null;
```

**Key parameters:** `target` (child class), `outerKey` (FK column in child entity), `nullable` (default false).

#### HasMany (parent owns many children)

```php
#[HasMany(target: Post::class, outerKey: 'user_id', orderBy: ['created_at' => 'DESC'])]
private array $posts = [];
```

**Key parameters:** `target`, `outerKey`, `where` (auto-filter), `orderBy` (default sort).

### Eager Loading with `load()`

Use `load()` to preload relation data and avoid N+1 queries:

```php
// Load single relation
$this->select()
    ->load('bankAccount')
    ->load('category')
    ->load('expense')
    ->where('bank_account_id', $bankAccountId)
    ->orderBy('date_actual', 'DESC')
    ->fetchAll();

// Nested relations (dot notation)
$this->select()->load('posts.comments.author')->fetchAll();
```

### Filtering by Relations with `with()`

Use `with()` to join a relation for WHERE conditions without loading its data:

```php
// Filter transactions by related bank account's company
$this->select()
    ->with('bankAccount')
    ->where('bankAccount.companyId', $companyId)
    ->fetchAll();
```

**Key difference:** `load()` = preload relation data. `with()` = join for filtering only.

### Entity Output with Relations

Add a `toDetailArray()` method for enriched output that includes relation data:

```php
public function toDetailArray(): array
{
    return [
        ...$this->toArray(),
        'category_label' => $this->category?->label,
        'expense_id' => $this->expense?->id,
    ];
}
```

Only call `toDetailArray()` on entities fetched with `->load()`.

### Aggregate Queries (SUM, COUNT, GROUP BY)

Use `buildQuery()` to access the DBAL-level query builder for aggregates:

```php
use Cycle\Database\Injection\Fragment;
use Cycle\Database\Injection\Expression;

// Simple aggregate
$total = $this->select()->where('status', 'active')->count();

// Complex aggregates with GROUP BY
$this->select()
    ->with('bankAccount')
    ->where('bankAccount.companyId', $companyId)
    ->buildQuery()
    ->columns([
        'bt.category_id',
        new Fragment('SUM(CASE WHEN CAST(bt.value AS DECIMAL(15,2)) > 0 THEN CAST(bt.value AS DECIMAL(15,2)) ELSE 0 END) AS income'),
        new Fragment('COUNT(*) AS transaction_count'),
    ])
    ->groupBy('bt.category_id')
    ->run()
    ->fetchAll();
```

**Fragment vs Expression:**
- `Fragment`: Raw SQL, no escaping. Use for SQL functions, subqueries.
- `Expression`: Auto-quotes column identifiers. Use when referencing columns inside functions.

### Dynamic WHERE Conditions

Build dynamic conditions using chained `where()` calls on the query builder:

```php
$query = $this->select()
    ->with('bankAccount')
    ->where('bankAccount.companyId', $companyId);

if ($pattern !== null) {
    $query->where('name', 'LIKE', '%' . $pattern . '%');
}

if ($amountMin !== null && $amountMax !== null) {
    $query->where(new Fragment('ABS(CAST(value AS DECIMAL(15,2)))'), '>=', $amountMin)
          ->where(new Fragment('ABS(CAST(value AS DECIMAL(15,2)))'), '<=', $amountMax);
}

return $query->orderBy('date_actual', 'DESC')
    ->limit($limit)->offset($offset)
    ->fetchAll();
```

---

## Code Quality

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

When migrating an existing PHP codebase to a newer language version, follow the workflow in [`PHP_UPGRADE_TO_NEWER_VERSION.md`](PHP_UPGRADE_TO_NEWER_VERSION.md). High-level steps:

1. **Inventory** — scan the codebase for deprecated patterns with PHPCompatibility, file the findings as a baseline.
2. **Automate fixes** — run Rector against the target `PhpVersion::PHP_XX` with focused deprecation rules.
3. **Manual cleanup** — patch what Rector can't (bundled libraries, removed extensions, magic-method renames).
4. **Verify** — green PHPUnit suite on the new PHP binary + PHPCompatibility scan reports zero project-code issues.
5. **Smoke test** — exercise UI flows in a browser before declaring the migration done.

Templated batch runners and a Rector config live in [`php_setup_files/`](php_setup_files/). Copy them into the project's `tools/` folder and fill in the gitignored `php_upgrade_config.bat`.

---

## Essential Rules

### Required Batch Files

Every project must include:

- `tools/run_tests.bat` - Runs the test suite

---

### Middleware

Use PSR-15 middleware for cross-cutting concerns such as authentication, CORS, logging, and rate
limiting. This keeps controller code focused on business logic and avoids duplicating infrastructure
code across routes.

---

### Configuration Files

Use plain PHP config files instead of `.env` files. Do not use `vlucas/phpdotenv`.

#### Structure

```
project/
├── config/
│   ├── app.php           # General application settings (gitignored)
│   ├── app.php.example   # Template for app.php
│   ├── database.php      # Database connection settings (gitignored)
│   └── database.php.example  # Template for database.php
```

#### config/app.php.example

```php
<?php

declare(strict_types=1);

return [
    'jwt_secret' => 'your-secret-key-change-in-production',
    'jwt_lifetime' => 86400,
    'debug' => true,
];
```

#### config/database.php.example

```php
<?php

declare(strict_types=1);

use Cycle\Database\Config;

$dbHost = 'localhost';
$dbPort = 3306;
$dbName = 'your_database';
$dbUser = 'root';
$dbPass = '';

return new Config\DatabaseConfig([
    'default' => 'default',
    'databases' => [
        'default' => ['connection' => 'mysql'],
    ],
    'connections' => [
        'mysql' => new Config\MySQLDriverConfig(
            connection: new Config\MySQL\TcpConnectionConfig(
                database: $dbName,
                host: $dbHost,
                port: $dbPort,
                user: $dbUser,
                password: $dbPass,
            ),
            queryCache: true,
        ),
    ],
]);
```

#### Usage in Code

```php
// Load app config
$config = require __DIR__ . '/../config/app.php';
$jwtSecret = $config['jwt_secret'];

// Load database config (returns DatabaseConfig object)
$dbConfig = require __DIR__ . '/../config/database.php';
```

#### .gitignore

Always exclude the actual config files, only commit the examples:

```
config/app.php
config/database.php
```

#### Setup Instructions (for README.md)

```bash
cp config/app.php.example config/app.php
cp config/database.php.example config/database.php
# Edit both files with your credentials
```

---

## Database Timezone Handling

When storing DATE type fields in a database using an ORM (Cycle, Doctrine, Eloquent), be careful with timezone handling. Creating a `DateTimeImmutable` from a date string without an explicit timezone can cause dates to shift by one day.

### The Problem

```php
// Server timezone: Europe/Paris (UTC+1)
$day = new DateTimeImmutable('2026-01-15');
// Creates: 2026-01-15 00:00:00+01:00

// When ORM stores as DATE type, it may convert to UTC:
// 2026-01-15 00:00:00+01:00 → 2026-01-14 23:00:00 UTC
// DATE becomes: 2026-01-14 (one day earlier!)
```

### The Solution

Always use explicit UTC timezone with noon time for DATE fields:

```php
$day = DateTimeImmutable::createFromFormat(
    'Y-m-d H:i:s',
    $dateString . ' 12:00:00',
    new \DateTimeZone('UTC')
);
```

### Why Noon?

Using noon (12:00) instead of midnight provides a safety buffer:
- Noon UTC is within the same calendar day for all timezones (UTC-12 to UTC+14)
- No timezone conversion can shift noon to a different day
- Makes code resilient to any server timezone configuration

### When This Pattern is Needed

- **DATE type columns**: Any field that stores only a date without time
- **User-provided date strings**: When parsing `Y-m-d` format from API requests
- **Date comparisons in queries**: Ensure consistent date handling

### When This Pattern is NOT Needed

- **DATETIME/TIMESTAMP columns**: These store full timestamps with timezone info
- **"Now" calculations**: `new DateTimeImmutable()` for current time is fine
- **Timestamps** (`created_at`, `updated_at`): These are meant to store exact moments

### Testing

Always include unit tests that verify date handling across different timezones:

```php
public function testDatePreservedAcrossTimezones(): void
{
    $inputDate = '2026-01-15';
    $originalTz = date_default_timezone_get();

    foreach (['UTC', 'Europe/Paris', 'America/New_York'] as $tz) {
        date_default_timezone_set($tz);

        $day = DateTimeImmutable::createFromFormat(
            'Y-m-d H:i:s',
            $inputDate . ' 12:00:00',
            new \DateTimeZone('UTC')
        );

        $this->assertSame($inputDate, $day->format('Y-m-d'));
    }

    date_default_timezone_set($originalTz);
}
```

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

## Value Objects for `$_POST` / `$_GET` Boundaries

Project-input arrays (`$_POST`, decoded request bodies, file-upload payloads) are the
legitimate source of raw associative arrays. Validate at the boundary and produce a typed
object **once**; never let `$_POST['some_key']` flow through three managers.

```php
// At the controller boundary
$payload = ContestSettingsPayload::fromPostArray($_POST);
if (!$payload->isValid()) {
    RedirectManager::backWithErrors($payload->errors());
    return;
}

// Everywhere downstream
$this->saveSettings($payload);   // type: ContestSettingsPayload
```

Pair with the existing "Input Validation at Boundaries" rule — that rule says *validate*;
this rule says *what the validated result should be*: a typed object, not a sanitized array.

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
