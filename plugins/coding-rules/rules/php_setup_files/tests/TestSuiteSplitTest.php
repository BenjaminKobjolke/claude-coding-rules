<?php

declare(strict_types=1);

namespace App\Tests;

use App\Tests\TestCase\ApiTestCase;
use PHPUnit\Framework\TestCase;

/**
 * Guards the unit/integration split declared in phpunit.xml.
 *
 * The split is by base class: anything extending ApiTestCase boots the Slim app and needs a
 * real MySQL database, and 13 such files live under tests/Service rather than tests/Api. That
 * cannot be expressed with a #[Group] on ApiTestCase - PHPUnit does not inherit class-level
 * Group attributes from an abstract parent (verified on 12.5.31) - so phpunit.xml carries two
 * hand-maintained path lists. Hand-maintained lists rot: without this test, a new DB-backed
 * Service test would land in the `unit` suite and fail there for no obvious reason.
 */
final class TestSuiteSplitTest extends TestCase
{
    public function testEveryDatabaseBackedTestIsInTheIntegrationSuite(): void
    {
        $projectRoot = dirname(__DIR__);
        $declared = $this->integrationFilesFromPhpunitXml($projectRoot);

        $misplaced = [];
        foreach ($this->testFiles($projectRoot . '/tests') as $relativePath) {
            $class = $this->classForPath($relativePath);
            if (!class_exists($class)) {
                continue;
            }
            $needsDatabase = is_subclass_of($class, ApiTestCase::class);
            $inIntegration = str_starts_with($relativePath, 'tests/Api/')
                || in_array($relativePath, $declared, true);

            if ($needsDatabase !== $inIntegration) {
                $misplaced[] = $needsDatabase
                    ? $relativePath . ' extends ApiTestCase but is NOT in the integration suite'
                    : $relativePath . ' is in the integration suite but does NOT extend ApiTestCase';
            }
        }

        $this->assertSame([], $misplaced, sprintf(
            "phpunit.xml's unit/integration lists have drifted from the code:\n%s\n"
            . 'Add or remove the file in BOTH the integration <file> list and the unit <exclude> list.',
            implode("\n", $misplaced)
        ));
    }

    /** @return string[] Forward-slash paths relative to the project root. */
    private function integrationFilesFromPhpunitXml(string $projectRoot): array
    {
        $xml = simplexml_load_file($projectRoot . '/phpunit.xml');
        self::assertNotFalse($xml, 'phpunit.xml is not readable or not valid XML');

        $files = [];
        foreach ($xml->testsuites->testsuite as $suite) {
            if ((string) $suite['name'] !== 'integration') {
                continue;
            }
            foreach ($suite->file as $file) {
                $files[] = str_replace('\\', '/', trim((string) $file));
            }
        }
        self::assertNotEmpty($files, 'No <file> entries found in the integration testsuite');

        return $files;
    }

    /** @return string[] Forward-slash paths relative to the project root. */
    private function testFiles(string $testsDir): array
    {
        $iterator = new \RecursiveIteratorIterator(new \RecursiveDirectoryIterator($testsDir));
        $projectRoot = dirname($testsDir);

        $paths = [];
        foreach ($iterator as $file) {
            if (!$file->isFile() || !str_ends_with($file->getFilename(), 'Test.php')) {
                continue;
            }
            $paths[] = str_replace('\\', '/', substr($file->getPathname(), strlen($projectRoot) + 1));
        }
        sort($paths);

        return $paths;
    }

    private function classForPath(string $relativePath): string
    {
        // tests/Api/FriendApiTest.php -> App\Tests\Api\FriendApiTest (see autoload-dev in composer.json)
        $withoutExtension = substr($relativePath, 0, -strlen('.php'));

        return 'App\\Tests\\' . str_replace('/', '\\', substr($withoutExtension, strlen('tests/')));
    }
}
