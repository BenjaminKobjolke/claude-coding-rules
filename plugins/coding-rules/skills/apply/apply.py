"""Deterministic core of the coding-rules:apply skill.

Owns the mechanical phases the skill used to hand-edit: version-merging rule
blocks into CODING_RULES.md, the CLAUDE.md pointer block, delegation markers +
settings.local.json permission merge, and clearing the legacy per-project
reminder-hook install (the hooks ship with the plugin now). Judgment calls
(which rule files apply, the delegation choice, an unrecognized legacy block)
stay with the skill/model -- this script reports them back via
`needs_user_decision` / `errors` instead of guessing.

State: `<project>/coding-rules.json` records what was last applied (per-rule
version, delegation, pointer version, plugin root) so a re-run only rewrites
what's stale. Source-of-truth versions come from
`<plugin-root>/rules/versions.json`; `--check-versions` guards that index
against the `# Version` header in each md file so they can't drift.

Run:  python apply.py --project <dir> --plugin-root <dir> --rules A.md,B.md [--delegation codex|deepseek|neither|keep] [--json]
Test: python apply.py --self-test
Guard: python apply.py --check-versions [--plugin-root <dir>]
"""

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

MANAGED_COMMENT = "<!-- Managed by /coding-rules:apply — do not edit rule blocks by hand -->"

# Two destinations. CODING_RULES.md holds code quality (binding always);
# IMPLEMENTATION_FLOW.md holds the orchestration steps, which an external
# orchestrator may run itself and therefore has to be able to ignore wholesale.
RULES_FILE = "CODING_RULES.md"
FLOW_FILE = "IMPLEMENTATION_FLOW.md"
FLOW_TITLE = "# Implementation Flow (All Languages)"
GRAPHIFY_FLOW_TITLE = "# graphify Flow Steps (Optional Addon)"
FLOW_RELS = {FLOW_FILE, "implementation_flow_addons/graphify_flow.md"}
FLOW_TITLES = {FLOW_TITLE, GRAPHIFY_FLOW_TITLE}

# Pre-split names, still found in already-applied projects and stale manifests.
LEGACY_FLOW_TITLE = "# AI Workflow Rules (All Languages)"
LEGACY_RELS = {
    "AI_RULES.md": FLOW_FILE,
    "ai_rules_addons/graphify.md": "implementation_flow_addons/graphify.md",
}
# Titles a source doc is also known by, so an old block isn't mistaken for
# user-authored content by split_orphan_tail during the migration.
HEADING_ALIASES = {FLOW_TITLE: {LEGACY_FLOW_TITLE}}

POINTER_TITLE = "# Coding Rules (Pointer)"
POINTER_BLOCK_TEMPLATE = """# Version
{version}

# Coding Rules (Pointer)

This project's rules live in two files in the project root:

- `CODING_RULES.md` — code quality and conventions. BINDING for all code work in
  this repository, always.
- `IMPLEMENTATION_FLOW.md` — the end-to-end flow to follow when planning and
  implementing a change (checks, gates, Definition of Done).

MANDATORY: Before writing or editing ANY code, you MUST Read BOTH files in full
**in the current session**. Do not rely on memory of a previous session, a
summary, or partial reads.

If you are about to make a code change and have not read both files in this
session: STOP, read them, then continue.

An external tool may orchestrate the implementation itself. When a skill or run
states that the implementation is orchestrated, ignore `IMPLEMENTATION_FLOW.md`
entirely — the orchestrator runs those steps as its own phases. `CODING_RULES.md`
stays binding either way.

Do not inline rules back into this file and do not use `@import` for either file —
they are intentionally referenced, not imported.
"""

# Both backends go through the same wrapper script (tools/coding_rules_delegate.*),
# so both need the same entries. Bare and ./-prefixed forms, because the allow
# entry is matched as a literal command prefix.
DELEGATE_PERMS = [
    "Bash(tools/coding_rules_delegate.sh:*)",
    "Bash(./tools/coding_rules_delegate.sh:*)",
    "PowerShell(tools/coding_rules_delegate.ps1:*)",
    "PowerShell(./tools/coding_rules_delegate.ps1:*)",
]

DELEGATION_PERMS = {
    "codex": DELEGATE_PERMS,
    "deepseek": DELEGATE_PERMS,
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


ATX_HEADING_RE = re.compile(r"^#{1,6} ")


def source_headings(src_text, all_levels=False):
    """Non-fenced headings of a source doc, incl. '# Version'. Sources may
    legitimately have more than one top-level heading (FLUTTER, PYTHON).

    Default (all_levels=False): top-level '# ' headings only -- process_rules'
    ongoing-update path, kept conservative so it never re-preserves a rule
    subsection the source deliberately removed.
    all_levels=True: every ATX heading level ('#'..'######') -- used only by
    the one-time legacy migration, where over-preservation beats deletion."""
    heads = {"# Version"}
    in_fence = False
    for line in src_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if all_levels and ATX_HEADING_RE.match(stripped):
            heads.add(stripped)
        elif not all_levels and stripped.startswith("# "):
            heads.add(stripped)
    for head in list(heads):
        heads |= HEADING_ALIASES.get(head, set())
    return heads


def split_orphan_tail(block_text, src_text, all_levels=False):
    """Split an existing block into (managed_text, orphan_text) at the first
    non-fenced heading the source doc doesn't contain. The orphan is
    user-authored content that must survive a block replacement. See
    source_headings() for what all_levels changes."""
    known = source_headings(src_text, all_levels=all_levels)
    lines = block_text.splitlines(keepends=True)
    in_fence = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        is_heading = ATX_HEADING_RE.match(stripped) if all_levels else stripped.startswith("# ")
        if is_heading and stripped not in known:
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


MARKER_RE = re.compile(r"^<!-- (codex|deepseek): (enabled|disabled) -->$")


def split_header(header_text):
    """-> (codex_state, deepseek_state, other_lines). Drops the managed comment
    and the delegation markers; keeps everything else the user put up there."""
    codex_state = deepseek_state = None
    other = []
    for line in header_text.splitlines():
        stripped = line.strip()
        m = MARKER_RE.match(stripped)
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
    return codex_state, deepseek_state, other


def compose_header(other_lines, resolved=None):
    """Managed comment, the delegation markers when `resolved` is given, then
    the user's own header lines."""
    lines = [MANAGED_COMMENT]
    if resolved is not None:
        lines.append("<!-- codex: %s -->" % ("enabled" if resolved == "codex" else "disabled"))
        lines.append("<!-- deepseek: %s -->" % ("enabled" if resolved == "deepseek" else "disabled"))
    lines.extend(other_lines)
    return "\n".join(lines) + "\n\n"


def rebuild_headers(rules_header, flow_header, delegation_choice):
    """Rebuild both file headers. The delegation markers live in
    IMPLEMENTATION_FLOW.md only -- delegation is a property of the flow, so a
    run that ignores the flow file must ignore its delegation setting too. A
    marker still sitting in CODING_RULES.md is a pre-split project: read it,
    then leave it behind. Returns (rules_header, flow_header, resolved)."""
    codex_r, deepseek_r, other_r = split_header(rules_header)
    codex_f, deepseek_f, other_f = split_header(flow_header)
    codex_state = codex_f if codex_f is not None else codex_r
    deepseek_state = deepseek_f if deepseek_f is not None else deepseek_r

    if delegation_choice == "keep":
        if codex_state == "enabled":
            resolved = "codex"
        elif deepseek_state == "enabled":
            resolved = "deepseek"
        else:
            resolved = "neither"
    else:
        resolved = delegation_choice

    return compose_header(other_r), compose_header(other_f, resolved), resolved


def destination_for(rel):
    return FLOW_FILE if rel in FLOW_RELS else RULES_FILE


def migrate_flow_blocks(rules_blocks, flow_blocks):
    """One-time split: move flow-owned blocks out of CODING_RULES.md into
    IMPLEMENTATION_FLOW.md, retitling the pre-split '# AI Workflow Rules' block
    so process_rules recognizes it (and so its version, and any user-authored
    tail below it, survive). Returns (rules_blocks, flow_blocks, moved_titles)."""
    keep, moved = [], []
    for b in rules_blocks:
        (moved if b["title"] in FLOW_TITLES or b["title"] == LEGACY_FLOW_TITLE else keep).append(b)
    present = {b["title"] for b in flow_blocks}
    moved_titles = []
    for b in moved:
        if b["title"] == LEGACY_FLOW_TITLE:
            b["text"] = b["text"].replace(LEGACY_FLOW_TITLE, FLOW_TITLE, 1)
            b["title"] = FLOW_TITLE
        if b["title"] in present:
            continue  # the flow file already owns it -- drop the stale copy
        flow_blocks.append(b)
        present.add(b["title"])
        moved_titles.append(b["title"])
    return keep, flow_blocks, moved_titles


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
        for alias in HEADING_ALIASES.get(title, ()):
            index.setdefault(alias, rel)
    return index


def strip_legacy_imports(text):
    lines = text.splitlines(keepends=True)
    return "".join(
        line for line in lines
        if not (line.strip().startswith("@") and "CODING_RULES.md" in line)
    )


def migrate_legacy(text, title_to_rel, plugin_root=None):
    """Move recognized legacy '# Version' blocks out of CLAUDE.md text into a
    migrated-versions dict; leave unrecognized ones untouched and reported.
    A recognized block's own content is dropped (it moves into CODING_RULES.md
    via process_rules), but any user-authored tail after the block's own
    headings -- e.g. project notes appended below the last inlined rule doc,
    which parse_managed's '# Version'-only split has no way to see as a
    separate block -- is preserved verbatim (regression: previously deleted
    whole). Returns (new_text, migrated_rel_to_version, unrecognized_titles)."""
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
            src_path = (plugin_root / "rules" / rel) if plugin_root else None
            try:
                src_text = read_text(src_path) if src_path else None
            except OSError:
                src_text = None
            if src_text is None:
                # Can't tell rule content from tail -- keep the whole block
                # rather than silently delete unknown user content.
                result_lines.extend(lines[b["start"]:b["end"]])
            else:
                _, orphan = split_orphan_tail(b["text"], src_text, all_levels=True)
                if orphan:
                    result_lines.append(orphan)
            continue
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
        # The pointer block runs to the next '# Version' line or EOF, so in the
        # common CLAUDE.md -- pointer on top, the project's own guidance below,
        # no further '# Version' -- that guidance is *inside* the block. Split it
        # back off at the first heading the template doesn't have, or replacing
        # the block deletes the whole file body.
        _, orphan = split_orphan_tail(
            existing["text"], POINTER_BLOCK_TEMPLATE.format(version=source_version),
            all_levels=True)
        rest_lines = lines[:existing["start"]] + [orphan] + lines[existing["end"]:]
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


def uninstall_local_hooks(project):
    """Remove the legacy per-project reminder-hook install.

    The hooks now ship with the plugin (hooks/hooks.json, ${CLAUDE_PLUGIN_ROOT}),
    so the copied script and the settings.json entries are dead weight — and the
    old entries used a relative path that broke whenever cwd was a subfolder.
    The user's coding-rules-reminder.off flag is kept. Returns a status string.
    """
    removed = False
    script = project / ".claude" / "hooks" / "coding-rules-reminder.py"
    if script.exists():
        script.unlink()
        removed = True

    path = project / ".claude" / "settings.json"
    if path.exists():
        raw = read_text(path)
        try:
            data = json.loads(raw) if raw.strip() else {}
        except json.JSONDecodeError:
            return "error"
        settings_changed = False
        hooks = data.get("hooks")
        if isinstance(hooks, dict):
            for event in list(hooks):
                arr = hooks.get(event)
                if not isinstance(arr, list):
                    continue
                kept = []
                for entry in arr:
                    inner = [h for h in entry.get("hooks", [])
                             if "coding-rules-reminder" not in h.get("command", "")]
                    if len(inner) != len(entry.get("hooks", [])):
                        settings_changed = True
                        if not inner:
                            continue
                        entry["hooks"] = inner
                    kept.append(entry)
                if kept:
                    hooks[event] = kept
                else:
                    del hooks[event]
            if not hooks:
                data.pop("hooks", None)
        if settings_changed:
            write_text(path, json.dumps(data, indent=2) + "\n")
            removed = True
    return "migrated" if removed else "plugin"


# -------------------------------------------------------------------- run

def run(project, plugin_root, requested_rules, delegation):
    versions = load_json(plugin_root / "rules" / "versions.json", {})
    manifest_path = project / "coding-rules.json"
    manifest = load_json(manifest_path, {})
    manifest.setdefault("rules", {})
    # Pre-split manifests key the flow rules by their old paths -- rename on
    # load so a migrated project reports `unchanged`, not a full re-apply.
    manifest["rules"] = {LEGACY_RELS.get(rel, rel): ver for rel, ver in manifest["rules"].items()}

    report = {"rules": [], "pointer": None, "delegation": None, "hooks": None,
              "needs_user_decision": [], "errors": []}

    # Phase B: migrate legacy blocks out of CLAUDE.md
    claude_path = project / "CLAUDE.md"
    claude_text = read_text(claude_path) if claude_path.exists() else ""
    title_to_rel = build_title_index(plugin_root, versions)
    claude_text, migrated, unrecognized = migrate_legacy(claude_text, title_to_rel, plugin_root)
    requested = list(dict.fromkeys(LEGACY_RELS.get(rel, rel) for rel in requested_rules))
    for rel, ver in migrated.items():
        manifest["rules"].setdefault(rel, ver)
        if rel not in requested:
            requested.append(rel)
    for title in unrecognized:
        report["needs_user_decision"].append(
            {"phase": "B", "detail": f"Unrecognized versioned block in CLAUDE.md: {title}"})

    # Phase C: version-merge rule blocks into their destination file
    crm_path = project / RULES_FILE
    flow_path = project / FLOW_FILE
    crm_header, crm_blocks = read_coding_rules(crm_path)
    flow_header, flow_blocks = read_coding_rules(flow_path)
    crm_blocks, flow_blocks, _moved = migrate_flow_blocks(crm_blocks, flow_blocks)

    rules_report = []
    merged = []
    for dest, dest_blocks in ((RULES_FILE, crm_blocks), (FLOW_FILE, flow_blocks)):
        subset = [rel for rel in requested if destination_for(rel) == dest]
        dest_blocks, manifest["rules"], dest_report = process_rules(
            dest_blocks, plugin_root, subset, manifest["rules"], versions)
        merged.append(dest_blocks)
        rules_report.extend(dest_report)
    crm_blocks, flow_blocks = merged

    report["rules"] = rules_report
    for item in rules_report:
        if item["status"] in ("conflict", "tailored-stale"):
            report["needs_user_decision"].append({"phase": "C", "detail": f"{item['rule']}: {item['detail']}"})
        elif item["status"] == "error":
            report["errors"].append({"phase": "C", "detail": f"{item['rule']}: {item['detail']}"})

    # Reconcile: record any recognized block already on disk that wasn't in
    # --rules this run (e.g. added by an earlier install), so the manifest
    # never lags behind what's actually in the files.
    manifest["rules"] = reconcile_manifest(crm_blocks + flow_blocks, manifest["rules"], title_to_rel)

    # Phase D2: delegation markers (they live in IMPLEMENTATION_FLOW.md)
    new_crm_header, new_flow_header, resolved_delegation = rebuild_headers(
        crm_header, flow_header, delegation)
    write_coding_rules(crm_path, new_crm_header, crm_blocks)
    if flow_blocks or flow_path.exists():
        write_coding_rules(flow_path, new_flow_header, flow_blocks)
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

    # Phase E: the reminder hooks ship with the plugin — clear any legacy local install
    manifest.pop("python", None)
    hook_status = uninstall_local_hooks(project)
    report["hooks"] = hook_status
    if hook_status == "error":
        report["errors"].append(
            {"phase": "E", "file": str(project / ".claude" / "settings.json"), "error": "invalid_json"})

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

    # rebuild_headers: keep / explicit / mutual exclusivity, markers in the flow
    # file only, and a pre-split marker read out of CODING_RULES.md
    crm_h, flow_h, resolved = rebuild_headers("", "", "codex")
    assert resolved == "codex"
    assert "<!-- codex: enabled -->" in flow_h and "<!-- deepseek: disabled -->" in flow_h
    assert "codex" not in crm_h and crm_h.startswith(MANAGED_COMMENT)
    crm_h2, flow_h2, resolved2 = rebuild_headers(crm_h, flow_h, "keep")
    assert resolved2 == "codex"
    _, flow_h3, resolved3 = rebuild_headers(crm_h2, flow_h2, "deepseek")
    assert resolved3 == "deepseek"
    assert "<!-- codex: disabled -->" in flow_h3 and "<!-- deepseek: enabled -->" in flow_h3
    # pre-split: the marker still sits in CODING_RULES.md and no flow file exists
    crm_h4, flow_h4, resolved4 = rebuild_headers(
        MANAGED_COMMENT + "\n<!-- codex: enabled -->\n<!-- deepseek: disabled -->\n", "", "keep")
    assert resolved4 == "codex", resolved4
    assert "codex" not in crm_h4 and "<!-- codex: enabled -->" in flow_h4
    # unrelated header lines survive on their own side
    crm_h5, _, _ = rebuild_headers("<!-- codex: enabled -->\nProject note.\n", "", "keep")
    assert "Project note." in crm_h5

    # migrate_flow_blocks: legacy-titled block moves and is retitled; a copy the
    # flow file already owns is dropped rather than duplicated
    legacy_block = {"title": LEGACY_FLOW_TITLE,
                    "text": f"# Version\n24\n\n{LEGACY_FLOW_TITLE}\n\nflow body\n"}
    quality_block = {"title": "# Foo Rules", "text": "# Version\n2\n\n# Foo Rules\n\nbody\n"}
    kept, flowed, moved_titles = migrate_flow_blocks([quality_block, legacy_block], [])
    assert kept == [quality_block], kept
    assert moved_titles == [FLOW_TITLE] and flowed[0]["title"] == FLOW_TITLE, (moved_titles, flowed)
    assert FLOW_TITLE in flowed[0]["text"] and LEGACY_FLOW_TITLE not in flowed[0]["text"]
    dup = {"title": LEGACY_FLOW_TITLE, "text": f"# Version\n24\n\n{LEGACY_FLOW_TITLE}\n\nstale\n"}
    already = {"title": FLOW_TITLE, "text": f"# Version\n25\n\n{FLOW_TITLE}\n\nnew\n"}
    kept2, flowed2, moved2 = migrate_flow_blocks([dup], [already])
    assert kept2 == [] and flowed2 == [already] and moved2 == [], (kept2, flowed2, moved2)

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

    # apply_pointer regression: the typical CLAUDE.md is the pointer block
    # followed by the project's own guidance and no further '# Version' line, so
    # that guidance parses as part of the pointer block. A version bump must not
    # delete it.
    with_body = (
        POINTER_BLOCK_TEMPLATE.format(version=1).rstrip("\n") + "\n\n"
        "# CLAUDE.md\n\nProject guidance.\n\n## Build\n\n`make`\n"
    )
    text5, ver5, status5 = apply_pointer(with_body, 1, 2)
    assert status5 == "updated" and ver5 == 2, (status5, ver5)
    assert "# CLAUDE.md" in text5 and "Project guidance." in text5 and "`make`" in text5, text5
    assert text5.count(POINTER_TITLE) == 1, text5
    assert "\n2\n" in text5.split(POINTER_TITLE)[0], text5

    # merge_json_permissions: create, append-missing, idempotent, invalid json
    tmp = Path(tempfile.mkdtemp())
    perm_path = tmp / "settings.local.json"
    changed, err = merge_json_permissions(perm_path, DELEGATE_PERMS)
    assert changed and err is None
    data = json.loads(read_text(perm_path))
    assert data["permissions"]["allow"] == DELEGATE_PERMS
    changed2, _ = merge_json_permissions(perm_path, DELEGATE_PERMS[:1])
    assert changed2 is False
    # both backends share the one wrapper, so both merge the same entries
    assert DELEGATION_PERMS["codex"] == DELEGATION_PERMS["deepseek"] == DELEGATE_PERMS
    bad_path = tmp / "bad.json"
    bad_path.write_text("{not json", encoding="utf-8")
    _, err2 = merge_json_permissions(bad_path, ["x"])
    assert err2 == "invalid_json"

    # uninstall_local_hooks: legacy install removed, foreign entries + .off kept
    legacy = Path(tempfile.mkdtemp())
    hooks_dir = legacy / ".claude" / "hooks"
    hooks_dir.mkdir(parents=True)
    (hooks_dir / "coding-rules-reminder.py").write_text("x", encoding="utf-8")
    (hooks_dir / "coding-rules-reminder.off").write_text("", encoding="utf-8")
    other = {"type": "command", "command": "python other.py"}
    write_text(legacy / ".claude" / "settings.json", json.dumps({
        "permissions": {"allow": ["Bash(ls:*)"]},
        "hooks": {
            "PostToolUse": [{"matcher": "ExitPlanMode", "hooks": [
                {"type": "command", "command": "python .claude/hooks/coding-rules-reminder.py"}]}],
            "PreToolUse": [
                {"matcher": "Edit|Write|MultiEdit", "hooks": [
                    {"type": "command", "command": "python .claude/hooks/coding-rules-reminder.py"},
                    dict(other)]},
                {"matcher": "Bash", "hooks": [dict(other)]},
            ],
        },
    }))
    assert uninstall_local_hooks(legacy) == "migrated"
    assert not (hooks_dir / "coding-rules-reminder.py").exists()
    assert (hooks_dir / "coding-rules-reminder.off").exists()  # user's disable flag survives
    left = json.loads(read_text(legacy / ".claude" / "settings.json"))
    assert "PostToolUse" not in left["hooks"]  # emptied event dropped
    assert left["hooks"]["PreToolUse"] == [
        {"matcher": "Edit|Write|MultiEdit", "hooks": [other]},
        {"matcher": "Bash", "hooks": [other]},
    ]
    assert left["permissions"]["allow"] == ["Bash(ls:*)"]
    assert uninstall_local_hooks(legacy) == "plugin"  # second run is a no-op
    clean = Path(tempfile.mkdtemp())
    assert uninstall_local_hooks(clean) == "plugin"
    bad_hooks = Path(tempfile.mkdtemp())
    write_text(bad_hooks / ".claude" / "settings.json", "[1,")
    assert uninstall_local_hooks(bad_hooks) == "error"

    # migrate_legacy: recognized block moved, unrecognized kept + reported
    legacy_plugin = Path(tempfile.mkdtemp())
    (legacy_plugin / "rules").mkdir()
    (legacy_plugin / "rules" / "FOO.md").write_text(
        "# Version\n1\n\n# Foo Rules\n\nnew body\n", encoding="utf-8")
    title_to_rel = {"# Foo Rules": "FOO.md"}
    claude_src = "Preamble.\n\n# Version\n1\n\n# Foo Rules\n\nold body\n\n# Version\n1\n\n# Custom Section\n\nkeep me\n"
    new_text, migrated_map, unrecognized = migrate_legacy(claude_src, title_to_rel, legacy_plugin)
    assert migrated_map == {"FOO.md": 1}, migrated_map
    assert unrecognized == ["# Custom Section"], unrecognized
    assert "Foo Rules" not in new_text and "Custom Section" in new_text and "Preamble." in new_text

    # migrate_legacy regression: a recognized block whose OWN text runs to EOF
    # (real-world cause: it's the last '# Version' block, so parse_managed has
    # no next-block boundary) carries a trailing '##' project section that is
    # NOT part of the rule source. That section must survive, not be deleted
    # whole along with the rule content.
    (legacy_plugin / "rules" / "BAR.md").write_text(
        "# Version\n1\n\n# Bar Rules\n\nrule body\n", encoding="utf-8")
    title_to_rel_bar = {"# Bar Rules": "BAR.md"}
    claude_src_tail = (
        "Preamble.\n\n"
        "# Version\n1\n\n# Bar Rules\n\nold rule body\n\n"
        "## Project Notes\n\nkeep me too\n"
    )
    new_text_tail, migrated_tail, _ = migrate_legacy(claude_src_tail, title_to_rel_bar, legacy_plugin)
    assert migrated_tail == {"BAR.md": 1}, migrated_tail
    assert "old rule body" not in new_text_tail and "Bar Rules" not in new_text_tail, new_text_tail
    assert "## Project Notes" in new_text_tail and "keep me too" in new_text_tail, new_text_tail
    assert "Preamble." in new_text_tail, new_text_tail

    # migrate_legacy: source file missing (rel recorded but unreadable) must
    # keep the whole block rather than silently delete unknown content.
    title_to_rel_missing = {"# Baz Rules": "BAZ_MISSING.md"}
    claude_src_missing = "# Version\n1\n\n# Baz Rules\n\nbody\n\n## Something\n\nstuff\n"
    new_text_missing, migrated_missing, _ = migrate_legacy(
        claude_src_missing, title_to_rel_missing, legacy_plugin)
    assert migrated_missing == {"BAZ_MISSING.md": 1}, migrated_missing
    assert "body" in new_text_missing and "## Something" in new_text_missing and "stuff" in new_text_missing

    # end-to-end run(): idempotent re-run, then a version bump only touches one block
    project = Path(tempfile.mkdtemp())
    plugin = Path(tempfile.mkdtemp())
    (plugin / "rules").mkdir()
    (plugin / "rules" / "FOO.md").write_text("# Version\n1\n\n# Foo Rules\n\nv1 body\n", encoding="utf-8")
    (plugin / "rules" / "BAR.md").write_text("# Version\n1\n\n# Bar Rules\n\nv1 body\n", encoding="utf-8")
    save_json(plugin / "rules" / "versions.json", {"pointer": 1, "FOO.md": 1, "BAR.md": 1})

    report1 = run(project, plugin, ["FOO.md", "BAR.md"], "neither")
    assert all(r["status"] == "updated" for r in report1["rules"]), report1
    crm_text_1 = read_text(project / "CODING_RULES.md")

    report2 = run(project, plugin, ["FOO.md", "BAR.md"], "keep")
    assert all(r["status"] == "unchanged" for r in report2["rules"]), report2
    assert read_text(project / "CODING_RULES.md") == crm_text_1  # idempotent

    (plugin / "rules" / "FOO.md").write_text("# Version\n2\n\n# Foo Rules\n\nv2 body\n", encoding="utf-8")
    save_json(plugin / "rules" / "versions.json", {"pointer": 1, "FOO.md": 2, "BAR.md": 1})
    report3 = run(project, plugin, ["FOO.md", "BAR.md"], "keep")
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
    report_real = run(project2, plugin, ["BAZ.md"], "neither")
    manifest_real = load_json(project2 / "coding-rules.json", {})
    assert manifest_real["rules"] == {"FOO.md": 3, "BAR.md": 1, "BAZ.md": 5}, manifest_real

    # The rules/flow split: a pre-split project has the flow block inlined in
    # CODING_RULES.md and the codex marker in its header. Both must move to
    # IMPLEMENTATION_FLOW.md, everything else must stay put, and a second run
    # must report `unchanged` (i.e. the manifest rel rename took).
    split_plugin = Path(tempfile.mkdtemp())
    (split_plugin / "rules").mkdir()
    (split_plugin / "rules" / "FOO.md").write_text(
        "# Version\n1\n\n# Foo Rules\n\nquality body\n", encoding="utf-8")
    (split_plugin / "rules" / FLOW_FILE).write_text(
        f"# Version\n25\n\n{FLOW_TITLE}\n\nflow body v25\n", encoding="utf-8")
    save_json(split_plugin / "rules" / "versions.json",
              {"pointer": 2, "FOO.md": 1, FLOW_FILE: 25})

    split_project = Path(tempfile.mkdtemp())
    write_text(split_project / RULES_FILE,
               MANAGED_COMMENT + "\n<!-- codex: enabled -->\n<!-- deepseek: disabled -->\n\n"
               "# Version\n1\n\n# Foo Rules\n\nquality body\n\n"
               f"# Version\n24\n\n{LEGACY_FLOW_TITLE}\n\nflow body v24\n")
    save_json(split_project / "coding-rules.json",
              {"rules": {"FOO.md": 1, "AI_RULES.md": 24}, "delegation": "codex", "pointerVersion": 1})

    split_report = run(split_project, split_plugin, ["FOO.md", "AI_RULES.md"], "keep")
    split_statuses = {r["rule"]: r["status"] for r in split_report["rules"]}
    assert split_statuses == {"FOO.md": "unchanged", FLOW_FILE: "updated"}, split_statuses
    assert split_report["delegation"] == "codex", split_report
    crm_after = read_text(split_project / RULES_FILE)
    flow_after = read_text(split_project / FLOW_FILE)
    assert "quality body" in crm_after, crm_after
    assert "Workflow Rules" not in crm_after and "flow body" not in crm_after, crm_after
    assert "codex" not in crm_after, crm_after
    assert "<!-- codex: enabled -->" in flow_after, flow_after
    assert "flow body v25" in flow_after and "flow body v24" not in flow_after, flow_after
    assert "Foo Rules" not in flow_after, flow_after
    split_manifest = load_json(split_project / "coding-rules.json", {})
    assert split_manifest["rules"] == {"FOO.md": 1, FLOW_FILE: 25}, split_manifest
    assert "IMPLEMENTATION_FLOW.md" in read_text(split_project / "CLAUDE.md")

    split_report2 = run(split_project, split_plugin, ["FOO.md", FLOW_FILE], "keep")
    assert all(r["status"] == "unchanged" for r in split_report2["rules"]), split_report2
    assert split_report2["pointer"] == "unchanged", split_report2
    assert read_text(split_project / RULES_FILE) == crm_after
    assert read_text(split_project / FLOW_FILE) == flow_after

    print("self-test OK")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project")
    parser.add_argument("--plugin-root")
    parser.add_argument("--rules", default="")
    parser.add_argument("--delegation", default="keep", choices=["codex", "deepseek", "neither", "keep"])
    parser.add_argument("--python", default="python", help=argparse.SUPPRESS)  # accepted, ignored: hooks ship with the plugin now
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
    report = run(Path(args.project), Path(args.plugin_root), rules, args.delegation)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_report(report)


if __name__ == "__main__":
    main()
