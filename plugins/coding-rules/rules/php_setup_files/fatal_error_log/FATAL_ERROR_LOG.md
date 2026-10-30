# Fatal Error Log

## Why

A PHP fatal error that happens before Slim runs never reaches the app log or the error
middleware: the client gets an empty `500`, and `logs/app-*.log` stays silent. For example, a half-uploaded `vendor/` can die inside `vendor/autoload.php`.

## What is logged

`public/index.php` registers `App\Bootstrap\FatalErrorLog` (`src/Bootstrap/FatalErrorLog.php`)
**before** the Composer autoloader. At shutdown it appends every `E_ERROR`, `E_PARSE`,
`E_CORE_ERROR` and `E_COMPILE_ERROR` (uncaught exceptions included) to `logs/fatal.log`:

```
<timestamp> Uncaught Error: Class "Composer\Autoload\ComposerStaticInit…" not found in /…/vendor/composer/autoload_real.php:<line>
```

The class uses the PHP standard library only and is loaded with `require_once` by path, so it
works while `vendor/`, the Container or the database are broken. A file over 1 MB is renamed to
`logs/fatal.log.1` (one generation) before the next write.

It does not catch a parse error in `FatalErrorLog.php` itself, or a crash before PHP runs
`index.php` (web server / PHP-FPM errors: ask the host for its error log).

## Viewing it

Open `https://<host>/fatal-log.php` (locally `http://localhost/<project>/fatal-log.php`)
and enter `admin_token_password` from `config/app.php`. The page shows the log, a **Refresh**
button and a **Clear log** button (empties `fatal.log` and deletes `fatal.log.1`).

Plain text, for scripts and Claude:

```bash
curl -s --data-urlencode "password=$ADMIN_PASSWORD" -d format=text https://<host>/fatal-log.php
```

Use `--data-urlencode`: the password may contain characters plain `-d` sends unencoded.

## Security

- The password is only accepted by `POST`, never in the URL, and compared with `hash_equals`.
  An empty or missing `admin_token_password` disables the viewer.
- Wrong password: `403`. Responses carry `Cache-Control: no-store` and `X-Robots-Tag: noindex`.
- No rate limit: the API's limiter needs the database, which this page must not depend on.
  Keep `admin_token_password` long and random.
- The log holds file paths and error messages, no request data.
