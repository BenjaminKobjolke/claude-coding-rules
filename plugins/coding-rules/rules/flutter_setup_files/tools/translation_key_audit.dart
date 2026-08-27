// Shared detection logic for the translation-key tooling in this folder.
//
// `check_translation_keys.dart` (report), `prune_unused_translation_keys.dart`
// and `prune_orphan_i18n_leaves.dart` must all agree on what "referenced"
// means — a pruner carrying its own stale copy of the rules deletes live keys.
// Everything that decides "is this key alive?" lives here, once.
//
// Both i18n layouts are supported and detected at startup:
//
//   modular      assets/i18n/modules.json + assets/i18n/<module>/<locale>.json
//   single-file  assets/i18n/<locale>.json
//
// Nothing here needs per-project editing; the only project config is the
// `_topKeyToClass` map in check_translation_keys.dart.

import 'dart:convert';
import 'dart:io';

/// Where the i18n JSON lives, and which top-level key belongs where.
class I18nLayout {
  I18nLayout._(this.root, this.modules, this._topKeyToModule, this.locales);

  final String root;

  /// Module directory names. Empty for the single-file layout.
  final List<String> modules;

  /// Top-level i18n key -> module directory (`''` in the single-file layout).
  final Map<String, String> _topKeyToModule;

  /// Locale codes from `assets/i18n/languages.json`.
  final List<String> locales;

  bool get isModular => modules.isNotEmpty;

  static I18nLayout detect(String root) {
    final i18n = Directory('$root/assets/i18n');
    if (!i18n.existsSync()) {
      stderr.writeln('i18n dir not found at ${i18n.path}');
      exit(1);
    }

    final locales = <String>[];
    final languages = File('$root/assets/i18n/languages.json');
    if (languages.existsSync()) {
      final decoded = jsonDecode(languages.readAsStringSync());
      if (decoded is Map<String, dynamic>) locales.addAll(decoded.keys);
    }
    if (locales.isEmpty) locales.add('en');

    final modulesFile = File('$root/assets/i18n/modules.json');
    final topKeyToModule = <String, String>{};
    if (!modulesFile.existsSync()) {
      final en = File('$root/assets/i18n/en.json');
      if (!en.existsSync()) {
        stderr.writeln('neither modules.json nor en.json found in ${i18n.path}');
        exit(1);
      }
      for (final k in _readJson(en).keys) {
        if (k != '_hint_') topKeyToModule[k] = '';
      }
      return I18nLayout._(root, const [], topKeyToModule, locales);
    }

    final modules =
        (jsonDecode(modulesFile.readAsStringSync()) as List).cast<String>();
    for (final mod in modules) {
      for (final k in _readJson(File('$root/assets/i18n/$mod/en.json')).keys) {
        if (k != '_hint_') topKeyToModule[k] = mod;
      }
    }
    return I18nLayout._(root, modules, topKeyToModule, locales);
  }

  /// Every dotted leaf path in the English source of truth.
  Set<String> loadLeaves() {
    final leaves = <String>{};
    for (final file in localeFiles('en')) {
      flattenLeaves(_readJson(file), '', leaves);
    }
    return leaves;
  }

  /// Every JSON file holding [locale], across modules when modular.
  List<File> localeFiles(String locale) {
    if (!isModular) return [File('$root/assets/i18n/$locale.json')];
    return [
      for (final mod in modules) File('$root/assets/i18n/$mod/$locale.json'),
    ];
  }

  /// The file holding [topKey] for [locale], or null when [topKey] is unknown.
  File? localeFileFor(String topKey, String locale) {
    final mod = _topKeyToModule[topKey];
    if (mod == null) return null;
    if (mod.isEmpty) return File('$root/assets/i18n/$locale.json');
    return File('$root/assets/i18n/$mod/$locale.json');
  }

  static Map<String, dynamic> _readJson(File f) {
    if (!f.existsSync()) {
      stderr.writeln('i18n file not found at ${f.path}');
      exit(1);
    }
    return jsonDecode(f.readAsStringSync()) as Map<String, dynamic>;
  }
}

/// A `static const String x = 'a.b.c';` declaration inside a `TK*` class.
class TkConst {
  TkConst(this.className, this.name, this.value, this.sourcePath);

  final String className;
  final String name;
  final String value;
  final String sourcePath;

  /// Constants named `...Prefix` hold a partial path completed at runtime —
  /// `tr('${TKStats.weekStatusPrefix}$status')`. They match every leaf below
  /// their value instead of one exact leaf. Without this, such a constant
  /// reads as "missing" and every leaf it reaches reads as an orphan — and a
  /// pruner would then delete live translations.
  bool get isPrefix => name.endsWith('Prefix');

  /// `TKCore.commonSave`
  String get qualifiedName => '$className.$name';
}

/// A `tr('some.literal')` call site that bypasses the TK class.
class RawHit {
  RawHit(this.filePath, this.line, this.literal, this.literalStart, this.literalEnd);

  final String filePath;
  final int line;
  final String literal;

  /// Offsets of the quoted literal itself (quotes included), so a rewrite can
  /// leave the surrounding call — `AppLocalizations.tr(` or `_tr(` — intact.
  final int literalStart;
  final int literalEnd;
}

/// TK references and raw literals found while walking `lib/` + `test/` once.
class CallerScan {
  CallerScan(this.references, this.rawHits);

  /// Qualified names, e.g. `TKCore.commonSave`.
  final Set<String> references;
  final List<RawHit> rawHits;
}

/// Collects the dotted paths of every string leaf under [node] into [out].
void flattenLeaves(Map<String, dynamic> node, String prefix, Set<String> out) {
  node.forEach((k, v) {
    if (k == '_hint_') return;
    final path = prefix.isEmpty ? k : '$prefix.$k';
    if (v is Map<String, dynamic>) {
      flattenLeaves(v, path, out);
    } else if (v is String) {
      out.add(path);
    }
  });
}

/// Every TK constant declared under `lib/config/translation_keys/`.
List<TkConst> loadTkConsts(String root) {
  final dir = Directory('$root/lib/config/translation_keys');
  if (!dir.existsSync()) {
    stderr.writeln('TK dir not found at ${dir.path}');
    exit(1);
  }
  final declRe = RegExp(r"static\s+const\s+String\s+(\w+)\s*=\s*'([^']+)'\s*;");
  final classRe = RegExp(r'^\s*class\s+(\w+)\s*\{', multiLine: true);
  final consts = <TkConst>[];
  for (final ent in dir.listSync()) {
    if (ent is! File || !ent.path.endsWith('.dart')) continue;
    final src = ent.readAsStringSync();
    final cm = classRe.firstMatch(src);
    if (cm == null) continue;
    for (final m in declRe.allMatches(src)) {
      consts.add(TkConst(cm.group(1)!, m.group(1)!, m.group(2)!, ent.path));
    }
  }
  return consts;
}

/// True when [path] is reached at runtime through a `...Prefix` constant.
bool coveredByPrefix(String path, Iterable<TkConst> consts) {
  for (final c in consts) {
    if (c.isPrefix && path.startsWith(c.value) && path != c.value) return true;
  }
  return false;
}

/// Walks `lib/` + `test/` collecting TK references and raw `tr()` literals.
///
/// Widgets often wrap the call in a file-local
/// `String _tr(String key) => AppLocalizations.tr(key);`, so both spellings
/// must be matched or the raw-literal check is blind to most callers.
Future<CallerScan> scanCallers(String root) async {
  final refRe = RegExp(r'\b(TK[A-Za-z]+)\.([A-Za-z_][A-Za-z0-9_]*)\b');
  final rawRe = RegExp(r"(?:AppLocalizations\.tr|\b_tr)\(\s*'([^']*)'");
  final references = <String>{};
  final rawHits = <RawHit>[];

  for (final dir in [Directory('$root/lib'), Directory('$root/test')]) {
    if (!dir.existsSync()) continue;
    await for (final ent in dir.list(recursive: true, followLinks: false)) {
      if (ent is! File || !ent.path.endsWith('.dart')) continue;
      final p = ent.path.replaceAll('\\', '/');
      if (p.contains('/lib/config/translation_keys/')) continue;
      if (p.endsWith('/lib/config/translation_keys.dart')) continue;
      final src = ent.readAsStringSync();

      for (final m in refRe.allMatches(src)) {
        references.add('${m.group(1)}.${m.group(2)}');
      }
      for (final m in rawRe.allMatches(src)) {
        final literal = m.group(1)!;
        // Interpolated literals are the `...Prefix` pattern, not a bypass.
        if (literal.contains(r'$')) continue;
        // The match ends right after the closing quote, so the literal plus
        // its two quotes is the tail of the match.
        final start = m.end - literal.length - 2;
        final line = '\n'.allMatches(src.substring(0, m.start)).length + 1;
        rawHits.add(RawHit(ent.path, line, literal, start, m.end));
      }
    }
  }
  return CallerScan(references, rawHits);
}
