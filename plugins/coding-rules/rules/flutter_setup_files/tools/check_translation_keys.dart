// Audit translation keys: detect TK constants pointing to missing i18n
// paths, unused TK constants, orphan i18n leaves with no TK reference,
// and raw `tr('literal')` calls that bypass the TK class.
//
// Run: `tools\check_translation_keys.bat`
//      `tools\check_translation_keys.bat --fix`
//
// `--fix` rewrites every "fixable" raw-literal hit (literal matches an
// existing i18n leaf AND a TK constant points at that leaf) to use the
// matching TK constant. `needs-const` and `broken` literals are report-only —
// they need human judgement.
//
// Detection rules live in translation_key_audit.dart, shared with the two
// pruners; both the modular and single-file i18n layouts are auto-detected.
//
// PER-PROJECT SETUP: fill in `_topKeyToClass` and `_packageName` below. The
// rest of the script needs no editing.
//
// Exit 0 if every category is empty (post-fix when --fix is set), else 1.

import 'dart:io';

import 'translation_key_audit.dart';

/// Top-level i18n key -> owning TK class. `--fix` uses it to decide where a
/// newly created constant belongs; the file name is derived from the class
/// name (`TKAppInfo` -> `tk_app_info.dart`).
///
/// Every top-level key in the i18n source must appear here, or `--fix` skips
/// the literals under the missing key.
const _topKeyToClass = <String, String>{
  'app': 'TKCore',
  'auth': 'TKCore',
  'common': 'TKCore',
  'nav': 'TKCore',
};

/// Package name from pubspec.yaml, used by `--fix` to add the barrel import.
const _packageName = 'my_app';

void main(List<String> args) async {
  final fix = args.contains('--fix');
  final root = Directory.current.path;

  final layout = I18nLayout.detect(root);
  final leafPaths = layout.loadLeaves();
  final tkConsts = loadTkConsts(root);
  final scan = await scanCallers(root);

  // 1. Missing: a constant whose i18n path does not exist. A `...Prefix`
  //    constant is satisfied by any leaf below it.
  final missing = <TkConst>[];
  for (final c in tkConsts) {
    if (leafPaths.contains(c.value)) continue;
    if (c.isPrefix && leafPaths.any((leaf) => leaf.startsWith(c.value))) {
      continue;
    }
    missing.add(c);
  }

  // 2. Reverse map: i18n value -> TK const. If several constants share a
  //    value, prefer the first encountered (stable).
  final valueToTk = <String, TkConst>{};
  for (final c in tkConsts) {
    valueToTk.putIfAbsent(c.value, () => c);
  }

  // 3. Bucket the raw literals.
  final fixableHits = <RawHit>[];
  final needsConstHits = <RawHit>[];
  final brokenHits = <RawHit>[];
  for (final h in scan.rawHits) {
    if (valueToTk.containsKey(h.literal)) {
      fixableHits.add(h);
    } else if (leafPaths.contains(h.literal)) {
      needsConstHits.add(h);
    } else {
      brokenHits.add(h);
    }
  }

  // 4. Unused constants.
  final unused =
      tkConsts.where((c) => !scan.references.contains(c.qualifiedName)).toList();

  // 5. Orphan leaves: no TK constant, no raw caller, not under a prefix.
  final tkValues = tkConsts.map((c) => c.value).toSet();
  final rawLiterals = scan.rawHits.map((h) => h.literal).toSet();
  final orphans = leafPaths
      .where((p) =>
          !tkValues.contains(p) &&
          !rawLiterals.contains(p) &&
          !coveredByPrefix(p, tkConsts))
      .toList()
    ..sort();

  // 6. Apply --fix:
  //    a) auto-create TK consts for needs-const hits and promote them to
  //       fixable;
  //    b) rewrite every fixable raw literal to use the TK const.
  var rewrites = 0;
  var touchedFiles = 0;
  var createdConsts = 0;
  if (fix && needsConstHits.isNotEmpty) {
    final byClass = <String, List<TkConst>>{};
    final pathToTkPending = <String, TkConst>{};
    final usedNames = <String, Set<String>>{};
    for (final c in tkConsts) {
      usedNames.putIfAbsent(c.className, () => <String>{}).add(c.name);
    }
    for (final path in needsConstHits.map((h) => h.literal).toSet()) {
      final topKey = path.split('.').first;
      final cls = _topKeyToClass[topKey];
      if (cls == null) {
        stderr.writeln("  no TK class mapped for '$topKey'; skipping $path");
        continue;
      }
      final base = _camelFromPath(path);
      final used = usedNames.putIfAbsent(cls, () => <String>{});
      var name = base;
      var n = 2;
      while (used.contains(name)) {
        name = '$base${n++}';
      }
      used.add(name);
      final pending = TkConst(cls, name, path, _tkFilePath(root, cls));
      byClass.putIfAbsent(cls, () => []).add(pending);
      pathToTkPending[path] = pending;
    }
    // Append decls to each sub-file, before the closing `}` of the class.
    for (final entry in byClass.entries) {
      final file = File(_tkFilePath(root, entry.key));
      final src = file.readAsStringSync();
      final lastBrace = src.lastIndexOf('}');
      if (lastBrace == -1) continue;
      final additions = StringBuffer();
      for (final c in entry.value) {
        additions.writeln("  static const String ${c.name} = '${c.value}';");
        createdConsts++;
      }
      file.writeAsStringSync(
        '${src.substring(0, lastBrace)}$additions${src.substring(lastBrace)}',
      );
    }
    for (final h in needsConstHits) {
      final tk = pathToTkPending[h.literal];
      if (tk == null) continue;
      valueToTk[h.literal] = tk;
      fixableHits.add(h);
    }
    needsConstHits.removeWhere((h) => pathToTkPending.containsKey(h.literal));
  }

  if (fix && fixableHits.isNotEmpty) {
    final byFile = <String, List<RawHit>>{};
    for (final h in fixableHits) {
      byFile.putIfAbsent(h.filePath, () => []).add(h);
    }
    for (final entry in byFile.entries) {
      var src = File(entry.key).readAsStringSync();
      // Apply substitutions right-to-left so offsets stay valid.
      final hits = entry.value
        ..sort((a, b) => b.literalStart.compareTo(a.literalStart));
      for (final h in hits) {
        final tk = valueToTk[h.literal]!;
        // Only the quoted literal is replaced, so a `_tr(...)` call site
        // keeps its wrapper.
        src = src.replaceRange(h.literalStart, h.literalEnd, tk.qualifiedName);
        rewrites++;
      }
      src = _ensureBarrelImport(src);
      File(entry.key).writeAsStringSync(src);
      touchedFiles++;
    }
  }

  // 7. Report.
  final out = StringBuffer()
    ..writeln('=== Translation key audit ===')
    ..writeln()
    ..writeln('i18n layout: ${layout.isModular ? 'modular' : 'single-file'} | '
        'locales: ${layout.locales.join(', ')}')
    ..writeln(
      'TK constants: ${tkConsts.length} | i18n leaves: ${leafPaths.length}',
    )
    ..writeln()
    ..writeln('--- Missing i18n paths (${missing.length}) ---');
  for (final c in missing) {
    out.writeln('  ${c.qualifiedName}  ->  ${c.value}');
  }
  out
    ..writeln()
    ..writeln('--- Unused TK constants (${unused.length}) ---');
  for (final c in unused) {
    out.writeln('  ${c.qualifiedName}  =  ${c.value}');
  }
  out
    ..writeln()
    ..writeln('--- Orphan i18n leaves (${orphans.length}) ---');
  for (final p in orphans) {
    out.writeln('  $p');
  }
  out
    ..writeln()
    ..writeln(
      '--- Raw tr() literals (fixable ${fixableHits.length} / '
      'needs-const ${needsConstHits.length} / broken ${brokenHits.length}) ---',
    );
  for (final h in fixableHits) {
    out.writeln(
      "  [fixable]      ${h.filePath}:${h.line}  '${h.literal}'"
      '  -> ${valueToTk[h.literal]!.qualifiedName}',
    );
  }
  for (final h in needsConstHits) {
    out.writeln(
      "  [needs-const]  ${h.filePath}:${h.line}  '${h.literal}'"
      '  (i18n leaf exists; add TK const)',
    );
  }
  for (final h in brokenHits) {
    out.writeln(
      "  [broken]       ${h.filePath}:${h.line}  '${h.literal}'"
      '  (no matching i18n leaf)',
    );
  }
  if (fix) {
    out
      ..writeln()
      ..writeln('Created $createdConsts new TK constants; rewrote $rewrites '
          'call sites across $touchedFiles files.');
  }
  stdout.write(out.toString());

  final hasIssues = missing.isNotEmpty ||
      unused.isNotEmpty ||
      orphans.isNotEmpty ||
      (!fix && fixableHits.isNotEmpty) ||
      needsConstHits.isNotEmpty ||
      brokenHits.isNotEmpty;
  exit(hasIssues ? 1 : 0);
}

/// Adds the translation_keys barrel import to [src] when it is missing.
String _ensureBarrelImport(String src) {
  if (src.contains('config/translation_keys.dart')) return src;
  final line = "import 'package:$_packageName/config/translation_keys.dart';\n";
  final imports =
      RegExp(r"^import\s+'[^']+';\s*$", multiLine: true).allMatches(src).toList();
  if (imports.isEmpty) return '$line$src';
  final pos = imports.last.end;
  return '${src.substring(0, pos)}\n$line${src.substring(pos)}';
}

/// `TKAppInfo` -> `<root>/lib/config/translation_keys/tk_app_info.dart`.
String _tkFilePath(String root, String className) {
  final snake = className
      .replaceAllMapped(RegExp(r'(?<=[a-z0-9])([A-Z])'), (m) => '_${m.group(1)}')
      .toLowerCase();
  return '$root/lib/config/translation_keys/$snake.dart';
}

/// `habits.enter_value_hint` -> `habitsEnterValueHint`. Both dots and
/// underscores are segment separators, matching the existing constant names.
String _camelFromPath(String path) {
  final parts = path.split(RegExp(r'[._]')).where((s) => s.isNotEmpty).toList();
  final buf = StringBuffer(parts.first);
  for (final seg in parts.skip(1)) {
    buf.write(seg[0].toUpperCase());
    if (seg.length > 1) buf.write(seg.substring(1));
  }
  return buf.toString();
}
