"""Project headers, pointers, delegation, and hook setup."""

import json

from apply_constants import (
    MANAGED_COMMENT, MARKER_RE, POINTER_BLOCK_TEMPLATE, POINTER_TITLE,
)
from file_io import read_text, write_text
from rule_blocks import parse_block_version, parse_managed, split_orphan_tail


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
        lines.append(
            "<!-- codex: %s -->" % ("enabled" if resolved == "codex" else "disabled")
        )
        lines.append(
            "<!-- deepseek: %s -->"
            % ("enabled" if resolved == "deepseek" else "disabled")
        )
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

def apply_pointer(claude_text, manifest_pointer_version, source_version):
    """Returns (new_claude_text, resolved_pointer_version, status)."""
    lines, blocks = parse_managed(claude_text)
    existing = next((b for b in blocks if b["title"] == POINTER_TITLE), None)

    if manifest_pointer_version is None and existing is not None:
        # No manifest entry yet (pre-manifest project) -- trust the version
        # already in the existing pointer block instead of treating it as
        # absent, so an up-to-date pointer isn't rewritten for nothing.
        manifest_pointer_version = parse_block_version(existing["text"])

    if (
        existing is not None
        and manifest_pointer_version is not None
        and manifest_pointer_version > source_version
    ):
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

def install_delegate_wrappers(project, plugin_root):
    """Copy changed delegation wrappers into the project. Return whether changed."""
    source_dir = plugin_root / "rules" / "delegate_setup_files"
    changed = False
    for name in ("coding_rules_delegate.sh", "coding_rules_delegate.ps1"):
        source = read_text(source_dir / name)
        destination = project / "tools" / name
        if not destination.exists() or read_text(destination) != source:
            write_text(destination, source)
            changed = True
    return changed

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
