<?php

declare(strict_types=1);

/**
 * Rector config template.
 *
 * Edit per project:
 *   - withPhpVersion()  : target PHP version
 *   - withPaths()       : project code dirs to process
 *   - withSkip()        : vendored libs, generated code, view templates
 *   - withRules()       : start with the three named rules below; add more
 *                         only as deprecation notices surface in tests.
 *                         Avoid withPhpSets() — too aggressive.
 */

use Rector\Config\RectorConfig;
use Rector\Php81\Rector\FuncCall\NullToStrictStringFuncCallArgRector;
use Rector\Php82\Rector\FuncCall\Utf8DecodeEncodeToMbConvertEncodingRector;
use Rector\Php84\Rector\Param\ExplicitNullableParamTypeRector;
use Rector\ValueObject\PhpVersion;

// Resolve paths against the repo root (this config lives in tools/).
$root = dirname(__DIR__);

return RectorConfig::configure()
    ->withPhpVersion(PhpVersion::PHP_85)
    ->withPaths([
        $root . '/src',
        // $root . '/app',
    ])
    ->withSkip([
        $root . '/vendor',
        $root . '/cache',
        // $root . '/views',     // template files
        // $root . '/src/libs',  // bundled third-party code
    ])
    ->withRules([
        // PHP 8.1+ — null passed to internal string funcs is deprecated.
        NullToStrictStringFuncCallArgRector::class,
        // PHP 8.2+ — utf8_encode/decode deprecated.
        Utf8DecodeEncodeToMbConvertEncodingRector::class,
        // PHP 8.4+ — implicit nullable params deprecated.
        ExplicitNullableParamTypeRector::class,
    ]);
