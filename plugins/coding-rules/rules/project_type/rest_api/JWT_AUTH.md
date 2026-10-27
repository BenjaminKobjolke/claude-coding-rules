# Version
1

Increase this version number whenever this rule file changes.

# PHP REST API — JWT Authentication

Applies on top of `project_type/REST_API.md` when the API authenticates with JWT Bearer tokens.

## JWT Authentication Middleware
<!-- steps: review, code -->

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

## JWT Dependency
<!-- steps: review, code -->

Require `firebase/php-jwt` in `composer.json`.

## Manual JWT Testing
<!-- steps: review, code -->

Use `tools/gen_token.php` to generate JWT tokens for curl testing:

```bash
# Generate a token for a user
TOKEN=$(php tools/gen_token.php <user_id>)

# GET request
curl -s -H "Authorization: Bearer $TOKEN" http://localhost/my-api/api/v1/habits | jq
```

## JWT Test Utility
<!-- steps: review, code -->

In `ApiTestCase`, `createAuthenticatedRequest()` creates authenticated requests with an auto-generated JWT:

```php
$request = $this->createAuthenticatedRequest('GET', '/api/v1/habits');
```

## JWT Endpoint Documentation
<!-- steps: review, code -->

Document authentication in endpoint docs with `Authorization: Bearer <token>`. The endpoint README
authentication note is `Authorization: Bearer <token>`.

## JWT Hoppscotch Header
<!-- steps: review, code -->

Set the `Authorization` header to `Bearer <<token>>`, using the `token` environment variable.
