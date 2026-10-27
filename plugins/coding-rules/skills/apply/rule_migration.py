"""Legacy rule migration and split-rule discovery."""

from apply_constants import (
    FLOW_FILE, FLOW_RELS, FLOW_TITLE, FLOW_TITLES, HEADING_ALIASES,
    LEGACY_FLOW_TITLE, POINTER_TITLE, RULES_FILE, SPLITS,
)
from file_io import read_text
from rule_blocks import (
    block_is_tailored, parse_block_version, parse_managed,
    parse_source_version_title,
    source_headings, split_orphan_tail,
)


def destination_for(rel):
    return FLOW_FILE if rel in FLOW_RELS else RULES_FILE

def migrate_flow_blocks(rules_blocks, flow_blocks):
    """One-time split: move flow-owned blocks out of CODING_RULES.md into
    IMPLEMENTATION_FLOW.md, retitling the pre-split '# AI Workflow Rules' block
    so process_rules recognizes it (and so its version, and any user-authored
    tail below it, survive). Returns (rules_blocks, flow_blocks, moved_titles)."""
    keep, moved = [], []
    for b in rules_blocks:
        (
            moved
            if b["title"] in FLOW_TITLES or b["title"] == LEGACY_FLOW_TITLE
            else keep
        ).append(b)
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
        return text, {}, [], []
    lines, blocks = parse_managed(text)
    if not blocks:
        return strip_legacy_imports(text), {}, [], []

    header_end = blocks[0]["start"]
    result_lines = list(lines[:header_end])
    migrated = {}
    unrecognized = []
    tailored = []
    for b in blocks:
        if b["title"] == POINTER_TITLE:
            result_lines.extend(lines[b["start"]:b["end"]])
            continue
        rel = title_to_rel.get(b["title"])
        ver = parse_block_version(b["text"]) if rel else None
        if rel and ver is not None:
            if block_is_tailored(b["text"]):
                tailored.append(rel)
                result_lines.extend(lines[b["start"]:b["end"]])
                continue
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
                extra = set()
                if rel in SPLITS and ver < SPLITS[rel][0]:
                    for optional in SPLITS[rel][1]:
                        optional_path = plugin_root / "rules" / optional
                        if optional_path.exists():
                            extra |= source_headings(
                                read_text(optional_path), all_levels=True
                            )
                _, orphan = split_orphan_tail(b["text"], src_text, all_levels=True,
                                              extra_headings=extra)
                if orphan:
                    result_lines.append(orphan)
            continue
        unrecognized.append(b["title"] or "(untitled block)")
        result_lines.extend(lines[b["start"]:b["end"]])
    return strip_legacy_imports("".join(result_lines)), migrated, unrecognized, tailored

def project_uses(project, markers):
    pyproject = project / "pyproject.toml"
    project_text = read_text(pyproject) if pyproject.exists() else ""
    composer = project / "composer.json"
    if composer.exists():
        project_text += "\n" + read_text(composer)
    project_files = [path for pattern in ("*.csproj", "*/*.csproj")
                     for path in project.glob(pattern)]
    project_text += "\n" + "\n".join(read_text(path) for path in project_files)
    project_text = project_text.lower()
    # ponytail: substring matching in project manifests sees comments
    # and may keep extra rules; parse dependencies if false positives become a problem.
    return any((project / marker).exists() or marker.lower() in project_text
               for marker in markers)

def split_supplements(
    project, blocks, migrated, manifest_rules, requested, title_to_rel
):
    kept = []
    for parent, (split_version, optional_files) in SPLITS.items():
        if parent not in requested:
            continue
        existing = next(
            (b for b in blocks if title_to_rel.get(b["title"]) == parent), None
        )
        if existing is None and parent not in migrated:
            continue
        if existing is not None and block_is_tailored(existing["text"]):
            continue
        applied = manifest_rules.get(parent)
        if applied is None:
            applied = (
                parse_block_version(existing["text"]) if existing else migrated[parent]
            )
        if applied is None or applied >= split_version:
            continue
        for rel, markers in optional_files.items():
            if rel not in requested and project_uses(project, markers):
                kept.append(rel)
    return kept
