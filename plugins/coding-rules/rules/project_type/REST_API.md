# Version
3

Increase this version number whenever this rule file changes.

# PHP REST API Rules

These rules apply to PHP REST API projects using Slim 4 + Cycle ORM.
See `COMMON_RULES.md` for rules that apply to all languages.
See `PHP_RULES.md` for general PHP rules (config files, timezone handling, batch files).

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Framework | Slim 4 (PSR-7 HTTP) |
| ORM | Cycle ORM 2.x with annotations |
| Authentication | Firebase JWT (`firebase/php-jwt`) |
| Database | MySQL/MariaDB |
| Schema Migration | Cycle `SyncTables` (auto-migration) |

---

## Project Structure

```
project/
├── .htaccess                   # Root rewrite to public/
├── config/
│   ├── app.php                 # Application settings (gitignored)
│   ├── app.php.example         # Template for app.php
│   ├── database.php            # Database connection (gitignored)
│   └── database.php.example    # Template for database.php
├── docs/
│   └── endpoints/              # Endpoint documentation (one .md per endpoint + README.md index)
├── hoppscotch/                 # API testing collections (one .json per feature group)
├── lang/                       # Localization JSON files (if needed)
├── public/
│   └── index.php               # Application entry point
├── src/
│   ├── Config/
│   │   └── Routes.php          # Route definitions
│   ├── Container.php           # PSR-11 DI Container
│   ├── Controller/             # Request handlers
│   │   └── AbstractController.php
│   ├── Database/
│   │   └── OrmFactory.php      # ORM bootstrap + SyncTables
│   ├── Entity/                 # Cycle ORM entities
│   ├── Exception/              # Custom exceptions
│   ├── Helper/                 # Utility helpers
│   ├── Middleware/              # HTTP middleware
│   │   ├── AuthMiddleware.php
│   │   └── CorsMiddleware.php
│   ├── Presenter/              # Response formatters
│   ├── Repository/             # Data access layer
│   ├── Service/                # Business logic layer
│   └── Util/                   # General utilities
├── tests/
│   ├── TestCase/
│   │   └── ApiTestCase.php     # Base test class
│   └── Api/                    # API test files
├── tools/
│   ├── run_tests.bat            # Run PHPUnit
│   ├── analyze_code.bat        # Run code analysis
│   ├── fix_issues.bat          # Auto-fix code issues
│   └── gen_token.php           # JWT token generator for manual testing
├── composer.json
├── phpunit.xml
└── README.md
```

---

## Entry Point

`public/index.php` bootstraps the Slim application with WAMP-compatible base path detection:

```php
<?php

declare(strict_types=1);

require __DIR__ . '/../vendor/autoload.php';

// PHP notices/deprecations must never corrupt JSON response bodies.
// Real Throwables still reach the Slim error middleware.
error_reporting(E_ALL & ~E_DEPRECATED & ~E_USER_DEPRECATED);
ini_set('display_errors', '0');

use Slim\Factory\AppFactory;
use App\Container;

$container = new Container(__DIR__ . '/..');
AppFactory::setContainer($container);
$app = AppFactory::create();

// Auto-detect base path for subdirectory installations (e.g., WAMP)
$scriptDir = str_replace('\\', '/', dirname($_SERVER['SCRIPT_NAME']));
$basePath = preg_replace('#/public$#', '', $scriptDir);
if ($basePath !== '') {
    $app->setBasePath($basePath);
}

$app->addBodyParsingMiddleware();
$app->addRoutingMiddleware();
$app->addErrorMiddleware(true, true, true);
$app->add(\App\Middleware\CorsMiddleware::class);

(require __DIR__ . '/../src/Config/Routes.php')($app);

$app->run();
```

---

## Dependency Injection Container

Implement PSR-11 `ContainerInterface`. Use `match` dispatch for service resolution with lazy-loaded singletons:

```php
class Container implements ContainerInterface
{
    private string $baseDir;
    private ?ORMInterface $orm = null;

    /** @var array<string, mixed> */
    private array $instances = [];

    public function __construct(string $baseDir)
    {
        $this->baseDir = $baseDir;
    }

    public function get(string $id): mixed
    {
        if (isset($this->instances[$id])) {
            return $this->instances[$id];
        }

        return match ($id) {
            OrmFactory::class => $this->getOrmFactory(),
            HabitService::class => $this->getHabitService(),
            // ... more services
            default => throw new \RuntimeException("Service not found: $id"),
        };
    }

    public function has(string $id): bool
    {
        return in_array($id, [
            OrmFactory::class,
            HabitService::class,
            // ... same list
        ], true);
    }
}
```

### Singleton Pattern

Use nullable private properties for services that must be shared (ORM, auth, logger). Use direct `new` for stateless services:

```php
// Singleton — shared instance
public function getOrmFactory(): OrmFactory
{
    if ($this->ormFactory === null) {
        $this->ormFactory = new OrmFactory(
            $this->getDatabaseConfig(),
            $this->baseDir . '/src/Entity'
        );
    }
    return $this->ormFactory;
}

// Non-singleton — fresh instance each call
public function getHabitService(): HabitService
{
    return new HabitService(
        $this->getOrm(),
        $this->getEntityManager(),
        $this->getLogger()
    );
}
```

### Splitting a Growing Container

When the Container exceeds the file line limit, move domain-grouped factory methods into a
trait used by the Container (e.g. `ContainerIntegrationServices` holding the Twig, push
notification, and cron-queue factories):

```php
class Container implements ContainerInterface
{
    use ContainerIntegrationServices;
    // core factories stay here
}
```

This is the sanctioned exception to the no-behavior-traits rule: the trait holds only
stateless factory methods and has exactly one consumer — it exists purely to keep the
Container file navigable.

### APP_ENV for Test Environment

Disable external services (push notifications, third-party APIs) in test environment:

```php
$isTestEnv = ($_ENV['APP_ENV'] ?? null) === 'testing';
$enabled = $isTestEnv ? false : ($config['enabled'] ?? false);
```

---

## Route Organization

Define routes in `src/Config/Routes.php` as a closure that receives the Slim `App`. Group protected routes with `AuthMiddleware`:

```php
return function (App $app): void {
    // Health check
    $app->get('/', function ($_request, $response) {
        $data = ['name' => 'My API', 'version' => '1.0.0', 'status' => 'ok'];
        $response->getBody()->write(json_encode($data));
        return $response->withHeader('Content-Type', 'application/json');
    });

    // Public routes (no auth)
    $app->post('/api/v1/auth/init', [AuthController::class, 'initOAuth']);
    $app->post('/api/v1/auth/callback', [AuthController::class, 'callback']);

    // Protected routes
    $app->group('/api/v1', function (RouteCollectorProxy $group): void {
        $group->get('/habits', [HabitController::class, 'index']);
        $group->post('/habits', [HabitController::class, 'create']);
        $group->get('/habits/{id:[0-9]+}', [HabitController::class, 'show']);
        $group->patch('/habits/{id:[0-9]+}', [HabitController::class, 'update']);
        $group->delete('/habits/{id:[0-9]+}', [HabitController::class, 'delete']);
    })->add(AuthMiddleware::class);
};
```

### Route Conventions

- Use `/api/v1/` prefix for all API routes
- Use `[0-9]+` regex for numeric route parameters
- Use `[ControllerClass::class, 'method']` syntax for handlers
- Group related routes logically (habits, friends, feed, etc.)

---

## AbstractController

All controllers extend `AbstractController` which provides response helpers and request utilities:

```php
abstract class AbstractController
{
    protected Container $container;

    public function __construct(Container $container)
    {
        $this->container = $container;
    }

    // Response helpers
    protected function json(array $data, int $status = 200): ResponseInterface;
    protected function error(string $message, int $status = 400, ?array $details = null): ResponseInterface;
    protected function notFound(string $message = 'Resource not found'): ResponseInterface;
    protected function unauthorized(string $message = 'Unauthorized'): ResponseInterface;
    protected function forbidden(string $message = 'Forbidden'): ResponseInterface;
    protected function validationError(array $errors): ResponseInterface;
    protected function created(array $data): ResponseInterface;
    protected function noContent(): ResponseInterface;

    // Request utilities
    protected function getUserId(ServerRequestInterface $request): ?string;
    protected function getBody(ServerRequestInterface $request): array;
    protected function getQueryParam(ServerRequestInterface $request, string $name, mixed $default = null): mixed;
}
```

### Error Response Format

All errors follow a consistent JSON structure:

```json
{
    "error": true,
    "message": "Validation failed",
    "details": ["name is required"]
}
```

### ValidationException

Services throw a `ValidationException` carrying a `field => message` map; controllers map it
to a 422 response via `validationError()` with the map as `details`:

```php
class ValidationException extends \Exception
{
    /** @param array<string, string> $errors */
    public function __construct(private array $errors, string $message = 'Validation failed')
    {
        parent::__construct($message);
    }

    /** @return array<string, string> */
    public function getErrors(): array
    {
        return $this->errors;
    }
}
```

---

## Service Layer

Services contain business logic. They receive `ORMInterface` and `EntityManagerInterface` via constructor injection and resolve repositories from ORM:

```php
class HabitService
{
    private ORMInterface $orm;
    private EntityManagerInterface $em;
    private HabitRepository $habitRepo;

    public function __construct(
        ORMInterface $orm,
        EntityManagerInterface $em
    ) {
        $this->orm = $orm;
        $this->em = $em;
        /** @var HabitRepository $habitRepo */
        $habitRepo = $orm->getRepository(Habit::class);
        $this->habitRepo = $habitRepo;
    }

    public function createHabit(string $userId, array $data): Habit
    {
        $habit = Habit::create($userId, $data['name']);
        $this->em->persist($habit);
        $this->em->run();
        return $habit;
    }
}
```

---

## Repository Pattern

Repositories extend `Cycle\ORM\Select\Repository` with typed generics. They encapsulate all database queries:

```php
use Cycle\ORM\Select\Repository;

/**
 * @extends Repository<Habit>
 */
class HabitRepository extends Repository
{
    /**
     * @return Habit[]
     */
    public function findByUserId(string $userId): array
    {
        return $this->select()
            ->where('user_id', $userId)
            ->where('deleted_at', null)
            ->where('archived', false)
            ->orderBy('order', 'ASC')
            ->fetchAll();
    }

    public function findByIdAndUser(int $id, string $userId): ?Habit
    {
        return $this->select()
            ->where('id', $id)
            ->where('user_id', $userId)
            ->where('deleted_at', null)
            ->fetchOne();
    }
}
```

### Repository Conventions

- Default to excluding soft-deleted records (`deleted_at IS NULL`)
- Default to excluding archived records where applicable
- Use `fetchAll()` for collections, `fetchOne()` for single results
- Order by a consistent default (e.g., `order ASC`)

---

## Entity Pattern

Entities use Cycle ORM annotations. Follow these conventions:

```php
use Cycle\Annotated\Annotation\Entity;
use Cycle\Annotated\Annotation\Column;

#[Entity(repository: HabitRepository::class, table: 'habits')]
class Habit
{
    // Class constants for enum-like values
    public const COMPLETION_TYPE_CHECKBOX = 'checkbox';
    public const COMPLETION_TYPE_NUMERIC = 'numeric';

    #[Column(type: 'primary')]
    public int $id;

    #[Column(type: 'string', name: 'user_id')]
    public string $userId;

    #[Column(type: 'string')]
    public string $name = '[]';

    #[Column(type: 'datetime', nullable: true, name: 'deleted_at')]
    public ?\DateTimeImmutable $deletedAt = null;

    // Static factory method
    public static function create(string $userId, string $name): self
    {
        $entity = new self();
        $entity->userId = $userId;
        $entity->name = NameHelper::encode([$name]);
        return $entity;
    }

    // Serialization
    public function toArray(): array
    {
        return [
            'id' => $this->id,
            'user_id' => $this->userId,
            'name' => $this->getNames(),
        ];
    }

    // Domain methods
    public function getNames(): array
    {
        return NameHelper::decode($this->name);
    }

    public function setNames(array $names): void
    {
        $this->name = NameHelper::encode($names);
    }
}
```

### Entity Conventions

- Use `#[Entity]` annotation with explicit `repository` and `table`
- Use class constants for enum-like string values
- Provide `static create()` factory methods instead of complex constructors
- Provide `toArray()` for API serialization
- Use soft deletes (`deleted_at` column) instead of hard deletes
- Map column names with `name:` when PHP property uses camelCase

---

## Presenter Pattern

Presenters handle complex response formatting. They are read-only and receive ORM + services to assemble responses:

```php
class SharedHabitPresenter
{
    private ORMInterface $orm;
    private HabitService $habitService;

    public function __construct(ORMInterface $orm, HabitService $habitService)
    {
        $this->orm = $orm;
        $this->habitService = $habitService;
    }

    public function present(Habit $habit, SharedHabit $share, string $viewerUserId): array
    {
        $base = $habit->toArray();
        $base['type'] = 'shared';
        $base['creator'] = false;
        $base['share_mode'] = $share->mode;
        return $base;
    }
}
```

### When to Use Presenters

- Response requires data from multiple entities or services
- Response includes computed fields not stored in the database
- Complex grouping or transformation of data (e.g., `completions_by_user`)
- Keep controllers thin by moving formatting logic to presenters

---

## JWT Authentication Middleware

The `AuthMiddleware` validates Bearer tokens and supports dual token types (JWT + API tokens with prefix):

```php
class AuthMiddleware implements MiddlewareInterface
{
    private Container $container;

    public function __construct(Container $container)
    {
        $this->container = $container;
    }

    public function process(ServerRequestInterface $request, RequestHandlerInterface $handler): ResponseInterface
    {
        $authHeader = $request->getHeaderLine('Authorization');

        if (empty($authHeader) || !preg_match('/^Bearer\s+(.+)$/i', $authHeader, $matches)) {
            return $this->unauthorized('Missing or invalid Authorization header');
        }

        $token = $matches[1];

        // Dispatch by token type (API token prefix vs JWT)
        if (ApiTokenConfig::isApiToken($token)) {
            return $this->handleApiToken($request, $handler, $token);
        }
        return $this->handleJwtToken($request, $handler, $token);
    }
}
```

### Auth Flow

1. Extract `Authorization: Bearer <token>` header
2. Detect token type by prefix (e.g., `thapi_` for API tokens)
3. Validate token and resolve user ID
4. Store user ID in request attribute: `$request->withAttribute('user_id', $userId)`
5. Store auth type in request attribute: `$request->withAttribute('auth_type', 'jwt')`
6. Controllers read via `$this->getUserId($request)`

### API Token Storage

API tokens are prefixed opaque tokens, never stored in plain text:

- Format: `<prefix>_<random>` (e.g. `thapi_` + `bin2hex(random_bytes(32))`)
- Store only the SHA-256 hash (`token_hash` column); the raw token is shown ONCE at creation
- Track `last_used_at` on each successful validation
- Restrict regular users' tokens to an endpoint allowlist in a config class
  (`ApiTokenConfig::ALLOWED_ENDPOINTS`, a `METHOD => [paths]` map checked by the middleware)

### Machine Accounts

For headless integrations, `POST /api/v1/auth/machine-account` provisions an account without
OAuth. The `User.isMachine` flag grants that account's API token FULL access, bypassing the
endpoint allowlist that restricts regular users' tokens. The middleware does one user lookup
to check the flag.

### Admin Token Dev Endpoint

`POST /api/v1/auth/admin-token` mints a JWT for a given user when the request supplies
`config['admin_token_password']` — a dev/testing convenience to skip the full OAuth flow.
Document it as dev-only.

---

## CORS Middleware

Handle preflight OPTIONS requests and add CORS headers to all responses:

```php
class CorsMiddleware implements MiddlewareInterface
{
    public function process(ServerRequestInterface $request, RequestHandlerInterface $handler): ResponseInterface
    {
        if ($request->getMethod() === 'OPTIONS') {
            $response = new Response();
            return $this->addCorsHeaders($response);
        }

        $response = $handler->handle($request);
        return $this->addCorsHeaders($response);
    }

    private function addCorsHeaders(ResponseInterface $response): ResponseInterface
    {
        return $response
            ->withHeader('Access-Control-Allow-Origin', '*')
            ->withHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With')
            ->withHeader('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, DELETE, OPTIONS')
            ->withHeader('Access-Control-Max-Age', '86400');
    }
}
```

---

## Cron Endpoints

Cron routes live OUTSIDE the AuthMiddleware group. Protect them with a password query
parameter compared via `hash_equals()` against `config['cron_password']`; reject empty or
missing passwords:

```php
private function validateCronPassword(ServerRequestInterface $request): bool
{
    $password = $request->getQueryParams()['password'] ?? '';
    $expected = $this->container->getConfig()['cron_password'] ?? '';
    return $password !== '' && $expected !== '' && hash_equals($expected, $password);
}
```

### Queue + Drain Pattern

Decouple slow side effects (push notifications, emails) from request latency: requests
enqueue rows into a queue entity (e.g. `NotificationQueue`); a cron endpoint drains it:

```
GET /cron/notifications?password=...   →   {"processed": 12, "failed": 0, "cleaned": 3}
```

The drain method processes pending rows, marks failures, and cleans up old entries.

---

## ORM Setup

`OrmFactory` initializes Cycle ORM with annotation-based schema compilation and `SyncTables` for automatic migration:

```php
class OrmFactory
{
    private DatabaseConfig $config;
    private string $entityPath;

    public function __construct(DatabaseConfig $config, string $entityPath)
    {
        $this->config = $config;
        $this->entityPath = $entityPath;
    }

    public function getOrm(): ORMInterface
    {
        if ($this->orm === null) {
            $this->orm = new ORM(
                new Factory($this->getDbal()),
                $this->compileSchema()
            );
        }
        return $this->orm;
    }

    private function compileSchema(): Schema
    {
        $finder = (new Finder())->files()->in($this->entityPath)->name('*.php');
        $classLocator = new ClassLocator($finder);

        return new Schema((new Compiler())->compile(new Registry($this->getDbal()), [
            new Generator\ResetTables(),
            new Annotated\Embeddings(new TokenizerEmbeddingLocator($classLocator)),
            new Annotated\Entities(new TokenizerEntityLocator($classLocator)),
            new Annotated\TableInheritance(),
            new Annotated\MergeColumns(),
            new Generator\GenerateRelations(),
            new Generator\GenerateModifiers(),
            new Generator\ValidateEntities(),
            new Generator\RenderTables(),
            new Generator\RenderRelations(),
            new Generator\RenderModifiers(),
            new Annotated\MergeIndexes(),
            new Generator\SyncTables(),      // Auto-creates/updates tables
            new Generator\GenerateTypecast(),
        ]));
    }
}
```

`SyncTables` automatically creates and alters database tables to match entity annotations. No manual migrations needed during development.

---

## Logging

Implements the central `Logger` rule from `PHP_RULES.md` as a file-based rotating logger:

- Level filtering from config; daily files `app-YYYY-MM-DD.log`
- `max_files` rotation (delete oldest beyond the cap), checked once per request
- `LOCK_EX` append writes
- Config keys: `logging => ['path' => ..., 'level' => ..., 'max_files' => ...]`

### Domain Log Files

Give a critical subsystem its own structured log file via a dedicated logger class
(e.g. `NotificationLogger` writing `type=... recipients=... status=... reason=...` key=value
lines). One file per subsystem makes monitoring and grepping trivial without wading through
the general application log.

---

## Test Infrastructure

### Base Test Class

All API tests extend `ApiTestCase` which bootstraps the Slim app and provides test utilities:

```php
abstract class ApiTestCase extends TestCase
{
    protected App $app;
    protected Container $container;
    protected string $testUserId;
    protected string $testUserEmail;

    /** @var User[] */
    protected array $createdUsers = [];

    protected function setUp(): void
    {
        parent::setUp();

        // Generate unique IDs per test to prevent DB conflicts
        $uniqueId = bin2hex(random_bytes(8));
        $this->testUserId = 'test-user-' . $uniqueId;
        $this->testUserEmail = 'phpunit-' . $uniqueId . '@test.com';

        $baseDir = dirname(__DIR__, 2);
        $this->container = new Container($baseDir);
        $this->cleanupOrphanedTestUsers();

        AppFactory::setContainer($this->container);
        $this->app = AppFactory::create();
        $this->app->addBodyParsingMiddleware();
        $this->app->addRoutingMiddleware();
        $this->app->addErrorMiddleware(true, true, true);

        (require $baseDir . '/src/Config/Routes.php')($this->app);
    }
}
```

### Key Test Utilities

```php
// Create authenticated requests with auto-generated JWT
$request = $this->createAuthenticatedRequest('GET', '/api/v1/habits');

// Create and auto-cleanup database users
$user = $this->createUser($this->testUserId, 'test@example.com');

// Assert JSON response with status code
$body = $this->assertJsonResponse($response, 200);
```

### Multi-User Testing

```php
$otherUserId = 'test-other-' . bin2hex(random_bytes(8));
$otherUser = $this->createUser($otherUserId, 'other@example.com');

$request = $this->createAuthenticatedRequest('GET', '/api/v1/habits', [], $otherUserId);
$response = $this->runRequest($request);
```

### Orphan Cleanup

The base class automatically cleans up test users matching `phpunit%@test.com` pattern in `setUp()`, preventing leftover data from failed test runs.

### Teardown

Users created with `$this->createUser()` are auto-cleaned in `tearDown()`. Other entities (habits, completions, etc.) need manual cleanup:

```php
protected function tearDown(): void
{
    // Clean up custom entities
    if (isset($this->habit)) {
        $this->container->getEntityManager()->delete($this->habit);
        $this->container->getEntityManager()->run();
    }

    parent::tearDown();  // Handles user cleanup
}
```

---

## Required Tools

Every REST API project must include these batch files in `tools/`:

| File | Purpose |
|------|---------|
| `tools/run_tests.bat` | Run PHPUnit test suite |
| `tools/analyze_code.bat` | Run PHPStan + code analysis |
| `tools/fix_issues.bat` | Auto-fix code style (PHP-CS-Fixer) |
| `tools/gen_token.php` | Generate JWT tokens for manual API testing |

### Post-Implementation Workflow

After implementing any new feature, run these in order:

```bash
# 1. Auto-fix code style
powershell -Command "cd 'tools'; cmd /c '.\fix_issues.bat'"

# 2. Run code analysis
powershell -Command "cd 'tools'; cmd /c '.\analyze_code.bat'"

# 3. Run all tests
powershell -Command "cd 'tools'; cmd /c '.\run_tests.bat'"
```

---

## Manual API Testing

Use `tools/gen_token.php` to generate JWT tokens for curl testing:

```bash
# Generate a token for a user
TOKEN=$(php tools/gen_token.php <user_id>)

# GET request
curl -s -H "Authorization: Bearer $TOKEN" http://localhost/my-api/api/v1/habits | jq

# POST request
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Habit"}' \
  http://localhost/my-api/api/v1/habits | jq
```

---

## Endpoint Documentation

Create one markdown file in `docs/endpoints/` **per endpoint**, named `<group>-<action>.md`
(e.g. `habits-create.md`, `habits-week.md`, `feed-mark-read.md`). Update the docs whenever an
endpoint changes.

### README.md Index (mandatory)

`docs/endpoints/README.md` is the entry point. It contains:

- Base URL code block
- Authentication note (`Authorization: Bearer <token>`)
- Endpoints grouped by feature, each linking to its file:

```markdown
### Habits
- [GET /habits](habits-index.md) - Get all habits
- [POST /habits](habits-create.md) - Create new habit
- [PATCH /habits/{id}](habits-update.md) - Update habit
```

- HTTP status code table (200/201/204/400/401/404/422/500)

### Per-Endpoint File Format

```markdown
# Get Habits for Week

Retrieve habits with week-specific data for the home screen.

## Endpoint

```
GET /api/v1/habits/week
```

## Authentication

**Required.** Bearer token in Authorization header.

## Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| offset | integer | No | Week offset (0 = current, -1 = last week). Default: 0. |

### Examples

```
GET /api/v1/habits/week
GET /api/v1/habits/week?offset=-1
```

## Response

### Success (200)

```json
{
    "week_start": "2025-01-06",
    "habits": [
        {"id": 1, "name": ["Morning Run"], "completions": []}
    ]
}
```

### Error (401)

```json
{
    "error": true,
    "message": "Invalid or expired token"
}
```
```

---

## Per-Topic Documentation

Each cross-cutting concern gets one markdown doc in `docs/`, kept updated when the concern
changes. Examples:

```
docs/
├── TIMEZONE.md            # DATE handling, UTC-noon convention
├── CRON.md                # Cron endpoints, queue drain, scheduling
├── DEEPLINKS.md           # App deep-link URL schemes
├── PHP_ERROR_OUTPUT.md    # Bootstrap error-output guard rationale
└── TRANSLATIONS.md        # Localization workflow
```

---

## API Testing Collection

Include Hoppscotch JSON collection files in `hoppscotch/` — **one collection file per feature
group**, no single big all-endpoints collection:

```
hoppscotch/
├── habits-week.json        # Habit week endpoints
├── feed.json               # Feed endpoints
├── friends.json            # Friends endpoints
├── statistics-week.json    # Statistics endpoints
└── ...                     # One file per feature group
```

### Environment Variables

All requests use Hoppscotch environment variables — never hardcode host or tokens:

```json
{
    "endpoint": "<<baseURL>>api/v1/habits/week",
    "headers": [
        {"key": "Authorization", "value": "Bearer <<token>>", "active": true}
    ]
}
```

Update the matching collection file whenever endpoints are added or changed.

---

## Code Quality

| Tool | Config | Purpose |
|------|--------|---------|
| PHPStan | Level 5 | Static analysis |
| PHP-CS-Fixer | PSR-12 | Code style |
| code_analysis_rules.json | Max 300/500 lines | File length limits |

### code_analysis_rules.json

Place in project root to enforce file length limits:

```json
{
    "max_lines_warning": 300,
    "max_lines_error": 500
}
```
