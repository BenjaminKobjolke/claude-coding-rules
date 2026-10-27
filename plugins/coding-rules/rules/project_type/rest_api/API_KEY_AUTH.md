# Version
1

Increase this version number whenever this rule file changes.

# PHP REST API — API Key Authentication

Applies on top of `project_type/REST_API.md` when the API authenticates with static API keys instead of JWT.

## API Key Header
<!-- steps: review, code -->

Send keys in the `X-Api-Key` header, never as a query parameter because query parameters can end
up in access logs. Define the name once as `Constants::HEADER_API_KEY`.

```http
X-Api-Key: <key>
```

Treat a missing or blank header value as missing authentication. A small `RequestHeader::get()`
helper should return a trimmed, non-empty header value or `null`. Add `X-Api-Key` to
`CorsMiddleware`'s `Access-Control-Allow-Headers` list.

## Admin Key and User Keys
<!-- steps: review, code -->

Use separate middleware and route groups for administrative and user access:

- The admin key is one secret in `config/app.php` under `admin_key`, with a placeholder in
  `config/app.php.example`. `AdminAuthMiddleware` compares it with `hash_equals`; an empty
  configured value rejects every request. It guards only user-management endpoints and does not
  authenticate a user.
- User API keys belong to users and are checked by `UserAuthMiddleware` on the normal `/api/v1`
  group. A user may have one or more keys.

```php
$app->group('/api/v1/users', function (RouteCollectorProxy $group): void {
    // User-management routes
})->add(AdminAuthMiddleware::class);

$app->group('/api/v1', function (RouteCollectorProxy $group): void {
    // Normal user routes
})->add(UserAuthMiddleware::class);
```

## Key Generation and Storage
<!-- steps: review, code -->

Generate each user key with `bin2hex(random_bytes(32))`; a readable prefix may be added. Store
only `hash('sha256', $key)` in a unique-indexed `api_key_hash` column. Show the raw key once in
the create or rotate response, and never include it in `toArray()`, list or detail rows, or logs.
Look up a key with `findByApiKeyHash(hash('sha256', $key))`. The hash lookup needs no
`hash_equals`; constant-time comparison applies to the admin key.

## Passing the User to Controllers
<!-- steps: review, code -->

After validating a user key, middleware puts the user's ID and auth type on the request. It may
also attach the loaded user entity to avoid another lookup. Admin middleware sets only the admin
auth type because the admin key does not authenticate a user.

```php
$request = $request
    ->withAttribute('user_id', $user->getId())
    ->withAttribute('auth_type', 'api_key')
    ->withAttribute('user', $user); // Optional: reuse the loaded entity

$request = $request->withAttribute('auth_type', 'admin');
```

Controllers use `$this->getUserId($request)`. Return `401` with the standard error body for a
missing or unknown key, and `403` when a valid key tries to access a forbidden resource. Track
`last_used_at` after successful user-key validation.

## Rotation and Revocation
<!-- steps: review, code -->

An admin-only `POST /api/v1/users/{id}/api-key` endpoint issues a new key and replaces the stored
hash. The old key stops working immediately; return the new raw key once. To revoke a key, set
`api_key_revoked_at` or deactivate its user, and make key lookup ignore revoked keys. Rotate the
admin key by changing the config value and redeploying; document the procedure in `docs/AUTH.md`.

## API Key Authentication Tests
<!-- steps: review, code -->

`ApiTestCase::createAuthenticatedRequest()` creates a user with a fresh key and sends it in
`X-Api-Key`. Add focused tests for each of these cases:

- Missing header returns `401`.
- Unknown key returns `401`.
- Blank header returns `401`.
- A valid key reaches the controller with the correct `user_id`.
- A revoked or rotated old key returns `401`.
- The new key works after rotation.
- Admin endpoints reject user keys and accept the admin key.
- An empty configured admin key rejects requests.
- Raw keys are absent from user list and detail responses.
- The stored value is the hash, never the raw key.

## Manual API Testing and Documentation
<!-- steps: review, code -->

Use the API key header when testing with curl:

```bash
curl -s -H "X-Api-Key: $API_KEY" http://localhost/my-api/api/v1/users | jq
```

The endpoint README authentication note names `X-Api-Key` and identifies which route groups
require the admin key. In Hoppscotch, set the `X-Api-Key` header to `<<api_key>>` for user routes
and `<<admin_key>>` for user-management routes; keep both values in environment variables.
