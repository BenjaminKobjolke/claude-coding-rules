<?php

declare(strict_types=1);

namespace App\Bootstrap;

/**
 * Records PHP fatal errors to a plain file and guards the viewer in public/fatal-log.php.
 *
 * Deliberately standalone (standard library only, loaded with require_once by path): it has to
 * work exactly when vendor/, the Container or the Logger are broken, e.g. a half-uploaded
 * vendor/ that dies inside vendor/autoload.php before anything else can log.
 */
final class FatalErrorLog
{
    // Fixed path, not config logging.path: it is registered before config/app.php can be read.
    public const LOG_FILE = __DIR__ . '/../../logs/fatal.log';
    public const MAX_BYTES = 1048576;
    public const PASSWORD_CONFIG_KEY = 'admin_token_password';
    public const ROTATED_SUFFIX = '.1';
    private const FATAL_TYPES = [E_ERROR, E_PARSE, E_CORE_ERROR, E_COMPILE_ERROR];

    public static function register(string $logFile = self::LOG_FILE): void
    {
        register_shutdown_function(static fn () => self::append($logFile, error_get_last()));
    }

    /** @param array{type: int, message: string, file: string, line: int}|null $error */
    public static function append(string $logFile, ?array $error): void
    {
        if ($error === null || !in_array($error['type'], self::FATAL_TYPES, true)) {
            return;
        }

        $dir = dirname($logFile);
        if (!is_dir($dir)) {
            @mkdir($dir, 0755, true);
        }
        if (is_file($logFile) && filesize($logFile) > self::MAX_BYTES) {
            @rename($logFile, $logFile . self::ROTATED_SUFFIX);
        }

        $line = date('c') . " {$error['message']} in {$error['file']}:{$error['line']}\n";
        // @: a failing write must never turn the original fatal into a second one.
        @file_put_contents($logFile, $line, FILE_APPEND | LOCK_EX);
    }

    public static function read(string $logFile): string
    {
        return is_file($logFile) ? (string) file_get_contents($logFile) : '';
    }

    public static function clear(string $logFile): void
    {
        if (is_file($logFile)) {
            file_put_contents($logFile, '', LOCK_EX);
        }
        @unlink($logFile . self::ROTATED_SUFFIX);
    }

    /** @param array<string, mixed> $config */
    public static function isAuthorized(array $config, ?string $password): bool
    {
        $expected = (string) ($config[self::PASSWORD_CONFIG_KEY] ?? '');

        return $password !== null && $password !== '' && $expected !== '' && hash_equals($expected, $password);
    }
}
