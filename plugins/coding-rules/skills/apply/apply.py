"""Deterministic core of the coding-rules:apply skill.

Owns the mechanical phases the skill used to hand-edit: version-merging rule
blocks into CODING_RULES.md, the CLAUDE.md pointer block, delegation markers +
settings.local.json permission merge, and the reminder-hook install into
settings.json. Judgment calls (which rule files apply, the delegation choice,
an unrecognized legacy block) stay with the skill/model -- this script reports
them back via `needs_user_decision` / `errors` instead of guessing.

State: `<project>/coding-rules.json` records what was last applied (per-rule
version, delegation, python interpreter, pointer version, plugin root) so a
re-run only rewrites what's stale. Source-of-truth versions come from
`<plugin-root>/rules/versions.json`; `--check-versions` guards that index
against the `# Version` header in each md file so they can't drift.

Run:  python apply.py --project <dir> --plugin-root <dir> --rules A.md,B.md [--delegation codex|deepseek|neither|keep] [--python python] [--json]
Test: python apply.py --self-test
Guard: python apply.py --check-versions [--plugin-root <dir>]
"""

import argparse
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

MANAGED_COMMENT = "<!-- Managed by /coding-rules:apply — do not edit rule blocks by hand -->"
POINTER_TITLE = "# Coding Rules (Pointer)"
POINTER_BLOCK_TEMPLATE = """# Version
{version}

# Coding Rules (Pointer)

This project's coding rules live in `CODING_RULES.md` in the project root. They are
BINDING for all code work in this repository.

MANDATORY: Before writing or editing ANY code, you MUST Read `CODING_RULES.md`
in full **in the current session**. Do not rely on memory of a previous session,
a summary, or partial reads.

If you are about to make a code change and have not read `CODING_RULES.md` in
this session: STOP, read it, then continue.

Do not inline rules back into this file and do not use `@import` for
`CODING_RULES.md` — it is intentionally referenced, not imported.
"""

DELEGATION_PERMS = {
    "codex": ["Bash(codex exec:*)", "PowerShell(codex exec:*)"],
    "deepseek": ["Bash(reasonix run:*)", "PowerShell(reasonix run:*)"],
}


# ---------------------------------------------------------------- IO helpers

def read_text(path):
    return path.read_text(encoding="utf-8")


def write_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def load_json(path, default):
    if not path.exists():
        return default
    raw = read_text(path)
    if not raw.strip():
        return default
    return json.loads(raw)


def save_json(path, data):
    write_text(path, json.dumps(data, indent=2) + "\n")


# ---------------------------------------------------- fence-aware block scan

def parse_managed(text):
    """Split text into (lines, blocks) on lines that are exactly '# Version',
    ignoring such lines inside ``` fences. A block runs to the next such line
    or EOF, matching the Phase B spec ("a block ends at the next # Version
    line ... or end of file")."""
    lines = text.splitlines(keepends=True)
    in_fence = False
    starts = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence and stripped == "# Version":
            starts.append(i)
    blocks = []
    for idx, start in enumerate(starts):
        end = starts[idx + 1] if idx + 1 < len(starts) else len(lines)
        block_lines = lines[start:end]
        blocks.append({
            "start": start,
            "end": end,
            "title": find_title(block_lines),
            "text": "".join(block_lines),
        })
    return lines, blocks


def find_title(block_lines):
    """First non-fenced '# <Title>' heading in a block, skipping '# Version' itself."""
    in_fence = False
    for line in block_lines[1:]:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if stripped.startswith("# ") and stripped != "# Version":
            return stripped
    return None


def parse_block_version(block_text):
    """Version number of a '# Version' block: the first line matching ^\\d+$
    after the header, skipping blank lines (historical blocks wrote the number
    with a blank line in between). None if other content comes first."""
    lines = block_text.splitlines()
    it = iter(lines)
    for line in it:
        if line.strip() == "# Version":
            break
    for line in it:
        stripped = line.strip()
        if not stripped:
            continue
        return int(stripped) if stripped.isdigit() else None
    return None


def block_is_tailored(block_text):
    """True if the block carries a non-fenced '<!-- tailored -->' line — a
    project-tailored copy apply.py must never auto-overwrite."""
    in_fence = False
    for line in block_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence and stripped == "<!-- tailored -->":
            return True
    return False


def source_headings(src_text):
    """All non-fenced top-level headings of a source doc, incl. '# Version'.
    Sources may legitimately have more than one (FLUTTER, PYTHON)."""
    heads = {"# Version"}
    in_fence = False
    for line in src_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence and stripped.startswith("# "):
            heads.add(stripped)
    return heads


def split_orphan_tail(block_text, src_text):
    """Split an existing block into (managed_text, orphan_text) at the first
    non-fenced top-level heading the source doc doesn't contain. The orphan is
    user-authored content that must survive a block replacement."""
    known = source_headings(src_text)
    lines = block_text.splitlines(keepends=True)
    in_fence = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence and stripped.startswith("# ") and stripped not in known:
            return "".join(lines[:i]), "".join(lines[i:])
    return block_text, ""


def parse_source_version_title(text):
    lines = text.splitlines()
    if not lines or lines[0].strip() != "# Version":
        raise ValueError("file does not start with a '# Version' header")
    version = int(lines[1].strip())
    title = find_title(lines)
    if title is None:
        raise ValueError("no '# <Title>' heading found after the version header")
    return version, title


# --------------------------------------------------------- CODING_RULES.md

def read_coding_rules(path):
    if not path.exists():
        return "", []
    text = read_text(path)
    lines, blocks = parse_managed(text)
    if not blocks:
        return text, []
    header = "".join(lines[:blocks[0]["start"]])
    return header, [{"title": b["title"], "text": b["text"]} for b in blocks]


def write_coding_rules(path, header, blocks):
    body = "\n\n".join(b["text"].rstrip("\n") for b in blocks)
    text = header.rstrip("\n") + "\n\n"
    text += (body + "\n") if body else ""
    write_text(path, text)


def process_rules(blocks, plugin_root, requested, manifest_rules, versions):
    """Version-merge each requested rule's source into the block list.
    Returns (blocks, new_manifest_rules, report)."""
    blocks_by_title = {b["title"]: b for b in blocks}
    new_manifest_rules = dict(manifest_rules)
    report = []
    for rel in requested:
        src_path = plugin_root / "rules" / rel
        if not src_path.exists():
            report.append({"rule": rel, "status": "error", "detail": "source file not found"})
            continue
        src_text = read_text(src_path)
        parsed_version, title = parse_source_version_title(src_text)
        version = versions.get(rel, parsed_version)
        existing = blocks_by_title.get(title)
        applied = manifest_rules.get(rel)
        if applied is None and existing is not None:
            # No manifest entry yet (pre-manifest project) -- trust the version
            # already written in the existing block instead of treating it as
            # absent, so an up-to-date block isn't blindly rewritten.
            applied = parse_block_version(existing["text"])
        if applied is not None and applied > version:
            new_manifest_rules[rel] = applied  # keep the conflicting version on record
            report.append({"rule": rel, "status": "conflict",
                            "detail": f"manifest version {applied} > source version {version}"})
            continue
        if applied == version and existing is not None:
            new_manifest_rules[rel] = version  # already applied -- still record it
            report.append({"rule": rel, "status": "unchanged", "version": version})
            continue
        if existing is not None and block_is_tailored(existing["text"]):
            # Project-tailored copy: stale, but a verbatim overwrite would
            # destroy the tailoring -- hand-merge is a judgment call.
            if applied is not None:
                new_manifest_rules[rel] = applied
            report.append({"rule": rel, "status": "tailored-stale",
                            "detail": f"tailored block at version {applied}, source at {version} — hand-merge required"})
            continue
        new_text = src_text if src_text.endswith("\n") else src_text + "\n"
        item = {"rule": rel, "status": "updated", "version": version}
        if existing is not None:
            _, orphan = split_orphan_tail(existing["text"], src_text)
            existing["text"] = new_text
            existing["title"] = title
            if orphan:
                orphan_title = next(
                    (l.strip() for l in orphan.splitlines() if l.strip().startswith("# ")), None)
                blocks.insert(blocks.index(existing) + 1,
                              {"title": orphan_title, "text": orphan})
                item["preserved"] = [orphan_title]
        else:
            new_block = {"title": title, "text": new_text}
            blocks.append(new_block)
            blocks_by_title[title] = new_block
        new_manifest_rules[rel] = version
        report.append(item)
    return blocks, new_manifest_rules, report


def reconcile_manifest(blocks, manifest_rules, title_to_rel):
    """Ensure every recognized block currently in CODING_RULES.md is recorded in
    the manifest, even if its rel wasn't passed in --rules this run (e.g. a
    block from an earlier install). The manifest mirrors the file, not the
    catalog: rules never applied to this project stay absent."""
    new_manifest_rules = dict(manifest_rules)
    for b in blocks:
        rel = title_to_rel.get(b["title"])
        if rel is None or rel in new_manifest_rules:
            continue
        ver = parse_block_version(b["text"])
        if ver is not None:
            new_manifest_rules[rel] = ver
    return new_manifest_rules


def rebuild_header(header_text, delegation_choice):
    """Rebuild the managed-comment + codex/deepseek marker header. Returns
    (new_header_text, resolved_delegation)."""
    marker_re = re.compile(r"^<!-- (codex|deepseek): (enabled|disabled) -->$")
    lines = header_text.splitlines()
    codex_state = deepseek_state = None
    other = []
    for line in lines:
        stripped = line.strip()
        m = marker_re.match(stripped)
        if m:
            if m.group(1) == "codex":
                codex_state = m.group(2)
            else:
                deepseek_state = m.group(2)
            continue
        if stripped.startswith("<!-- Managed by"):
            continue
        if stripped:
            other.append(stripped)

    if delegation_choice == "keep":
        if codex_state == "enabled":
            resolved = "codex"
        elif deepseek_state == "enabled":
            resolved = "deepseek"
        else:
            resolved = "neither"
    else:
        resolved = delegation_choice

    codex_state = "enabled" if resolved == "codex" else "disabled"
    deepseek_state = "enabled" if resolved == "deepseek" else "disabled"

    new_lines = [MANAGED_COMMENT, f"<!-- codex: {codex_state} -->", f"<!-- deepseek: {deepseek_state} -->"]
    new_lines.extend(other)
    return "\n".join(new_lines) + "\n\n", resolved


# -------------------------------------------------------------- CLAUDE.md

def build_title_index(plugin_root, versions):
    """title -> rel path, for every shipped rule file listed in versions.json."""
    index = {}
    for rel in versions:
        if rel == "pointer":
            continue
        src_path = plugin_root / "rules" / rel
        if not src_path.exists():
            continue
        _, title = parse_source_version_title(read_text(src_path))
        index[title] = rel
    return index


def strip_legacy_imports(text):
    lines = text.splitlines(keepends=True)
    return "".join(
        line for line in lines
        if not (line.strip().startswith("@") and "CODING_RULES.md" in line)
    )


def migrate_legacy(text, title_to_rel):
    """Move recognized legacy '# Version' blocks out of CLAUDE.md text into a
    migrated-versions dict; leave unrecognized ones untouched and reported.
    Returns (new_text, migrated_rel_to_version, unrecognized_titles)."""
    if not text:
        return text, {}, []
    lines, blocks = parse_managed(text)
    if not blocks:
        return strip_legacy_imports(text), {}, []

    header_end = blocks[0]["start"]
    result_lines = list(lines[:header_end])
    migrated = {}
    unrecognized = []
    for b in blocks:
        if b["title"] == POINTER_TITLE:
            result_lines.extend(lines[b["start"]:b["end"]])
            continue
        rel = title_to_rel.get(b["title"])
        ver = parse_block_version(b["text"]) if rel else None
        if rel and ver is not None:
            migrated[rel] = ver
            continue  # dropped -- moves into CODING_RULES.md via process_rules
        unrecognized.append(b["title"] or "(untitled block)")
        result_lines.extend(lines[b["start"]:b["end"]])
    return strip_legacy_imports("".join(result_lines)), migrated, unrecognized


def apply_pointer(claude_text, manifest_pointer_version, source_version):
    """Returns (new_claude_text, resolved_pointer_version, status)."""
    lines, blocks = parse_managed(claude_text)
    existing = next((b for b in blocks if b["title"] == POINTER_TITLE), None)

    if manifest_pointer_version is None and existing is not None:
        # No manifest entry yet (pre-manifest project) -- trust the version
        # already in the existing pointer block instead of treating it as
        # absent, so an up-to-date pointer isn't rewritten for nothing.
        manifest_pointer_version = parse_block_version(existing["text"])

    if existing is not None and manifest_pointer_version is not None and manifest_pointer_version > source_version:
        return claude_text, manifest_pointer_version, "conflict"
    if existing is not None and manifest_pointer_version == source_version:
        return claude_text, manifest_pointer_version, "unchanged"

    if existing is not None:
        rest_lines = lines[:existing["start"]] + lines[existing["end"]:]
    else:
        rest_lines = lines
    rest_text = "".join(rest_lines).lstrip("\n")

    new_text = POINTER_BLOCK_TEMPLATE.format(version=source_version).rstrip("\n") + "\n"
    new_text += ("\n\n" + rest_text) if rest_text.strip() else "\n"
    return new_text, source_version, "updated"


# --------------------------------------------------------------- JSON merges

def merge_json_permissions(path, entries):
    """Ensure each allow-string in `entries` is present. Returns (changed, error)."""
    if path.exists():
        raw = read_text(path)
        try:
            data = json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError:
            return False, "invalid_json"
    else:
        data = {}
    allow = data.setdefault("permissions", {}).setdefault("allow", [])
    changed = False
    for entry in entries:
        if entry not in allow:
            allow.append(entry)
            changed = True
    if changed or not path.exists():
        write_text(path, json.dumps(data, indent=2) + "\n")
    return changed, None


def merge_hooks(path, python_interp):
    """Merge the PostToolUse/PreToolUse reminder-hook entries. Returns status string."""
    if path.exists():
        raw = read_text(path)
        try:
            data = json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError:
            return "error"
    else:
        data = {}
    hooks = data.setdefault("hooks", {})
    command = f"{python_interp} .claude/hooks/coding-rules-reminder.py"

    def upsert(event, matcher):
        arr = hooks.setdefault(event, [])
        for entry in arr:
            for h in entry.get("hooks", []):
                if "coding-rules-reminder" in h.get("command", ""):
                    entry["matcher"] = matcher
                    h["command"] = command
                    return
        arr.append({"matcher": matcher, "hooks": [{"type": "command", "command": command}]})

    upsert("PostToolUse", "ExitPlanMode")
    upsert("PreToolUse", "Edit|Write|MultiEdit")
    write_text(path, json.dumps(data, indent=2) + "\n")
    return "ok"


# -------------------------------------------------------------------- run

def run(project, plugin_root, requested_rules, delegation, python_interp):
    versions = load_json(plugin_root / "rules" / "versions.json", {})
    manifest_path = project / "coding-rules.json"
    manifest = load_json(manifest_path, {})
    manifest.setdefault("rules", {})

    report = {"rules": [], "pointer": None, "delegation": None, "hooks": None,
              "needs_user_decision": [], "errors": []}

    # Phase B: migrate legacy blocks out of CLAUDE.md
    claude_path = project / "CLAUDE.md"
    claude_text = read_text(claude_path) if claude_path.exists() else ""
    title_to_rel = build_title_index(plugin_root, versions)
    claude_text, migrated, unrecognized = migrate_legacy(claude_text, title_to_rel)
    requested = list(dict.fromkeys(requested_rules))
    for rel, ver in migrated.items():
        manifest["rules"].setdefault(rel, ver)
        if rel not in requested:
            requested.append(rel)
    for title in unrecognized:
        report["needs_user_decision"].append(
            {"phase": "B", "detail": f"Unrecognized versioned block in CLAUDE.md: {title}"})

    # Phase C: version-merge rule blocks into CODING_RULES.md
    crm_path = project / "CODING_RULES.md"
    header, blocks = read_coding_rules(crm_path)
    blocks, manifest["rules"], rules_report = process_rules(
        blocks, plugin_root, requested, manifest["rules"], versions)
    report["rules"] = rules_report
    for item in rules_report:
        if item["status"] in ("conflict", "tailored-stale"):
            report["needs_user_decision"].append({"phase": "C", "detail": f"{item['rule']}: {item['detail']}"})
        elif item["status"] == "error":
            report["errors"].append({"phase": "C", "detail": f"{item['rule']}: {item['detail']}"})

    # Reconcile: record any recognized block already in CODING_RULES.md that
    # wasn't in --rules this run (e.g. added by an earlier install), so the
    # manifest never lags behind what's actually in the file.
    manifest["rules"] = reconcile_manifest(blocks, manifest["rules"], title_to_rel)

    # Phase D2: delegation markers (header lives in CODING_RULES.md)
    new_header, resolved_delegation = rebuild_header(header, delegation)
    write_coding_rules(crm_path, new_header, blocks)
    manifest["delegation"] = resolved_delegation
    report["delegation"] = resolved_delegation
    if resolved_delegation in DELEGATION_PERMS:
        settings_local = project / ".claude" / "settings.local.json"
        changed, err = merge_json_permissions(settings_local, DELEGATION_PERMS[resolved_delegation])
        if err:
            report["errors"].append({"phase": "D2", "file": str(settings_local), "error": err})

    # Phase D: pointer block in CLAUDE.md
    pointer_version = versions.get("pointer", 1)
    new_claude_text, resolved_pointer_version, pointer_status = apply_pointer(
        claude_text, manifest.get("pointerVersion"), pointer_version)
    write_text(claude_path, new_claude_text)
    manifest["pointerVersion"] = resolved_pointer_version
    report["pointer"] = pointer_status
    if pointer_status == "conflict":
        report["needs_user_decision"].append(
            {"phase": "D", "detail": f"CLAUDE.md pointer version {manifest.get('pointerVersion')} > source {pointer_version}"})

    # Phase E: reminder hook + settings.json
    manifest["python"] = python_interp
    hooks_src = Path(__file__).resolve().parent / "hooks" / "coding-rules-reminder.py"
    if hooks_src.exists():
        hooks_dst = project / ".claude" / "hooks" / "coding-rules-reminder.py"
        hooks_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(hooks_src, hooks_dst)
        settings_path = project / ".claude" / "settings.json"
        hook_status = merge_hooks(settings_path, python_interp)
        report["hooks"] = hook_status
        if hook_status == "error":
            report["errors"].append({"phase": "E", "file": str(settings_path), "error": "invalid_json"})
    else:
        report["hooks"] = "skipped"

    manifest["pluginRoot"] = str(plugin_root)
    save_json(manifest_path, manifest)
    return report


def print_report(report):
    for item in report["rules"]:
        print(f"  rule {item['rule']}: {item['status']}")
    print(f"  pointer: {report['pointer']}")
    print(f"  delegation: {report['delegation']}")
    print(f"  hooks: {report['hooks']}")
    for d in report["needs_user_decision"]:
        print(f"  NEEDS DECISION [{d['phase']}]: {d['detail']}")
    for e in report["errors"]:
        print(f"  ERROR: {e}")


# --------------------------------------------------------------- check-versions

def check_versions(plugin_root):
    """Only files that actually start with a '# Version' header are versioned
    rule docs subject to this check -- *_setup_files/ templates and plain
    workflow docs (CREATE_RELEASE_NOTES.md, PHP_UPGRADE_TO_NEWER_VERSION.md, ...)
    are skipped, not flagged."""
    versions_path = plugin_root / "rules" / "versions.json"
    versions = load_json(versions_path, {})
    problems = []
    seen = set()
    for md in sorted((plugin_root / "rules").rglob("*.md")):
        if "_setup_files" in md.parts:
            continue
        text = read_text(md)
        first_line = text.splitlines()[0].strip() if text.strip() else ""
        if first_line != "# Version":
            continue
        rel = md.relative_to(plugin_root / "rules").as_posix()
        seen.add(rel)
        try:
            version, _ = parse_source_version_title(text)
        except ValueError as e:
            problems.append(f"{rel}: cannot parse version header ({e})")
            continue
        if rel not in versions:
            problems.append(f"{rel}: missing from versions.json")
        elif versions[rel] != version:
            problems.append(f"{rel}: versions.json has {versions[rel]}, header has {version}")
        if block_is_tailored(text):
            problems.append(f"{rel}: shipped source contains a '<!-- tailored -->' marker (project-only marker)")
    for rel in versions:
        if rel != "pointer" and rel not in seen:
            problems.append(f"{rel}: listed in versions.json but file not found")
    if problems:
        print("check-versions: FAIL")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)
    print("check-versions: OK")


# -------------------------------------------------------------------- self-test

def self_test():
    # parse_source_version_title
    v, t = parse_source_version_title("# Version\n3\n\ntext\n\n# My Title\n\nbody\n")
    assert (v, t) == (3, "# My Title"), (v, t)

    # fence-aware block splitting: an embedded example must not start a new block
    sample = (
        "# Version\n1\n\n# Real Title\n\nSee example:\n\n"
        "```markdown\n# Version\n1\n```\n\nmore body\n"
    )
    _, blocks = parse_managed(sample)
    assert len(blocks) == 1, blocks
    assert blocks[0]["title"] == "# Real Title", blocks[0]

    # process_rules: absent -> update, equal -> unchanged, manifest>source -> conflict
    src_dir = Path(tempfile.mkdtemp()) / "rules"
    src_dir.mkdir(parents=True)
    (src_dir / "FOO.md").write_text("# Version\n2\n\n# Foo Rules\n\nbody\n", encoding="utf-8")
    blocks, manifest_rules, report = process_rules([], src_dir.parent, ["FOO.md"], {}, {})
    assert report[0]["status"] == "updated" and manifest_rules["FOO.md"] == 2, report
    blocks, manifest_rules, report = process_rules(blocks, src_dir.parent, ["FOO.md"], manifest_rules, {})
    assert report[0]["status"] == "unchanged", report
    blocks, manifest_rules, report = process_rules(blocks, src_dir.parent, ["FOO.md"], {"FOO.md": 5}, {})
    assert report[0]["status"] == "conflict", report

    # tolerant version parse: historical blank-line format (regression: bug that
    # silently overwrote a v4 block with v3 source because int('') threw)
    assert parse_block_version("# Version\n\n4\n\n# Foo Rules\nbody\n") == 4
    assert parse_block_version("# Version\n2\n\n# Foo Rules\n") == 2
    assert parse_block_version("# Version\n\n# Foo Rules\n") is None

    # pre-manifest blocks in the blank-line format: conflict + unchanged paths
    blank_conflict = {"title": "# Foo Rules", "text": "# Version\n\n4\n\n# Foo Rules\n\nbody\n"}
    _, _, rep_bc = process_rules([blank_conflict], src_dir.parent, ["FOO.md"], {}, {})
    assert rep_bc[0]["status"] == "conflict", rep_bc
    blank_equal = {"title": "# Foo Rules", "text": "# Version\n\n2\n\n# Foo Rules\n\nbody\n"}
    _, _, rep_be = process_rules([blank_equal], src_dir.parent, ["FOO.md"], {}, {})
    assert rep_be[0]["status"] == "unchanged", rep_be

    # orphan tail preserved on replace (regression: user-authored sections after
    # the last managed block were deleted by a block update)
    stale_with_tail = {"title": "# Foo Rules",
                       "text": "# Version\n1\n\n# Foo Rules\n\nold body\n\n# My Project Notes\n\nkeep me\n"}
    blocks_o = [stale_with_tail]
    blocks_o, _, rep_o = process_rules(blocks_o, src_dir.parent, ["FOO.md"], {"FOO.md": 1}, {})
    assert rep_o[0]["status"] == "updated" and rep_o[0]["preserved"] == ["# My Project Notes"], rep_o
    assert len(blocks_o) == 2 and "keep me" in blocks_o[1]["text"], blocks_o
    assert "My Project Notes" not in blocks_o[0]["text"], blocks_o

    # multi-heading source (PYTHON/FLUTTER style): its own extra heading must
    # NOT be split out as an orphan
    (src_dir / "MULTI.md").write_text(
        "# Version\n1\n\n# Multi Rules\n\nbody\n\n# Essential Extras\n\nmore\n", encoding="utf-8")
    old_multi = {"title": "# Multi Rules",
                 "text": "# Version\n0\n\n# Multi Rules\n\nold\n\n# Essential Extras\n\nold more\n"}
    blocks_m = [old_multi]
    blocks_m, _, rep_m = process_rules(blocks_m, src_dir.parent, ["MULTI.md"], {}, {})
    assert rep_m[0]["status"] == "updated" and "preserved" not in rep_m[0], rep_m
    assert len(blocks_m) == 1 and "old more" not in blocks_m[0]["text"], blocks_m

    # tailored marker: stale -> tailored-stale + untouched; equal -> unchanged
    tailored_stale = {"title": "# Foo Rules",
                      "text": "# Version\n1\n\n# Foo Rules\n<!-- tailored -->\n\ncustom body\n"}
    _, mf_ts, rep_ts = process_rules([tailored_stale], src_dir.parent, ["FOO.md"], {}, {})
    assert rep_ts[0]["status"] == "tailored-stale", rep_ts
    assert "custom body" in tailored_stale["text"]
    assert mf_ts["FOO.md"] == 1, mf_ts
    tailored_equal = {"title": "# Foo Rules",
                      "text": "# Version\n2\n\n# Foo Rules\n<!-- tailored -->\n\ncustom body\n"}
    _, mf_te, rep_te = process_rules([tailored_equal], src_dir.parent, ["FOO.md"], {}, {})
    assert rep_te[0]["status"] == "unchanged" and mf_te["FOO.md"] == 2, rep_te
    # a fenced '<!-- tailored -->' (documentation example) does not count
    assert not block_is_tailored("# Version\n1\n\n# X\n\n```\n<!-- tailored -->\n```\n")

    # process_rules: pre-manifest project -- existing block already at current
    # version must NOT be rewritten just because the manifest has no entry,
    # AND (regression for the real bug) it must still land in the manifest
    # even though its "unchanged" status never touched the on-disk block.
    preexisting_block = {"title": "# Foo Rules", "text": "# Version\n2\n\n# Foo Rules\n\nbody\n"}
    _, manifest_premanifest, report_premanifest = process_rules(
        [preexisting_block], src_dir.parent, ["FOO.md"], {}, {})
    assert report_premanifest[0]["status"] == "unchanged", report_premanifest
    assert manifest_premanifest == {"FOO.md": 2}, manifest_premanifest

    # process_rules: a conflicting rule must also stay on record, not vanish
    _, manifest_conflict, report_conflict = process_rules(
        [preexisting_block], src_dir.parent, ["FOO.md"], {"FOO.md": 9}, {})
    assert report_conflict[0]["status"] == "conflict", report_conflict
    assert manifest_conflict == {"FOO.md": 9}, manifest_conflict

    # reconcile_manifest: a block already in CODING_RULES.md whose rel was
    # never passed in --rules (real-world cause: an earlier, pre-manifest
    # install) must still be recorded.
    other_block = {"title": "# Bar Rules", "text": "# Version\n4\n\n# Bar Rules\n\nbody\n"}
    reconciled = reconcile_manifest([preexisting_block, other_block],
                                     {"FOO.md": 2}, {"# Foo Rules": "FOO.md", "# Bar Rules": "BAR.md"})
    assert reconciled == {"FOO.md": 2, "BAR.md": 4}, reconciled
    # already-recorded rels and unrecognized titles are left alone
    reconciled2 = reconcile_manifest([preexisting_block], {"FOO.md": 99}, {"# Foo Rules": "FOO.md"})
    assert reconciled2 == {"FOO.md": 99}, reconciled2  # not clobbered by the block's own version
    unrecognized_block = {"title": "# Untracked Section", "text": "# Version\n1\n\n# Untracked Section\n\nbody\n"}
    reconciled3 = reconcile_manifest([unrecognized_block], {}, {})
    assert reconciled3 == {}, reconciled3

    # rebuild_header: keep / explicit / mutual exclusivity
    header, resolved = rebuild_header("", "codex")
    assert resolved == "codex"
    assert "<!-- codex: enabled -->" in header and "<!-- deepseek: disabled -->" in header
    header2, resolved2 = rebuild_header(header, "keep")
    assert resolved2 == "codex"
    header3, resolved3 = rebuild_header(header2, "deepseek")
    assert resolved3 == "deepseek"
    assert "<!-- codex: disabled -->" in header3 and "<!-- deepseek: enabled -->" in header3

    # apply_pointer: absent -> insert, equal -> unchanged, manifest>source -> conflict
    text, ver, status = apply_pointer("Some preamble.\n", None, 1)
    assert status == "updated" and ver == 1 and POINTER_TITLE in text and "Some preamble." in text, text
    text2, ver2, status2 = apply_pointer(text, ver, 1)
    assert status2 == "unchanged", status2
    text3, ver3, status3 = apply_pointer(text, 5, 1)
    assert status3 == "conflict", status3

    # apply_pointer: pre-manifest project -- existing pointer already at
    # current version must not be rewritten just because manifest is absent
    text4, ver4, status4 = apply_pointer(text, None, 1)
    assert status4 == "unchanged" and ver4 == 1, (status4, ver4)

    # merge_json_permissions: create, append-missing, idempotent, invalid json
    tmp = Path(tempfile.mkdtemp())
    perm_path = tmp / "settings.local.json"
    changed, err = merge_json_permissions(perm_path, ["Bash(codex exec:*)", "PowerShell(codex exec:*)"])
    assert changed and err is None
    data = json.loads(read_text(perm_path))
    assert data["permissions"]["allow"] == ["Bash(codex exec:*)", "PowerShell(codex exec:*)"]
    changed2, _ = merge_json_permissions(perm_path, ["Bash(codex exec:*)"])
    assert changed2 is False
    bad_path = tmp / "bad.json"
    bad_path.write_text("{not json", encoding="utf-8")
    _, err2 = merge_json_permissions(bad_path, ["x"])
    assert err2 == "invalid_json"

    # merge_hooks: create, idempotent update-in-place, invalid json
    hooks_path = tmp / "settings.json"
    status = merge_hooks(hooks_path, "python")
    assert status == "ok"
    data = json.loads(read_text(hooks_path))
    assert len(data["hooks"]["PostToolUse"]) == 1
    status2 = merge_hooks(hooks_path, "python3")
    assert status2 == "ok"
    data2 = json.loads(read_text(hooks_path))
    assert len(data2["hooks"]["PostToolUse"]) == 1  # updated in place, not duplicated
    assert "python3" in data2["hooks"]["PostToolUse"][0]["hooks"][0]["command"]
    bad_hooks = tmp / "bad_settings.json"
    bad_hooks.write_text("[1,", encoding="utf-8")
    assert merge_hooks(bad_hooks, "python") == "error"

    # migrate_legacy: recognized block moved, unrecognized kept + reported
    title_to_rel = {"# Foo Rules": "FOO.md"}
    claude_src = "Preamble.\n\n# Version\n1\n\n# Foo Rules\n\nold body\n\n# Version\n1\n\n# Custom Section\n\nkeep me\n"
    new_text, migrated_map, unrecognized = migrate_legacy(claude_src, title_to_rel)
    assert migrated_map == {"FOO.md": 1}, migrated_map
    assert unrecognized == ["# Custom Section"], unrecognized
    assert "Foo Rules" not in new_text and "Custom Section" in new_text and "Preamble." in new_text

    # end-to-end run(): idempotent re-run, then a version bump only touches one block
    project = Path(tempfile.mkdtemp())
    plugin = Path(tempfile.mkdtemp())
    (plugin / "rules").mkdir()
    (plugin / "rules" / "FOO.md").write_text("# Version\n1\n\n# Foo Rules\n\nv1 body\n", encoding="utf-8")
    (plugin / "rules" / "BAR.md").write_text("# Version\n1\n\n# Bar Rules\n\nv1 body\n", encoding="utf-8")
    save_json(plugin / "rules" / "versions.json", {"pointer": 1, "FOO.md": 1, "BAR.md": 1})

    report1 = run(project, plugin, ["FOO.md", "BAR.md"], "neither", "python")
    assert all(r["status"] == "updated" for r in report1["rules"]), report1
    crm_text_1 = read_text(project / "CODING_RULES.md")

    report2 = run(project, plugin, ["FOO.md", "BAR.md"], "keep", "python")
    assert all(r["status"] == "unchanged" for r in report2["rules"]), report2
    assert read_text(project / "CODING_RULES.md") == crm_text_1  # idempotent

    (plugin / "rules" / "FOO.md").write_text("# Version\n2\n\n# Foo Rules\n\nv2 body\n", encoding="utf-8")
    save_json(plugin / "rules" / "versions.json", {"pointer": 1, "FOO.md": 2, "BAR.md": 1})
    report3 = run(project, plugin, ["FOO.md", "BAR.md"], "keep", "python")
    statuses = {r["rule"]: r["status"] for r in report3["rules"]}
    assert statuses == {"FOO.md": "updated", "BAR.md": "unchanged"}, statuses
    assert "v2 body" in read_text(project / "CODING_RULES.md")
    assert "v1 body" in read_text(project / "CODING_RULES.md")  # BAR untouched

    manifest = load_json(project / "coding-rules.json", {})
    assert manifest["rules"] == {"FOO.md": 2, "BAR.md": 1}, manifest

    # Reproduce the real-world bug: a project with CODING_RULES.md already
    # holding several blocks and no manifest yet, apply.py run with a request
    # list that only names ONE of those blocks. All must still end up recorded.
    project2 = Path(tempfile.mkdtemp())
    (project2 / "CODING_RULES.md").write_text(
        "<!-- Managed by /coding-rules:apply — do not edit rule blocks by hand -->\n\n"
        "# Version\n3\n\n# Foo Rules\n\nbody\n\n"
        "# Version\n1\n\n# Bar Rules\n\nbody\n\n"
        "# Version\n5\n\n# Baz Rules\n\nbody\n",
        encoding="utf-8",
    )
    (plugin / "rules" / "BAZ.md").write_text("# Version\n5\n\n# Baz Rules\n\nbody\n", encoding="utf-8")
    save_json(plugin / "rules" / "versions.json",
              {"pointer": 1, "FOO.md": 2, "BAR.md": 1, "BAZ.md": 5})
    report_real = run(project2, plugin, ["BAZ.md"], "neither", "python")
    manifest_real = load_json(project2 / "coding-rules.json", {})
    assert manifest_real["rules"] == {"FOO.md": 3, "BAR.md": 1, "BAZ.md": 5}, manifest_real

    print("self-test OK")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project")
    parser.add_argument("--plugin-root")
    parser.add_argument("--rules", default="")
    parser.add_argument("--delegation", default="keep", choices=["codex", "deepseek", "neither", "keep"])
    parser.add_argument("--python", default="python")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--check-versions", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        self_test()
        return
    if args.check_versions:
        plugin_root = Path(args.plugin_root) if args.plugin_root else Path(__file__).resolve().parents[2]
        check_versions(plugin_root)
        return
    if not args.project or not args.plugin_root:
        parser.error("--project and --plugin-root are required")

    rules = [r.strip() for r in args.rules.split(",") if r.strip()]
    report = run(Path(args.project), Path(args.plugin_root), rules, args.delegation, args.python)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_report(report)


if __name__ == "__main__":
    main()
