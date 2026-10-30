# Fatal Error Log Setup

Copy the files from this folder into a PHP REST API project:

| Example file | Project location |
|---|---|
| `FatalErrorLog.php` | `src/Bootstrap/FatalErrorLog.php` |
| `fatal-log.php` | `public/fatal-log.php` |
| `FatalErrorLogTest.php` | `tests/Bootstrap/FatalErrorLogTest.php` |
| `FATAL_ERROR_LOG.md` | `docs/FATAL_ERROR_LOG.md` |

The class namespace is `App\Bootstrap`; adjust it to follow the project's PSR-4 root if the project uses a different root. When changing the namespace, update the class reference in `fatal-log.php` and the fully qualified class reference in the `public/index.php` snippet below to match. The test must load the class by path with `require_once`, as shown in the example, so it can run without Composer autoloading the class.

Add these three lines to `public/index.php` immediately after `declare(strict_types=1);`, before the Composer autoloader:

```php
// Before the autoloader: a broken vendor/ can die before the app logger is available.
require_once __DIR__ . '/../src/Bootstrap/FatalErrorLog.php';
\App\Bootstrap\FatalErrorLog::register();
```

Add `admin_token_password` to `config/app.php` and `config/app.example.php` for every authentication variant. Use a long random password. An empty or missing value disables the viewer.

Use `--data-urlencode` for the password so special characters are sent safely:

```bash
curl -s --data-urlencode "password=$ADMIN_PASSWORD" -d format=text https://<host>/fatal-log.php
```
