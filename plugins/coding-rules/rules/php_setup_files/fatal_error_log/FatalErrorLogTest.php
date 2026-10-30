<?php

declare(strict_types=1);

namespace App\Tests\Bootstrap;

use App\Bootstrap\FatalErrorLog;
use PHPUnit\Framework\TestCase;

// Loaded by path like public/index.php does: the class must work without the Composer autoloader.
require_once dirname(__DIR__, 2) . '/src/Bootstrap/FatalErrorLog.php';

class FatalErrorLogTest extends TestCase
{
    private string $dir;
    private string $logFile;

    protected function setUp(): void
    {
        $this->dir = sys_get_temp_dir() . '/fatal-log-test-' . bin2hex(random_bytes(8));
        $this->logFile = $this->dir . '/fatal.log';
    }

    protected function tearDown(): void
    {
        @unlink($this->logFile);
        @unlink($this->logFile . FatalErrorLog::ROTATED_SUFFIX);
        @rmdir($this->dir);
    }

    private function fatal(string $message, int $type = E_ERROR): array
    {
        return ['type' => $type, 'message' => $message, 'file' => '/app/vendor/autoload.php', 'line' => 22];
    }

    public function testAppendCreatesDirectoryAndWritesFatalLine(): void
    {
        FatalErrorLog::append($this->logFile, $this->fatal('Class "X" not found'));

        $log = FatalErrorLog::read($this->logFile);
        $this->assertMatchesRegularExpression(
            '/^\S+ Class "X" not found in \/app\/vendor\/autoload\.php:22\n$/',
            $log
        );
    }

    public function testAppendIgnoresNonFatalAndMissingErrors(): void
    {
        FatalErrorLog::append($this->logFile, $this->fatal('just a warning', E_WARNING));
        FatalErrorLog::append($this->logFile, null);

        $this->assertSame('', FatalErrorLog::read($this->logFile));
    }

    public function testAppendRotatesOversizedLogToSingleGeneration(): void
    {
        mkdir($this->dir);
        file_put_contents($this->logFile . FatalErrorLog::ROTATED_SUFFIX, 'older generation');
        file_put_contents($this->logFile, str_repeat('x', FatalErrorLog::MAX_BYTES + 1));

        FatalErrorLog::append($this->logFile, $this->fatal('after rotation'));

        $this->assertSame(FatalErrorLog::MAX_BYTES + 1, filesize($this->logFile . FatalErrorLog::ROTATED_SUFFIX));
        $this->assertStringContainsString('after rotation', FatalErrorLog::read($this->logFile));
        $this->assertLessThan(200, filesize($this->logFile));
    }

    public function testReadMissingFileIsEmpty(): void
    {
        $this->assertSame('', FatalErrorLog::read($this->logFile));
    }

    public function testClearEmptiesLogAndRemovesRotatedGeneration(): void
    {
        FatalErrorLog::append($this->logFile, $this->fatal('to clear'));
        file_put_contents($this->logFile . FatalErrorLog::ROTATED_SUFFIX, 'older generation');

        FatalErrorLog::clear($this->logFile);

        $this->assertSame('', FatalErrorLog::read($this->logFile));
        $this->assertFileDoesNotExist($this->logFile . FatalErrorLog::ROTATED_SUFFIX);
    }

    public function testIsAuthorizedRequiresMatchingNonEmptyPassword(): void
    {
        $config = ['admin_token_password' => 'secret'];

        $this->assertTrue(FatalErrorLog::isAuthorized($config, 'secret'));
        $this->assertFalse(FatalErrorLog::isAuthorized($config, 'wrong'));
        $this->assertFalse(FatalErrorLog::isAuthorized($config, ''));
        $this->assertFalse(FatalErrorLog::isAuthorized($config, null));
        $this->assertFalse(FatalErrorLog::isAuthorized(['admin_token_password' => ''], ''));
        $this->assertFalse(FatalErrorLog::isAuthorized([], 'secret'));
    }
}
