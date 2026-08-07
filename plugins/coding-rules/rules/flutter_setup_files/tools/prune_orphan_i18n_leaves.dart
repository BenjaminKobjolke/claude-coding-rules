// Remove i18n leaves that have no TK constant pointing at them.
//
// 1. Re-runs the orphan detection from check_translation_keys.dart.
// 2. Removes each orphan dotted path from `assets/i18n/<module>/en.json`
//    and `de.json` only (other locales handled by translator).
// 3. Appends every removed path to `tools/attributes_to_remove.json` so
//    `translator_remove_json_attribute_app-texts.bat` can fan out the
//    removal to the remaining locale files.
//
// Run: `fvm dart run tools/prune_orphan_i18n_leaves.dart`

import 'dart:convert';
import 'dart:io';

void main() async {
  final root = Directory.current.path;
  final modules =
      (jsonDecode(File('$root/assets/i18n/modules.json').readAsStringSync())
              as List)
          .cast<String>();

  // 1. Flatten en.json of every module → leafPath set + topKey→module.
  final allLeaves = <String>{};
  final topKeyToModule = <String, String>{};
  for (final mod in modules) {
    final data = jsonDecode(
      File('$root/assets/i18n/$mod/en.json').readAsStringSync(),
    ) as Map<String, dynamic>;
    for (final k in data.keys) {
      if (k == '_hint_') continue;
      topKeyToModule[k] = mod;
    }
    _flatten(data, '', allLeaves);
  }

  // 2. Collect TK constant values.
  final tkDir = Directory('$root/lib/config/translation_keys');
  final valRe = RegExp(r"'([^']+)'");
  final declRe = RegExp(r"static\s+const\s+String\s+\w+\s*=");
  final tkValues = <String>{};
  for (final ent in tkDir.listSync()) {
    if (ent is! File || !ent.path.endsWith('.dart')) continue;
    final src = ent.readAsStringSync();
    // Each decl line (or its 2-line variant) has exactly one quoted string.
    for (final m in declRe.allMatches(src)) {
      final rest = src.substring(m.end);
      final v = valRe.firstMatch(rest);
      if (v != null) tkValues.add(v.group(1)!);
    }
  }

  // 2b. Also collect raw-literal `AppLocalizations.tr('foo.bar')` usages so
  // we don't strip leaves that have a hard-coded caller.
  final rawRefs = <String>{};
  final rawRe = RegExp(r"AppLocalizations\.tr\(\s*'([^']+)'");
  for (final r in [Directory('$root/lib'), Directory('$root/test')]) {
    if (!r.existsSync()) continue;
    await for (final ent in r.list(recursive: true, followLinks: false)) {
      if (ent is! File || !ent.path.endsWith('.dart')) continue;
      final p = ent.path.replaceAll('\\', '/');
      if (p.contains('/lib/config/translation_keys/')) continue;
      if (p.endsWith('/lib/config/translation_keys.dart')) continue;
      for (final m in rawRe.allMatches(ent.readAsStringSync())) {
        final lit = m.group(1)!;
        if (lit.contains(r'$')) continue;
        rawRefs.add(lit);
      }
    }
  }

  // 3. Orphan = leaves minus tkValues minus rawRefs.
  final referenced = {...tkValues, ...rawRefs};
  final orphans = allLeaves.difference(referenced).toList()..sort();
  stderr.writeln('Found ${orphans.length} orphan leaves.');
  if (orphans.isEmpty) return;

  // 4. Remove each orphan from en.json + de.json of its module.
  final byModule = <String, List<List<String>>>{}; // mod -> list of path segments
  for (final p in orphans) {
    final segs = p.split('.');
    final mod = topKeyToModule[segs.first];
    if (mod == null) {
      stderr.writeln('  WARNING: orphan $p has no module mapping; skipping.');
      continue;
    }
    byModule.putIfAbsent(mod, () => []).add(segs);
  }

  for (final entry in byModule.entries) {
    for (final locale in ['en', 'de']) {
      final f = File('$root/assets/i18n/${entry.key}/$locale.json');
      final raw = f.readAsStringSync();
      final data = jsonDecode(raw) as Map<String, dynamic>;
      var removed = 0;
      for (final segs in entry.value) {
        if (_deletePath(data, segs)) removed++;
      }
      // Tidy: drop empty parent maps.
      _pruneEmpty(data);
      f.writeAsStringSync(
        '${const JsonEncoder.withIndent('  ').convert(data)}\n',
      );
      stderr.writeln('  ${entry.key}/$locale.json: removed $removed leaves');
    }
  }

  // 5. Merge orphan paths into attributes_to_remove.json (nested form).
  final attrFile = File('$root/tools/attributes_to_remove.json');
  final attrRaw = attrFile.existsSync() ? attrFile.readAsStringSync() : '{}';
  final attrs = jsonDecode(attrRaw) as Map<String, dynamic>;
  for (final p in orphans) {
    _markAttribute(attrs, p.split('.'));
  }
  attrFile.writeAsStringSync(
    '${const JsonEncoder.withIndent('  ').convert(attrs)}\n',
  );
  stderr.writeln('Updated tools/attributes_to_remove.json '
      'with ${orphans.length} paths.');
  stderr.writeln('Done.');
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

bool _deletePath(Map<String, dynamic> node, List<String> segs) {
  if (segs.length == 1) {
    return node.remove(segs.first) != null;
  }
  final child = node[segs.first];
  if (child is Map<String, dynamic>) {
    return _deletePath(child, segs.sublist(1));
  }
  return false;
}

void _pruneEmpty(Map<String, dynamic> node) {
  final removeKeys = <String>[];
  node.forEach((k, v) {
    if (v is Map<String, dynamic>) {
      _pruneEmpty(v);
      if (v.isEmpty) removeKeys.add(k);
    }
  });
  for (final k in removeKeys) {
    node.remove(k);
  }
}

void _markAttribute(Map<String, dynamic> node, List<String> segs) {
  if (segs.length == 1) {
    node[segs.first] = true;
    return;
  }
  final child = node[segs.first];
  if (child is Map<String, dynamic>) {
    _markAttribute(child, segs.sublist(1));
  } else {
    final nested = <String, dynamic>{};
    node[segs.first] = nested;
    _markAttribute(nested, segs.sublist(1));
  }
}
