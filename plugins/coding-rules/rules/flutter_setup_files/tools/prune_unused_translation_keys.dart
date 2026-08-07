// Prune unused TK constants from lib/config/translation_keys/tk_*.dart.
//
// Recomputes the "unused" set the same way `check_translation_keys.dart`
// does, then rewrites each sub-file without the dead declarations.
// Preserves class shell and section comments. Idempotent.
//
// Run: `fvm dart run tools/prune_unused_translation_keys.dart`

import 'dart:io';

void main() async {
  final root = Directory.current.path;

  // 1. Parse TK files: collect (file, className, name, fullLine).
  final tkDir = Directory('$root/lib/config/translation_keys');
  final declRe =
      RegExp(r"^(\s*)static\s+const\s+String\s+(\w+)\s*=\s*'([^']+)'\s*;\s*$");
  final classRe = RegExp(r'^\s*class\s+(\w+)\s*\{');
  final tkFiles = <File>[];
  final tkConsts = <_Decl>[];
  for (final ent in tkDir.listSync()) {
    if (ent is! File || !ent.path.endsWith('.dart')) continue;
    tkFiles.add(ent);
    // Collapse multi-line `static const String X =\n      'value';` decls.
    final normalized = ent.readAsStringSync().replaceAllMapped(
          RegExp(
            r"(static\s+const\s+String\s+\w+\s*=)\s*\r?\n\s*('[^']+'\s*;)",
            multiLine: true,
          ),
          (m) => '${m.group(1)} ${m.group(2)}',
        );
    if (normalized != ent.readAsStringSync()) {
      ent.writeAsStringSync(normalized);
    }
    String? className;
    final lines = ent.readAsLinesSync();
    for (var i = 0; i < lines.length; i++) {
      final cm = classRe.firstMatch(lines[i]);
      if (cm != null) {
        className = cm.group(1);
        continue;
      }
      final dm = declRe.firstMatch(lines[i]);
      if (dm != null && className != null) {
        tkConsts.add(_Decl(ent.path, className, dm.group(2)!, i));
      }
    }
  }

  // 2. Find referenced names by walking lib/ + test/.
  final tkRefs = <String>{};
  final refRe = RegExp(r'\b(TK[A-Za-z]+)\.([A-Za-z_][A-Za-z0-9_]*)\b');
  for (final r in [Directory('$root/lib'), Directory('$root/test')]) {
    if (!r.existsSync()) continue;
    await for (final ent in r.list(recursive: true, followLinks: false)) {
      if (ent is! File || !ent.path.endsWith('.dart')) continue;
      final p = ent.path.replaceAll('\\', '/');
      if (p.contains('/lib/config/translation_keys/')) continue;
      if (p.endsWith('/lib/config/translation_keys.dart')) continue;
      for (final m in refRe.allMatches(ent.readAsStringSync())) {
        tkRefs.add('${m.group(1)}.${m.group(2)}');
      }
    }
  }

  // 3. Determine unused.
  final unusedByFile = <String, Set<int>>{};
  var unusedCount = 0;
  for (final d in tkConsts) {
    if (!tkRefs.contains('${d.className}.${d.name}')) {
      unusedByFile.putIfAbsent(d.filePath, () => <int>{}).add(d.lineIdx);
      unusedCount++;
    }
  }
  stderr.writeln('Found $unusedCount unused TK constants.');

  // 4. Rewrite each TK file dropping the marked lines.
  // Also collapse runs of orphan section comments (a comment immediately
  // followed by another section comment or a class-close brace).
  for (final f in tkFiles) {
    final drop = unusedByFile[f.path];
    if (drop == null || drop.isEmpty) continue;
    final lines = f.readAsLinesSync();
    final kept = <String>[];
    for (var i = 0; i < lines.length; i++) {
      if (drop.contains(i)) continue;
      kept.add(lines[i]);
    }
    // Second pass: drop section-only comments (lines starting with `  //`)
    // that are followed by another comment or by `}`.
    final pruned = <String>[];
    for (var i = 0; i < kept.length; i++) {
      final cur = kept[i].trimRight();
      final isComment = RegExp(r'^\s*//').hasMatch(cur);
      if (isComment) {
        // peek forward to next non-blank
        var j = i + 1;
        while (j < kept.length && kept[j].trim().isEmpty) {
          j++;
        }
        if (j >= kept.length) {
          continue; // trailing comment before EOF
        }
        final next = kept[j];
        if (RegExp(r'^\s*//').hasMatch(next) ||
            RegExp(r'^\s*\}').hasMatch(next)) {
          continue; // orphan section header
        }
      }
      pruned.add(kept[i]);
    }
    f.writeAsStringSync('${pruned.join('\n')}\n');
    stderr.writeln('Pruned ${drop.length} from ${f.path}');
  }
  stderr.writeln('Done.');
}

class _Decl {
  _Decl(this.filePath, this.className, this.name, this.lineIdx);
  final String filePath;
  final String className;
  final String name;
  final int lineIdx;
}
