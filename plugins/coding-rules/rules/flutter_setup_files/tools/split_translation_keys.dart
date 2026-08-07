// Codemod: split lib/config/translation_keys.dart into per-i18n-module files.
//
// Reads assets/i18n/modules.json, derives topKey -> module map from each
// module's en.json, parses the current TK class, emits one sub-class per
// module under lib/config/translation_keys/, rewrites translation_keys.dart
// as a barrel, and rewrites every `TK.foo` reference in lib/ and test/ to
// the matching `TKModule.foo`.
//
// Run from project root: `dart run tools/split_translation_keys.dart`
// (or `fvm dart run tools/split_translation_keys.dart`).

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

class _Constant {
  _Constant(this.name, this.value, this.topKey, this.section);
  final String name;
  final String value;
  final String topKey;
  final String section; // preceding // comment text (may be empty)
}

Future<void> main() async {
  final projectRoot = Directory.current.path;
  final i18nDir = File('$projectRoot/assets/i18n/modules.json');
  if (!await i18nDir.exists()) {
    stderr.writeln('modules.json not found at ${i18nDir.path}');
    exit(1);
  }

  final modules =
      (jsonDecode(await i18nDir.readAsString()) as List).cast<String>();

  // 1. topKey -> module
  final topKeyToModule = <String, String>{};
  for (final mod in modules) {
    final en = File('$projectRoot/assets/i18n/$mod/en.json');
    final data = jsonDecode(await en.readAsString()) as Map<String, dynamic>;
    for (final k in data.keys) {
      if (k.startsWith('_')) continue; // skip _hint_
      topKeyToModule[k] = mod;
    }
  }

  // 2. Parse current TK file.
  final tkFile = File('$projectRoot/lib/config/translation_keys.dart');
  if (!await tkFile.exists()) {
    stderr.writeln('translation_keys.dart not found');
    exit(1);
  }
  final tkText = await tkFile.readAsString();

  // Normalize: collapse multi-line `static const String X = '...';` to one line.
  final normalized = tkText.replaceAllMapped(
    RegExp(
      r"static\s+const\s+String\s+(\w+)\s*=\s*'([^']+)'\s*;",
      multiLine: true,
    ),
    (m) => "static const String ${m.group(1)} = '${m.group(2)}';",
  );

  final lines = normalized.split(RegExp(r'\r?\n'));
  final constants = <_Constant>[];
  String currentSection = '';
  final declRe = RegExp(
    r"^\s*static\s+const\s+String\s+(\w+)\s*=\s*'([^']+)'\s*;",
  );
  final commentRe = RegExp(r"^\s*//\s*(.*)$");
  for (final line in lines) {
    final dm = declRe.firstMatch(line);
    if (dm != null) {
      final name = dm.group(1)!;
      final value = dm.group(2)!;
      final topKey = value.split('.').first;
      constants.add(_Constant(name, value, topKey, currentSection));
      continue;
    }
    final cm = commentRe.firstMatch(line);
    if (cm != null) {
      currentSection = cm.group(1)!.trim();
      continue;
    }
    if (line.trim().isEmpty) {
      // blank line ends section influence — keep currentSection until next comment;
      // simpler: do nothing.
    }
  }

  stderr.writeln('Parsed ${constants.length} TK constants.');

  // 3. Group by module. Unknown top-keys fall back to 01_core with a warning.
  final byModule = <String, List<_Constant>>{};
  for (final c in constants) {
    final mod = topKeyToModule[c.topKey] ?? '01_core';
    if (topKeyToModule[c.topKey] == null) {
      stderr.writeln(
        'WARNING: top-key "${c.topKey}" not in any i18n module — '
        'placing ${c.name} in TKCore.',
      );
    }
    byModule.putIfAbsent(mod, () => []).add(c);
  }

  // 4. name -> className map.
  final nameToClass = <String, String>{};
  for (final entry in byModule.entries) {
    final cls = _moduleClassNames[entry.key]!;
    for (final c in entry.value) {
      nameToClass[c.name] = cls;
    }
  }

  // 5. Emit sub-class files.
  final outDir = Directory('$projectRoot/lib/config/translation_keys');
  if (!await outDir.exists()) {
    await outDir.create(recursive: true);
  }
  for (final mod in modules) {
    final list = byModule[mod] ?? const <_Constant>[];
    if (list.isEmpty) continue;
    final cls = _moduleClassNames[mod]!;
    final file = File('${outDir.path}/${_moduleFileNames[mod]!}');
    final buf = StringBuffer();
    buf.writeln(
      '// Generated from assets/i18n/$mod/en.json — do not edit manually.',
    );
    buf.writeln('// Regenerate via tools/split_translation_keys.dart.');
    buf.writeln();
    buf.writeln('class $cls {');
    buf.writeln('  $cls._();');
    buf.writeln();
    String lastSection = '';
    for (final c in list) {
      if (c.section != lastSection && c.section.isNotEmpty) {
        buf.writeln('  // ${c.section}');
        lastSection = c.section;
      }
      buf.writeln("  static const String ${c.name} = '${c.value}';");
    }
    buf.writeln('}');
    await file.writeAsString(buf.toString());
    stderr.writeln('Wrote ${file.path} (${list.length} keys, class $cls).');
  }

  // 6. Rewrite barrel.
  final barrelBuf = StringBuffer();
  barrelBuf.writeln(
    '// Translation key barrel. Generated by tools/split_translation_keys.dart.',
  );
  barrelBuf.writeln(
    '// Edit the per-module files under translation_keys/ (or rerun the script).',
  );
  barrelBuf.writeln();
  for (final mod in modules) {
    if (!byModule.containsKey(mod)) continue;
    barrelBuf.writeln("export 'translation_keys/${_moduleFileNames[mod]!}';");
  }
  await tkFile.writeAsString(barrelBuf.toString());
  stderr.writeln('Rewrote barrel ${tkFile.path}.');

  // 7. Walk lib/ and test/ and rewrite TK.foo references.
  final targets = <Directory>[
    Directory('$projectRoot/lib'),
    Directory('$projectRoot/test'),
  ];
  final refRe = RegExp(r'\bTK\.([A-Za-z_][A-Za-z0-9_]*)\b');
  var filesTouched = 0;
  var replacements = 0;
  final missingNames = <String>{};
  for (final root in targets) {
    if (!await root.exists()) continue;
    await for (final ent in root.list(recursive: true, followLinks: false)) {
      if (ent is! File) continue;
      if (!ent.path.endsWith('.dart')) continue;
      // Skip the translation_keys files themselves.
      final p = ent.path.replaceAll('\\', '/');
      if (p.endsWith('lib/config/translation_keys.dart')) continue;
      if (p.contains('/lib/config/translation_keys/')) continue;
      final src = await ent.readAsString();
      if (!src.contains('TK.')) continue;
      var fileChanged = false;
      final rewritten = src.replaceAllMapped(refRe, (m) {
        final name = m.group(1)!;
        final cls = nameToClass[name];
        if (cls == null) {
          missingNames.add(name);
          return m.group(0)!;
        }
        replacements++;
        fileChanged = true;
        return '$cls.$name';
      });
      if (fileChanged) {
        await ent.writeAsString(rewritten);
        filesTouched++;
      }
    }
  }
  stderr.writeln(
    'Rewrote $replacements references across $filesTouched files.',
  );
  if (missingNames.isNotEmpty) {
    stderr.writeln(
      'WARNING: ${missingNames.length} TK.<name> references had no matching constant:',
    );
    for (final n in missingNames) {
      stderr.writeln('  TK.$n');
    }
    exit(3);
  }
  stderr.writeln('Done.');
}
