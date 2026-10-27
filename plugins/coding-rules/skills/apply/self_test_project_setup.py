"""Self-tests for apply project setup and migration behavior."""

from apply import run
from apply_constants import (
    DELEGATE_PERMS, DELEGATION_PERMS, FLOW_FILE, FLOW_TITLE, LEGACY_FLOW_TITLE,
    MANAGED_COMMENT, POINTER_BLOCK_TEMPLATE, POINTER_TITLE, RULES_FILE,
)
from file_io import load_json, read_text, save_json, write_text
from pathlib import Path
from project_setup import (
    apply_pointer, merge_json_permissions, rebuild_headers, uninstall_local_hooks,
)
from rule_migration import migrate_flow_blocks
import json
import tempfile


def self_test():
    # rebuild_headers: keep / explicit / mutual exclusivity, markers in the flow
    # file only, and a pre-split marker read out of CODING_RULES.md
    crm_h, flow_h, resolved = rebuild_headers("", "", "codex")
    assert resolved == "codex"
    assert (
        "<!-- codex: enabled -->" in flow_h
        and "<!-- deepseek: disabled -->" in flow_h
    )
    assert "codex" not in crm_h and crm_h.startswith(MANAGED_COMMENT)
    crm_h2, flow_h2, resolved2 = rebuild_headers(crm_h, flow_h, "keep")
    assert resolved2 == "codex"
    _, flow_h3, resolved3 = rebuild_headers(crm_h2, flow_h2, "deepseek")
    assert resolved3 == "deepseek"
    assert (
        "<!-- codex: disabled -->" in flow_h3
        and "<!-- deepseek: enabled -->" in flow_h3
    )
    # pre-split: the marker still sits in CODING_RULES.md and no flow file exists
    crm_h4, flow_h4, resolved4 = rebuild_headers(
        MANAGED_COMMENT + "\n<!-- codex: enabled -->\n<!-- deepseek: disabled -->\n",
        "", "keep",
    )
    assert resolved4 == "codex", resolved4
    assert "codex" not in crm_h4 and "<!-- codex: enabled -->" in flow_h4
    # unrelated header lines survive on their own side
    crm_h5, _, _ = rebuild_headers(
        "<!-- codex: enabled -->\nProject note.\n", "", "keep"
    )
    assert "Project note." in crm_h5

    # migrate_flow_blocks: legacy-titled block moves and is retitled; a copy the
    # flow file already owns is dropped rather than duplicated
    legacy_block = {
        "title": LEGACY_FLOW_TITLE,
        "text": f"# Version\n24\n\n{LEGACY_FLOW_TITLE}\n\nflow body\n",
    }
    quality_block = {
        "title": "# Foo Rules",
        "text": "# Version\n2\n\n# Foo Rules\n\nbody\n",
    }
    kept, flowed, moved_titles = migrate_flow_blocks([quality_block, legacy_block], [])
    assert kept == [quality_block], kept
    assert moved_titles == [FLOW_TITLE] and flowed[0]["title"] == FLOW_TITLE, (
        moved_titles, flowed
    )
    assert (
        FLOW_TITLE in flowed[0]["text"]
        and LEGACY_FLOW_TITLE not in flowed[0]["text"]
    )
    dup = {
        "title": LEGACY_FLOW_TITLE,
        "text": f"# Version\n24\n\n{LEGACY_FLOW_TITLE}\n\nstale\n",
    }
    already = {"title": FLOW_TITLE, "text": f"# Version\n25\n\n{FLOW_TITLE}\n\nnew\n"}
    kept2, flowed2, moved2 = migrate_flow_blocks([dup], [already])
    assert kept2 == [] and flowed2 == [already] and moved2 == [], (
        kept2, flowed2, moved2
    )

    # apply_pointer: absent -> insert, equal -> unchanged, manifest>source -> conflict
    text, ver, status = apply_pointer("Some preamble.\n", None, 1)
    assert (
        status == "updated" and ver == 1 and POINTER_TITLE in text
        and "Some preamble." in text
    ), text
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
    assert (
        "# CLAUDE.md" in text5 and "Project guidance." in text5
        and "`make`" in text5
    ), text5
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
                {"type": "command",
                 "command": "python .claude/hooks/coding-rules-reminder.py"}]}],
            "PreToolUse": [
                {"matcher": "Edit|Write|MultiEdit", "hooks": [
                    {"type": "command",
                     "command": "python .claude/hooks/coding-rules-reminder.py"},
                    dict(other)]},
                {"matcher": "Bash", "hooks": [dict(other)]},
            ],
        },
    }))
    assert uninstall_local_hooks(legacy) == "migrated"
    assert not (hooks_dir / "coding-rules-reminder.py").exists()
    # The user's disable flag survives the migration.
    assert (hooks_dir / "coding-rules-reminder.off").exists()
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

    # end-to-end run(): idempotent re-run, then a version bump only touches one block
    project = Path(tempfile.mkdtemp())
    plugin = Path(tempfile.mkdtemp())
    (plugin / "rules").mkdir()
    (plugin / "rules" / "FOO.md").write_text(
        "# Version\n1\n\n# Foo Rules\n\nv1 body\n", encoding="utf-8"
    )
    (plugin / "rules" / "BAR.md").write_text(
        "# Version\n1\n\n# Bar Rules\n\nv1 body\n", encoding="utf-8"
    )
    save_json(
        plugin / "rules" / "versions.json",
        {"pointer": 1, "FOO.md": 1, "BAR.md": 1},
    )

    report1 = run(project, plugin, ["FOO.md", "BAR.md"], "neither")
    assert all(r["status"] == "updated" for r in report1["rules"]), report1
    crm_text_1 = read_text(project / "CODING_RULES.md")

    report2 = run(project, plugin, ["FOO.md", "BAR.md"], "keep")
    assert all(r["status"] == "unchanged" for r in report2["rules"]), report2
    assert read_text(project / "CODING_RULES.md") == crm_text_1  # idempotent

    (plugin / "rules" / "FOO.md").write_text(
        "# Version\n2\n\n# Foo Rules\n\nv2 body\n", encoding="utf-8"
    )
    save_json(
        plugin / "rules" / "versions.json",
        {"pointer": 1, "FOO.md": 2, "BAR.md": 1},
    )
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
    (plugin / "rules" / "BAZ.md").write_text(
        "# Version\n5\n\n# Baz Rules\n\nbody\n", encoding="utf-8"
    )
    save_json(
        plugin / "rules" / "versions.json",
        {"pointer": 1, "FOO.md": 2, "BAR.md": 1, "BAZ.md": 5},
    )
    run(project2, plugin, ["BAZ.md"], "neither")
    manifest_real = load_json(project2 / "coding-rules.json", {})
    assert manifest_real["rules"] == {
        "FOO.md": 3, "BAR.md": 1, "BAZ.md": 5
    }, manifest_real

    # The rules/flow split: a pre-split project has the flow block inlined in
    # CODING_RULES.md and the codex marker in its header. Both must move to
    # IMPLEMENTATION_FLOW.md, everything else must stay put, and a second run
    # must report `unchanged` (i.e. the manifest rel rename took).
    split_plugin = Path(tempfile.mkdtemp())
    (split_plugin / "rules").mkdir()
    split_wrappers = split_plugin / "rules" / "delegate_setup_files"
    split_wrappers.mkdir()
    (split_wrappers / "coding_rules_delegate.sh").write_text(
        "shell\n", encoding="utf-8"
    )
    (split_wrappers / "coding_rules_delegate.ps1").write_text(
        "powershell\n", encoding="utf-8"
    )
    (split_plugin / "rules" / "FOO.md").write_text(
        "# Version\n1\n\n# Foo Rules\n\nquality body\n", encoding="utf-8")
    (split_plugin / "rules" / FLOW_FILE).write_text(
        f"# Version\n25\n\n{FLOW_TITLE}\n\nflow body v25\n", encoding="utf-8")
    save_json(
        split_plugin / "rules" / "versions.json",
        {"pointer": 2, "FOO.md": 1, FLOW_FILE: 25},
    )

    split_project = Path(tempfile.mkdtemp())
    write_text(
        split_project / RULES_FILE,
        MANAGED_COMMENT
        + "\n<!-- codex: enabled -->\n<!-- deepseek: disabled -->\n\n"
        "# Version\n1\n\n# Foo Rules\n\nquality body\n\n"
        f"# Version\n24\n\n{LEGACY_FLOW_TITLE}\n\nflow body v24\n",
    )
    save_json(
        split_project / "coding-rules.json",
        {"rules": {"FOO.md": 1, "AI_RULES.md": 24},
         "delegation": "codex", "pointerVersion": 1},
    )

    split_report = run(split_project, split_plugin, ["FOO.md", "AI_RULES.md"], "keep")
    split_statuses = {r["rule"]: r["status"] for r in split_report["rules"]}
    assert split_statuses == {
        "FOO.md": "unchanged", FLOW_FILE: "updated"
    }, split_statuses
    assert split_report["delegation"] == "codex", split_report
    crm_after = read_text(split_project / RULES_FILE)
    flow_after = read_text(split_project / FLOW_FILE)
    assert "quality body" in crm_after, crm_after
    assert "Workflow Rules" not in crm_after and "flow body" not in crm_after, crm_after
    assert "codex" not in crm_after, crm_after
    assert "<!-- codex: enabled -->" in flow_after, flow_after
    assert (
        "flow body v25" in flow_after and "flow body v24" not in flow_after
    ), flow_after
    assert "Foo Rules" not in flow_after, flow_after
    split_manifest = load_json(split_project / "coding-rules.json", {})
    assert split_manifest["rules"] == {"FOO.md": 1, FLOW_FILE: 25}, split_manifest
    assert "IMPLEMENTATION_FLOW.md" in read_text(split_project / "CLAUDE.md")

    split_report2 = run(split_project, split_plugin, ["FOO.md", FLOW_FILE], "keep")
    assert all(
        r["status"] == "unchanged" for r in split_report2["rules"]
    ), split_report2
    assert split_report2["pointer"] == "unchanged", split_report2
    assert read_text(split_project / RULES_FILE) == crm_after
    assert read_text(split_project / FLOW_FILE) == flow_after

