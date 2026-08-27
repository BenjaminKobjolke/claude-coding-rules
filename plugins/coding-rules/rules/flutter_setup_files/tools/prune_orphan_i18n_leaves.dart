// Remove i18n leaves that no caller reaches — no TK constant, no raw literal,
// and not below a `...Prefix` constant.
//
// Run: `tools\prune_orphan_i18n_leaves.bat --dry-run`   (list only)
//      `tools\prune_orphan_i18n_leaves.bat`             (edit the JSON)
//
// Orphan detection is shared with check_translation_keys.dart via
// translation_key_audit.dart — a second, drifting copy of the rules here would
// silently delete live translations. The i18n layout (modular or single-file)
// is auto-detected.
//
// Locales come from assets/i18n/languages.json. When
// `tools/attributes_to_remove.json` exists, removed paths are merged into it
// so a translator batch can fan the removal out to locale files this script
// does not own; projects without that batch simply do not create the file.
//
// This deletes translations — commit first.

import 'dart:convert';
import 'dart:io';

import 'translation_key_audit.dart';

void main(List<String> args) async {
  final dryRun = args.contains('--dry-run');
  final root = Directory.current.path;

  final layout = I18nLayout.detect(root);
  final tkConsts = loadTkConsts(root);
  final scan = await scanCallers(root);

  final tkValues = tkConsts.map((c) => c.value).toSet();
  final rawLiterals = scan.rawHits.map((h) => h.literal).toSet();
  final orphans = layout
      .loadLeaves()
      .where((p) =>
          !tkValues.contains(p) &&
          !rawLiterals.contains(p) &&
          !coveredByPrefix(p, tkConsts))
      .toList()
    ..sort();

  stderr.writeln('Found ${orphans.length} orphan leaves.');
  for (final p in orphans) {
    stderr.writeln('  $p');
  }
  if (orphans.isEmpty) return;
  if (dryRun) {
    stderr.writeln('Dry run — nothing written.');
    return;
  }

  // Group by the file that owns each path, per locale, so every JSON file is
  // read and written exactly once.
  for (final locale in layout.locales) {
    final byFile = <String, List<String>>{};
    for (final p in orphans) {
      final file = layout.localeFileFor(p.split('.').first, locale);
      if (file == null) {
        stderr.writeln('  WARNING: no i18n file owns $p; skipping.');
        continue;
      }
      byFile.putIfAbsent(file.path, () => []).add(p);
    }
    for (final entry in byFile.entries) {
      final file = File(entry.key);
      if (!file.existsSync()) {
        stderr.writeln('  ${file.path} missing; skipped.');
        continue;
      }
      final data = jsonDecode(file.readAsStringSync()) as Map<String, dynamic>;
      var removed = 0;
      for (final p in entry.value) {
        if (_deletePath(data, p.split('.'))) removed++;
      }
      _pruneEmpty(data);
      file.writeAsStringSync(
        '${const JsonEncoder.withIndent('  ').convert(data)}\n',
      );
      stderr.writeln('  ${file.path}: removed $removed leaves');
    }
  }

  // Opt-in fan-out: only maintained when the project already has the file.
  final attrFile = File('$root/tools/attributes_to_remove.json');
  if (attrFile.existsSync()) {
    final attrs = jsonDecode(attrFile.readAsStringSync()) as Map<String, dynamic>;
    for (final p in orphans) {
      _markAttribute(attrs, p.split('.'));
    }
    attrFile.writeAsStringSync(
      '${const JsonEncoder.withIndent('  ').convert(attrs)}\n',
    );
    stderr.writeln('Updated tools/attributes_to_remove.json '
        'with ${orphans.length} paths.');
  }
  stderr.writeln('Done.');
}

/// Removes the leaf addressed by [segs]; returns true when something went.
bool _deletePath(Map<String, dynamic> node, List<String> segs) {
  if (segs.length == 1) return node.remove(segs.first) != null;
  final child = node[segs.first];
  if (child is Map<String, dynamic>) {
    return _deletePath(child, segs.sublist(1));
  }
  return false;
}

/// Drops parent maps left empty by the deletions.
void _pruneEmpty(Map<String, dynamic> node) {
  final empties = <String>[];
  node.forEach((k, v) {
    if (v is Map<String, dynamic>) {
      _pruneEmpty(v);
      if (v.isEmpty) empties.add(k);
    }
  });
  for (final k in empties) {
    node.remove(k);
  }
}

/// Marks a dotted path in the nested `attributes_to_remove.json` shape.
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
