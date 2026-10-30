<?php

declare(strict_types=1);

/**
 * Password-protected viewer for logs/fatal.log (see docs/FATAL_ERROR_LOG.md).
 *
 * Plain PHP + inline HTML on purpose: no Twig, Container or autoloader, so the page still works
 * when vendor/ is what is broken.
 * shortcut: no rate limit (the API limiter needs the DB); hash_equals + the admin password are
 * the guard. Add a file-based limiter if this URL gets probed.
 */

require_once __DIR__ . '/../src/Bootstrap/FatalErrorLog.php';

use App\Bootstrap\FatalErrorLog;

$logFile = FatalErrorLog::LOG_FILE;
FatalErrorLog::register();

header('Cache-Control: no-store');
header('X-Robots-Tag: noindex');

$config = require __DIR__ . '/../config/app.php';
$password = isset($_POST['password']) ? (string) $_POST['password'] : null;
$authorized = FatalErrorLog::isAuthorized(is_array($config) ? $config : [], $password);

if ($authorized && ($_POST['action'] ?? '') === 'clear') {
    FatalErrorLog::clear($logFile);
}

if ($password !== null && !$authorized) {
    http_response_code(403);
}

if (($_POST['format'] ?? '') === 'text') {
    header('Content-Type: text/plain; charset=utf-8');
    echo $authorized ? FatalErrorLog::read($logFile) : "Forbidden\n";
    exit;
}

header('Content-Type: text/html; charset=utf-8');
$log = $authorized ? FatalErrorLog::read($logFile) : '';
$e = static fn (string $value): string => htmlspecialchars($value, ENT_QUOTES, 'UTF-8');
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="robots" content="noindex">
    <title>Fatal error log</title>
</head>
<body>
<h1>Fatal error log</h1>
<?php if (!$authorized): ?>
    <?php if ($password !== null): ?><p>Wrong password.</p><?php endif; ?>
    <form method="post">
        <input type="password" name="password" autofocus>
        <button type="submit">Show log</button>
    </form>
<?php else: ?>
    <pre><?= $log === '' ? 'No fatal errors logged.' : $e($log) ?></pre>
    <form method="post">
        <input type="hidden" name="password" value="<?= $e((string) $password) ?>">
        <button type="submit">Refresh</button>
        <button type="submit" name="action" value="clear">Clear log</button>
    </form>
<?php endif; ?>
</body>
</html>
