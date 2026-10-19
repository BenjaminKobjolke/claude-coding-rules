# Fast PHPUnit Suites for PHP APIs

How to make a Slim + Cycle ORM test suite run in seconds instead of an hour. Generic recipe —
adapt DB names and paths. Worked examples: turbo-habits-api (`docs/SETUP_AND_RUN_TESTS.md`,
1407 tests in ~40s) and tickets-api (426 tests in ~16s).

## The three causes (measured on turbo-habits-api, one 55-test file)

| Change | Time for that file |
|---|---|
| Baseline: tests ran against the **live** DB over the network | 3m 47s |
| Point tests at a **local mirror** of that DB | 29.3s |
| Compile the Cycle ORM schema **once per process** instead of once per test | 3.0s |
| Run with `XDEBUG_MODE=off` | **1.8s** |

They are independent and multiply: a ~15 ms network round-trip per query (vs 0.03 ms locally),
a full schema introspection + `SyncTables` in every `setUp()`, and Xdebug's `develop` mode
costing ~12x on function calls. Do all three.

## 1. Local mirror of the live DB

Tests never touch production. `config/database.php` on a dev machine points at a local MySQL
database (`localhost`, `root`, no password — the same values as `config/database.php.example`).
A runner refreshes that mirror from live before each full run via the `sqlbackup` CLI
(`D:\GIT\BenjaminKobjolke\sql-backup`, needs `uv`):

- Two JSON configs next to the project's live backups, **outside the repo**:
  `<Backups>\<project>\sql\<project>.json` (live credentials) and
  `<project>_local.json` (`{"host":"localhost","port":<port>,"user":"root","password":"","database":"<local_db>"}`),
  `<port>` = the local server that matches live (see below).
- `tools/get_live_db.bat` — copy [`tools/get_live_db.bat`](tools/get_live_db.bat) and replace the
  `__PLACEHOLDERS__` in its header. It runs `sqlbackup --copy --source <live> --target <local> --force`,
  which **drops and recreates** the local DB. It is non-interactive on purpose (no confirm
  prompt, no `pause`): the test runner calls it unattended.

### The mirror runs the same engine as live

Run `SELECT VERSION()` on live before setting up the mirror and use the same engine locally —
MariaDB for a MariaDB live, MySQL for a MySQL live, ideally the same major version. A mismatched
mirror either fails the copy or tests a schema that is not live's:

- MariaDB stores long `UNIQUE` keys on MyISAM as a hidden hash (`USING HASH` in
  `SHOW CREATE TABLE`). MySQL cannot restore them: `1071 Specified key was too long; max key
  length is 1000 bytes`.
- MariaDB-only syntax in a migration (`ADD UNIQUE KEY IF NOT EXISTS`, …) fails on a MySQL mirror,
  so the migration can never be rehearsed locally.

WAMP ships both servers: MySQL on 3306 and MariaDB on **3307** (`mariaPortUsed` in
`wampmanager.conf`). Keep MySQL running for projects whose live is MySQL; point a MariaDB
project's `_local.json` and its test DB config at 3307. WAMP's MariaDB `my.ini` ships
`innodb_default_row_format=compact`, which caps index columns at 767 bytes
(`1709 Index column size too large`) — set it to `dynamic`. A WAMP reinstall resets it.

The copy and the tests must hit the **same** server: the test DB config (`config/database.php`,
or the project's test-settings class) needs its own port setting that matches `_local.json`.
Without it the copy refreshes one server while the tests read a stale DB on the other.

## 2. Runners

Copy [`tools/tests.bat`](tools/tests.bat), [`tools/run_tests.bat`](tools/run_tests.bat) and
[`tools/run_integration_tests.bat`](tools/run_integration_tests.bat) verbatim:

| Runner | Runs | DB pull |
|---|---|---|
| `tests.bat` | everything (`default` suite) | yes, unless `SKIP_DB_PULL=1` |
| `run_tests.bat` | `--testsuite unit` | never (sets `SKIP_DB_PULL=1`, works offline) |
| `run_integration_tests.bat` | `--testsuite integration` | yes |

`tests.bat` pulls the mirror, sets `XDEBUG_MODE=off`, and calls
`vendor\bin\phpunit.bat --colors=never --debug --log-events-text tools\_last_test_run.log %*`
with no redirect and no pipe. PHPUnit prints each test live and writes the log itself (gitignore
it); the script exits with phpunit's code. The `REM` comments in the bats carry the
gotchas (`cd /d`, full-path `sqlbackup.bat` call, no redirect, no pipe) — keep them.

Never run two phpunit processes at once: the pull drops the DB under the other run.

## 3. Schema compiled once per process

In `src/Database/OrmFactory.php` cache the compiled `Schema` in a static keyed by entity path;
build a fresh `ORM` per factory (a shared ORM would leak Cycle's identity map between tests):

```php
/** @var array<string, Schema> */
private static array $schemaCache = [];

public function getOrm(): ORMInterface
{
    if ($this->orm === null) {
        self::$schemaCache[$this->entityPath] ??= $this->compileSchema();
        $this->orm = new ORM(new Factory($this->getDbal()), self::$schemaCache[$this->entityPath]);
    }
    return $this->orm;
}
```

`compileSchema()` (tokenize entities, `SyncTables`, …) stays as it is; it now runs once per
phpunit process instead of once per test.

## 4. unit / integration suites in `phpunit.xml`

The split is **by base class, not by directory**: anything extending `ApiTestCase` boots the app
and needs MySQL. A `#[Group]` on the abstract base does not work — PHPUnit (verified on 12.5)
does not inherit class-level `Group` attributes — so `phpunit.xml` carries explicit lists:

```xml
<testsuite name="default"><directory>tests</directory></testsuite>
<testsuite name="integration">
    <directory>tests/Api</directory>
    <exclude>tests/Api/SomePureTest.php</exclude>
</testsuite>
<testsuite name="unit">
    <file>tests/Api/SomePureTest.php</file>
</testsuite>
```

Set `defaultTestSuite="default"`. When DB-backed tests live outside `tests/Api` (turbo-habits has
13 under `tests/Service`), the hand-maintained lists rot: copy
[`tests/TestSuiteSplitTest.php`](tests/TestSuiteSplitTest.php) into the project — it fails the
moment a class's base and its suite disagree. With only a handful of pure tests the drift is
self-revealing (a DB test in `unit` fails loudly) and the guard test can be skipped.

## 5. Project docs to write

- `docs/SETUP_AND_RUN_TESTS.md` — one-time setup (MySQL, sqlbackup + uv, the two JSONs, config
  copy, first pull), the runner table with measured times, `SKIP_DB_PULL`, never-two-phpunit,
  why `XDEBUG_MODE=off`, troubleshooting. Copy tickets-api's and adjust names.
- `tests/CLAUDE.md` — note that `tests.bat` drops/recreates the mirror and that a bare
  `php vendor/bin/phpunit` does not refresh it.
- `CLAUDE.md` / `README.md` — the three runner lines.
- `.gitignore` — `tools/_last_test_run.log`.
