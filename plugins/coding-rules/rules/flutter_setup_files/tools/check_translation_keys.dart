// Audit translation keys: detect TK constants pointing to missing i18n
// paths, unused TK constants, orphan i18n leaves with no TK reference,
// and raw `AppLocalizations.tr('literal')` calls that bypass the TK class.
//
// Run: `fvm dart run tools/check_translation_keys.dart`
//      `fvm dart run tools/check_translation_keys.dart --fix`
//
// `--fix` rewrites every "fixable" raw-literal hit (literal matches an
// existing i18n leaf AND a TK constant points at that leaf) to use the
// matching TK constant. `needs-const` and `broken` literals are
// report-only — they need human judgement.
//
// Exit 0 if every category is empty (post-fix when --fix is set), else 1.

import 'dart:convert';
import 'dart:io';

const _moduleClassNames = <String, String>{
  '01_core': 'TKCore',
  '02_browser': 'TKBrowser',
  '03_file_operations': 'TKFileOps',
  '04_favorites': 'TKFavorites',
  '05_settings': 'TKSettings',
  '06_tools_editors': 'TKToolsEditors',
  '07_tools_utilities': 'TKToolsUtilities',
  '08_tools_connections': 'TKToolsConnections',
  '09_tools_ai': 'TKToolsAi',
  '10_downloads': 'TKDownloads',
};

const _moduleFileNames = <String, String>{
  '01_core': 'tk_core.dart',
  '02_browser': 'tk_browser.dart',
  '03_file_operations': 'tk_file_ops.dart',
  '04_favorites': 'tk_favorites.dart',
  '05_settings': 'tk_settings.dart',
  '06_tools_editors': 'tk_tools_editors.dart',
  '07_tools_utilities': 'tk_tools_utilities.dart',
  '08_tools_connections': 'tk_tools_connections.dart',
  '09_tools_ai': 'tk_tools_ai.dart',
  '10_downloads': 'tk_downloads.dart',
};

void main(List<String> args) async {
  final fix = args.contains('--fix');
  final root = Directory.current.path;

  // 1. Load i18n modules → leaf path set + topKey -> module.
  final modulesFile = File('$root/assets/i18n/modules.json');
  if (!modulesFile.existsSync()) {
    stderr.writeln('modules.json not found at ${modulesFile.path}');
    exit(2);
  }
  final modules =
      (jsonDecode(modulesFile.readAsStringSync()) as List).cast<String>();
  final leafPaths = <String>{};
  final topKeyToModule = <String, String>{};
  for (final mod in modules) {
    final f = File('$root/assets/i18n/$mod/en.json');
    final data = jsonDecode(f.readAsStringSync()) as Map<String, dynamic>;
    for (final k in data.keys) {
      if (k == '_hint_') continue;
      topKeyToModule[k] = mod;
    }
    _flatten(data, '', leafPaths);
  }

  // 2. Parse TK files.
  final tkDir = Directory('$root/lib/config/translation_keys');
  if (!tkDir.existsSync()) {
    stderr.writeln('TK dir not found at ${tkDir.path}');
    exit(2);
  }
  final declRe = RegExp(
    r"static\s+const\s+String\s+(\w+)\s*=\s*'([^']+)'\s*;",
  );
  final classRe = RegExp(r'^\s*class\s+(\w+)\s*\{', multiLine: true);
  final tkConsts = <_TkConst>[];
  for (final ent in tkDir.listSync()) {
    if (ent is! File || !ent.path.endsWith('.dart')) continue;
    final src = ent.readAsStringSync();
    final cm = classRe.firstMatch(src);
    if (cm == null) continue;
    final className = cm.group(1)!;
    for (final m in declRe.allMatches(src)) {
      tkConsts.add(_TkConst(className, m.group(1)!, m.group(2)!, ent.path));
    }
  }

  // 3. Missing.
  final missing = <_TkConst>[];
  for (final c in tkConsts) {
    if (!leafPaths.contains(c.value)) missing.add(c);
  }

  // 4. Reverse map: i18n value -> (className, constName). If multiple TK
  // consts share the same value, prefer the first encountered (stable).
  final valueToTk = <String, _TkConst>{};
  for (final c in tkConsts) {
    valueToTk.putIfAbsent(c.value, () => c);
  }

  // 5. Scan callers for TK references AND raw-literal tr() calls.
  final tkRefs = <String>{};
  final refRe = RegExp(r'\b(TK[A-Za-z]+)\.([A-Za-z_][A-Za-z0-9_]*)\b');
  final rawRe = RegExp(r"AppLocalizations\.tr\(\s*'([^']+)'");
  final searchRoots = [Directory('$root/lib'), Directory('$root/test')];

  final fixableHits = <_RawHit>[];
  final needsConstHits = <_RawHit>[];
  final brokenHits = <_RawHit>[];

  for (final r in searchRoots) {
    if (!r.existsSync()) continue;
    await for (final ent in r.list(recursive: true, followLinks: false)) {
      if (ent is! File || !ent.path.endsWith('.dart')) continue;
      final p = ent.path.replaceAll('\\', '/');
      if (p.contains('/lib/config/translation_keys/')) continue;
      if (p.endsWith('/lib/config/translation_keys.dart')) continue;
      final src = ent.readAsStringSync();

      for (final m in refRe.allMatches(src)) {
        tkRefs.add('${m.group(1)}.${m.group(2)}');
      }

      for (final m in rawRe.allMatches(src)) {
        final literal = m.group(1)!;
        if (literal.contains(r'${') || literal.contains(r'$')) continue;
        final line = '\n'.allMatches(src.substring(0, m.start)).length + 1;
        final hit = _RawHit(ent.path, line, literal, m.start, m.end);
        if (valueToTk.containsKey(literal)) {
          fixableHits.add(hit);
        } else if (leafPaths.contains(literal)) {
          needsConstHits.add(hit);
        } else {
          brokenHits.add(hit);
        }
      }
    }
  }

  // 6. Unused.
  final unused = <_TkConst>[];
  for (final c in tkConsts) {
    if (!tkRefs.contains('${c.className}.${c.name}')) unused.add(c);
  }

  // 7. Orphan leaves.
  final tkValues = tkConsts.map((c) => c.value).toSet();
  final orphans = <String>[];
  for (final path in leafPaths) {
    if (!tkValues.contains(path)) orphans.add(path);
  }
  orphans.sort();

  // 8. Apply --fix:
  //    a) auto-create TK consts for needs-const hits and promote them to
  //       fixable;
  //    b) rewrite every fixable raw-literal call to use the TK const.
  var rewrites = 0;
  var touchedFiles = 0;
  var createdConsts = 0;
  if (fix && needsConstHits.isNotEmpty) {
    // Group needed paths by module; build name + class lookups.
    final byModule = <String, List<String>>{};
    final pathToTkPending = <String, _TkConst>{};
    final usedNames = <String, Set<String>>{};
    for (final c in tkConsts) {
      usedNames.putIfAbsent(c.className, () => <String>{}).add(c.name);
    }
    final uniqueLiterals = needsConstHits.map((h) => h.literal).toSet();
    for (final path in uniqueLiterals) {
      final top = path.split('.').first;
      final mod = topKeyToModule[top];
      if (mod == null) continue;
      final cls = _moduleClassNames[mod];
      if (cls == null) continue;
      final base = _camelFromPath(path);
      final used = usedNames.putIfAbsent(cls, () => <String>{});
      var name = base;
      var n = 2;
      while (used.contains(name)) {
        name = '$base$n';
        n++;
      }
      used.add(name);
      byModule.putIfAbsent(mod, () => []).add('$name|$path');
      pathToTkPending[path] =
          _TkConst(cls, name, path, '$root/lib/config/translation_keys/${_moduleFileNames[mod]}');
    }
    // Append decls to each sub-file (before the closing `}` of the class).
    for (final entry in byModule.entries) {
      final file = File(
        '$root/lib/config/translation_keys/${_moduleFileNames[entry.key]}',
      );
      var src = file.readAsStringSync();
      final lastBrace = src.lastIndexOf('}');
      if (lastBrace == -1) continue;
      final additions = StringBuffer();
      for (final spec in entry.value) {
        final parts = spec.split('|');
        additions.writeln("  static const String ${parts[0]} = '${parts[1]}';");
        createdConsts++;
      }
      final newSrc = '${src.substring(0, lastBrace)}$additions${src.substring(lastBrace)}';
      file.writeAsStringSync(newSrc);
    }
    // Move needs-const hits into fixable using the pending TK map.
    for (final h in needsConstHits) {
      final tk = pathToTkPending[h.literal];
      if (tk != null) {
        valueToTk[h.literal] = tk;
        fixableHits.add(h);
      }
    }
    needsConstHits.removeWhere((h) => pathToTkPending.containsKey(h.literal));
  }

  if (fix && fixableHits.isNotEmpty) {
    final byFile = <String, List<_RawHit>>{};
    for (final h in fixableHits) {
      byFile.putIfAbsent(h.filePath, () => []).add(h);
    }
    for (final entry in byFile.entries) {
      final src = File(entry.key).readAsStringSync();
      // Apply substitutions right-to-left so offsets stay valid.
      final hits = entry.value..sort((a, b) => b.matchStart.compareTo(a.matchStart));
      var newSrc = src;
      for (final h in hits) {
        final tk = valueToTk[h.literal]!;
        final replacement = "AppLocalizations.tr(${tk.className}.${tk.name}";
        newSrc = newSrc.replaceRange(h.matchStart, h.matchEnd, replacement);
        rewrites++;
      }
      // Ensure the translation_keys barrel import exists.
      if (!newSrc.contains("config/translation_keys.dart")) {
        final importLine =
            "import 'package:android_folder_gallery/config/translation_keys.dart';\n";
        final lastImport = RegExp(r"^import\s+'[^']+';\s*$",
                multiLine: true)
            .allMatches(newSrc)
            .toList();
        if (lastImport.isNotEmpty) {
          final pos = lastImport.last.end;
          newSrc = '${newSrc.substring(0, pos)}\n$importLine${newSrc.substring(pos)}';
        } else {
          newSrc = '$importLine$newSrc';
        }
      }
      File(entry.key).writeAsStringSync(newSrc);
      touchedFiles++;
    }
  }

  // 9. Report.
  final out = StringBuffer();
  out.writeln('=== Translation key audit ===');
  out.writeln();
  out.writeln(
    'TK constants: ${tkConsts.length} | i18n leaves: ${leafPaths.length}',
  );
  out.writeln();
  out.writeln('--- Missing i18n paths (${missing.length}) ---');
  for (final c in missing) {
    out.writeln('  ${c.className}.${c.name}  ->  ${c.value}');
  }
  out.writeln();
  out.writeln('--- Unused TK constants (${unused.length}) ---');
  for (final c in unused) {
    out.writeln('  ${c.className}.${c.name}  =  ${c.value}');
  }
  out.writeln();
  out.writeln('--- Orphan i18n leaves (${orphans.length}) ---');
  for (final p in orphans) {
    out.writeln('  $p');
  }
  out.writeln();
  out.writeln(
    '--- Raw tr() literals (fixable ${fixableHits.length} / '
    'needs-const ${needsConstHits.length} / broken ${brokenHits.length}) ---',
  );
  for (final h in fixableHits) {
    final tk = valueToTk[h.literal]!;
    out.writeln(
      "  [fixable]      ${h.filePath}:${h.line}  '${h.literal}'  -> ${tk.className}.${tk.name}",
    );
  }
  for (final h in needsConstHits) {
    out.writeln(
      "  [needs-const]  ${h.filePath}:${h.line}  '${h.literal}'  (i18n leaf exists; add TK const)",
    );
  }
  for (final h in brokenHits) {
    out.writeln(
      "  [broken]       ${h.filePath}:${h.line}  '${h.literal}'  (no matching i18n leaf)",
    );
  }
  if (fix) {
    out.writeln();
    out.writeln(
      'Created $createdConsts new TK constants; rewrote $rewrites call sites across $touchedFiles files.',
    );
  }
  stdout.write(out.toString());

  final stillFixable = fix ? 0 : fixableHits.length;
  final hasIssues = missing.isNotEmpty ||
      unused.isNotEmpty ||
      orphans.isNotEmpty ||
      stillFixable > 0 ||
      needsConstHits.isNotEmpty ||
      brokenHits.isNotEmpty;
  exit(hasIssues ? 1 : 0);
}

String _camelFromPath(String path) {
  final parts = path.split('.');
  final buf = StringBuffer(parts.first);
  for (var i = 1; i < parts.length; i++) {
    final seg = parts[i];
    if (seg.isEmpty) continue;
    buf.write(seg[0].toUpperCase());
    if (seg.length > 1) buf.write(seg.substring(1));
  }
  return buf.toString();
}

void _flatten(Map<String, dynamic> node, String prefix, Set<String> out) {
  node.forEach((k, v) {
    if (k == '_hint_') return;
    final path = prefix.isEmpty ? k : '$prefix.$k';
    if (v is Map<String, dynamic>) {
      _flatten(v, path, out);
    } else if (v is String) {
      out.add(path);
    }
  });
}

class _TkConst {
  _TkConst(this.className, this.name, this.value, this.sourcePath);
  final String className;
  final String name;
  final String value;
  final String sourcePath;
}

class _RawHit {
  _RawHit(this.filePath, this.line, this.literal, this.matchStart, this.matchEnd);
  final String filePath;
  final int line;
  final String literal;
  final int matchStart;
  final int matchEnd;
}
