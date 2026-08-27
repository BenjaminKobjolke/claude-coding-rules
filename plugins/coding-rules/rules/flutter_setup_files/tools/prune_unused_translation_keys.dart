// Prune unused TK constants from lib/config/translation_keys/tk_*.dart.
//
// Uses the same "referenced" rule as check_translation_keys.dart (shared via
// translation_key_audit.dart), then drops the dead declarations line by line.
// Untouched lines keep their exact bytes, so the prune is not buried in
// formatting churn and mixed CRLF/LF files survive. Idempotent.
//
// Run: `tools\prune_unused_translation_keys.bat`
//      `tools\prune_unused_translation_keys.bat --dry-run`
//
// This rewrites source — commit first.

import 'dart:io';

import 'translation_key_audit.dart';

/// `  static const String foo = 'a.b';`
final _declRe =
    RegExp(r"^\s*static\s+const\s+String\s+(\w+)\s*=\s*'([^']+)'\s*;\s*$");

/// First line of the wrapped form: `  static const String foo =`
final _declHeadRe = RegExp(r"^\s*static\s+const\s+String\s+(\w+)\s*=\s*$");

/// Second line of the wrapped form: `      'a.b';`
final _declTailRe = RegExp(r"^\s*'([^']+)'\s*;\s*$");

final _classRe = RegExp(r'^\s*class\s+(\w+)\s*\{');
final _commentRe = RegExp(r'^\s*//');
final _closeBraceRe = RegExp(r'^\s*\}');

void main(List<String> args) async {
  final dryRun = args.contains('--dry-run');
  final root = Directory.current.path;

  final tkFiles = Directory('$root/lib/config/translation_keys')
      .listSync()
      .whereType<File>()
      .where((f) => f.path.endsWith('.dart'))
      .toList();
  final references = (await scanCallers(root)).references;
  var unusedCount = 0;

  for (final file in tkFiles) {
    // Split on '\n' rather than readAsLines() so each line keeps its own '\r'.
    final lines = file.readAsStringSync().split('\n');
    final drop = <int>{};
    String? className;

    for (var i = 0; i < lines.length; i++) {
      final cm = _classRe.firstMatch(lines[i]);
      if (cm != null) {
        className = cm.group(1);
        continue;
      }
      if (className == null) continue;

      String? name;
      String? value;
      var span = 1;
      final flat = _declRe.firstMatch(lines[i]);
      if (flat != null) {
        name = flat.group(1);
        value = flat.group(2);
      } else {
        final head = _declHeadRe.firstMatch(lines[i]);
        final tail = i + 1 < lines.length ? _declTailRe.firstMatch(lines[i + 1]) : null;
        if (head == null || tail == null) continue;
        name = head.group(1);
        value = tail.group(1);
        span = 2;
      }
      if (references.contains('$className.$name')) continue;

      for (var k = 0; k < span; k++) {
        drop.add(i + k);
      }
      unusedCount++;
      if (dryRun) stderr.writeln('  would remove $className.$name  =  $value');
    }
    if (drop.isEmpty || dryRun) continue;

    final kept = [
      for (var i = 0; i < lines.length; i++)
        if (!drop.contains(i)) lines[i],
    ];
    file.writeAsStringSync(_dropDanglingComments(kept).join('\n'));
    stderr.writeln('Pruned ${drop.length} line(s) from ${file.path}');
  }

  stderr.writeln(dryRun
      ? 'Found $unusedCount unused TK constants (dry run, nothing written).'
      : 'Done. Removed $unusedCount unused TK constants.');
}

/// Drops section-header comments left pointing at nothing.
///
/// Works on whole runs of consecutive comment lines, not single lines — a
/// multi-line `///` doc comment is one run and must survive intact. A run goes
/// only when the next non-blank line is another comment run, the class-closing
/// brace, or end of file.
List<String> _dropDanglingComments(List<String> lines) {
  final drop = <int>{};
  var i = 0;
  while (i < lines.length) {
    if (!_commentRe.hasMatch(lines[i])) {
      i++;
      continue;
    }
    var end = i;
    while (end + 1 < lines.length && _commentRe.hasMatch(lines[end + 1])) {
      end++;
    }
    var next = end + 1;
    while (next < lines.length && lines[next].trim().isEmpty) {
      next++;
    }
    final dangling = next >= lines.length ||
        _commentRe.hasMatch(lines[next]) ||
        _closeBraceRe.hasMatch(lines[next]);
    if (dangling) {
      for (var k = i; k <= end; k++) {
        drop.add(k);
      }
    }
    i = end + 1;
  }
  return [
    for (var i = 0; i < lines.length; i++)
      if (!drop.contains(i)) lines[i],
  ];
}
