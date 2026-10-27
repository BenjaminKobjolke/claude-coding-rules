"""Parsing and version-merging managed coding rule blocks."""

from apply_constants import HEADING_ALIASES, ATX_HEADING_RE
from file_io import read_text, write_text


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

def split_orphan_tail(block_text, src_text, all_levels=False, extra_headings=()):
    """Split an existing block into (managed_text, orphan_text) at the first
    non-fenced heading the source doc doesn't contain. The orphan is
    user-authored content that must survive a block replacement. See
    source_headings() for what all_levels changes."""
    known = source_headings(src_text, all_levels=all_levels) | set(extra_headings)
    lines = block_text.splitlines(keepends=True)
    in_fence = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        is_heading = (
            ATX_HEADING_RE.match(stripped)
            if all_levels
            else stripped.startswith("# ")
        )
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
            report.append(
                {"rule": rel, "status": "error", "detail": "source file not found"}
            )
            continue
        src_text = read_text(src_path)
        parsed_version, title = parse_source_version_title(src_text)
        version = versions.get(rel, parsed_version)
        existing = blocks_by_title.get(title)
        if existing is None:
            existing = next((blocks_by_title[alias]
                             for alias in HEADING_ALIASES.get(title, ())
                             if alias in blocks_by_title), None)
        applied = manifest_rules.get(rel)
        if applied is None and existing is not None:
            # No manifest entry yet (pre-manifest project) -- trust the version
            # already written in the existing block instead of treating it as
            # absent, so an up-to-date block isn't blindly rewritten.
            applied = parse_block_version(existing["text"])
        if applied is not None and applied > version:
            new_manifest_rules[rel] = applied  # keep the conflicting version on record
            report.append({"rule": rel, "status": "conflict",
                            "detail": (
                                f"manifest version {applied} > source version {version}"
                            )})
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
                            "detail": (
                                f"tailored block at version {applied}, "
                                f"source at {version} "
                                "— hand-merge required"
                            )})
            continue
        new_text = src_text if src_text.endswith("\n") else src_text + "\n"
        item = {"rule": rel, "status": "updated", "version": version}
        if existing is not None:
            _, orphan = split_orphan_tail(existing["text"], src_text)
            existing["text"] = new_text
            existing["title"] = title
            if orphan:
                orphan_title = next(
                    (
                        line.strip()
                        for line in orphan.splitlines()
                        if line.strip().startswith("# ")
                    ),
                    None,
                )
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
