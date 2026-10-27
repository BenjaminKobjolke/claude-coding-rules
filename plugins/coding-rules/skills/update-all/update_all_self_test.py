"""Self-tests for update-all scanning and project discovery."""

import contextlib
import io
import json
import os
import tempfile
from pathlib import Path

import apply
from project_discovery import SETTINGS_TEMPLATE, SettingsError, load_settings
from update_all import (
    GRAPHIFY, GRAPHIFY_FLOW, check_project, classify_manifest, main, scan_projects,
)


def self_test():
    temp = Path(tempfile.mkdtemp())
    plugin = temp / "plugin"
    rules = plugin / "rules"
    rules.mkdir(parents=True)
    source = rules / "FOO.md"
    source.write_text("# Version\n1\n\n# Foo Rules\n\nv1\n", encoding="utf-8")
    apply.save_json(rules / "versions.json", {"pointer": 1, "FOO.md": 1})

    root = temp / "repos"
    root.mkdir()

    def repo(name):
        project = root / name
        (project / ".git").mkdir(parents=True)
        return project

    stale = repo("stale")
    apply.run(stale, plugin, ["FOO.md"], "neither")
    (stale / "nested" / ".git").mkdir(parents=True)

    source.write_text("# Version\n2\n\n# Foo Rules\n\nv2\n", encoding="utf-8")
    apply.save_json(rules / "versions.json", {"pointer": 1, "FOO.md": 2})
    current = repo("current")
    apply.run(current, plugin, ["FOO.md"], "neither")
    current_before = apply.read_text(current / apply.RULES_FILE)

    ignored = root / "_old_x" / "ignored"
    (ignored / ".git").mkdir(parents=True)
    no_manifest = repo("no-manifest")
    (no_manifest / apply.RULES_FILE).write_text("old install\n", encoding="utf-8")

    stale_before = apply.read_text(stale / apply.RULES_FILE)
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        assert scan_projects([root], ("_old_",), plugin, dry_run=True) == 0
    assert apply.read_text(stale / apply.RULES_FILE) == stale_before
    assert "would update:" in output.getvalue() and "no manifest:" in output.getvalue()
    assert "3 scanned" in output.getvalue(), output.getvalue()

    with contextlib.redirect_stdout(io.StringIO()):
        assert scan_projects([root], ("_old_",), plugin) == 0
    assert apply.load_json(stale / "coding-rules.json", {})["rules"]["FOO.md"] == 2
    assert apply.read_text(current / apply.RULES_FILE) == current_before
    assert (stale / "CODING_RULES_PLAN.md").exists()

    pointer_stale = temp / "pointer-stale"
    pointer_stale.mkdir()
    (pointer_stale / ".git").mkdir()
    apply.run(pointer_stale, plugin, ["FOO.md"], "neither")
    pointer_manifest = apply.load_json(pointer_stale / "coding-rules.json", {})
    pointer_manifest["pointerVersion"] = 0
    apply.save_json(pointer_stale / "coding-rules.json", pointer_manifest)
    for filename in (
        "CODING_RULES_PLAN.md", "CODING_RULES_REVIEW.md", "CODING_RULES_CODE.md"
    ):
        (pointer_stale / filename).unlink()
    pointer_entry = check_project(
        pointer_stale, plugin, apply.load_json(rules / "versions.json", {})
    )
    assert pointer_entry["status"] == "updated" and pointer_entry["outdated"] == [
        {"rule": "pointer", "applied": 0, "current": 1},
    ], pointer_entry
    assert (pointer_stale / "CODING_RULES_PLAN.md").exists()

    # JSON scan mode keeps the same repo selection, including its scanned count.
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        assert scan_projects([root], ("_old_",), plugin, as_json=True) == 0
    scan_json = json.loads(output.getvalue())
    assert scan_json["totals"]["projects"] == 3, scan_json
    assert all("_old_" not in item["path"] for item in scan_json["projects"]), scan_json

    def stale_json_repo(name):
        project = repo(name)
        apply.run(project, plugin, ["FOO.md"], "neither")
        manifest = apply.load_json(project / "coding-rules.json", {})
        manifest["rules"]["FOO.md"] = 1
        apply.save_json(project / "coding-rules.json", manifest)
        return project

    stale_copy = stale_json_repo("stale-copy")
    stale_copy_before = apply.read_text(stale_copy / apply.RULES_FILE)
    missing_project = root / "missing-project"
    current_spelling = os.path.join(str(current.parent), ".", current.name)
    explicit_paths = [
        str(stale_copy), str(current), str(no_manifest), str(missing_project),
        str(current), current_spelling,
    ]
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        assert main([
            *sum((["--project", path] for path in explicit_paths), []),
            "--json", "--dry-run",
        ], plugin_root=plugin) == 1
    explicit_json = json.loads(output.getvalue())
    assert explicit_json["dry_run"] is True, explicit_json
    assert [item["path"] for item in explicit_json["projects"]] == [
        str(stale_copy), str(current), str(no_manifest), str(missing_project),
        current_spelling,
    ], explicit_json
    assert [item["status"] for item in explicit_json["projects"]] == [
        "updated", "current", "no_manifest", "error", "current",
    ], explicit_json
    assert explicit_json["projects"][2]["rules_file"] is True, explicit_json
    assert explicit_json["totals"] == {
        "projects": 5, "using": 3, "updated": 1, "current": 2,
        "needs_decision": 0, "no_manifest": 1, "errors": 1,
    }, explicit_json
    assert apply.read_text(stale_copy / apply.RULES_FILE) == stale_copy_before

    stale_update = stale_json_repo("stale-update")
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        assert main(["--project", str(stale_update), "--json"], plugin_root=plugin) == 0
    update_json = json.loads(output.getvalue())
    assert update_json["projects"][0]["status"] == "updated", update_json
    assert update_json["projects"][0]["outdated"] == [
        {"rule": "FOO.md", "applied": 1, "current": 2},
    ], update_json
    assert (
        apply.load_json(stale_update / "coding-rules.json", {})["rules"]["FOO.md"]
        == 2
    )

    # Exercise argparse wiring against the real plugin root without a manifest.
    cli_project = temp / "cli-project"
    cli_project.mkdir()
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        assert main(["--project", str(cli_project), "--json", "--dry-run"]) == 0
    assert json.loads(output.getvalue())["projects"][0]["status"] == "no_manifest"

    classification_versions = {
        "pointer": 1,
        apply.FLOW_FILE: 1,
        GRAPHIFY: 1,
        GRAPHIFY_FLOW: 1,
    }
    outdated, decisions = classify_manifest(
        {"rules": {"AI_RULES.md": 0}, "pointerVersion": 1}, classification_versions)
    assert outdated == [(apply.FLOW_FILE, 0, 1)] and not decisions, (
        outdated, decisions
    )
    outdated, decisions = classify_manifest(
        {"rules": {GRAPHIFY: 1}, "pointerVersion": 1}, classification_versions)
    assert (GRAPHIFY_FLOW, 0, 1) in outdated and not decisions, (outdated, decisions)
    _, decisions = classify_manifest(
        {"rules": {GRAPHIFY: 2, "UNKNOWN.md": 1}, "pointerVersion": 1},
        classification_versions,
    )
    assert len(decisions) == 2, decisions

    missing = temp / "settings" / "settings.json"
    try:
        load_settings(missing)
        raise AssertionError("missing settings should fail")
    except SettingsError:
        pass
    assert (
        missing.with_name("settings.example.json").read_bytes()
        == SETTINGS_TEMPLATE.read_bytes()
    )
    missing.write_text(
        json.dumps({"folders": [str(root)], "ignore_prefixes": [""]}),
        encoding="utf-8",
    )
    try:
        load_settings(missing)
        raise AssertionError("empty ignore prefix should fail")
    except SettingsError:
        pass
    python_source = rules / "PYTHON_RULES.md"
    python_source.write_text(
        "# Version\n6\n\n# Python Rules (uv)\n\n## GUI Framework\n\nold GUI\n",
        encoding="utf-8",
    )
    apply.save_json(
        rules / "versions.json",
        {"pointer": 1, "FOO.md": 2, "PYTHON_RULES.md": 6},
    )
    desktop = repo("desktop")
    (desktop / "pyproject.toml").write_text(
        'dependencies = ["pyside6"]\n', encoding="utf-8"
    )
    apply.run(desktop, plugin, ["PYTHON_RULES.md"], "neither")
    (rules / "python").mkdir()
    (rules / "python" / "GUI.md").write_text(
        "# Version\n1\n\n# Python Desktop GUI (PySide6)\n\nnew GUI\n", encoding="utf-8")
    python_source.write_text(
        "# Version\n7\n\n# Python Rules (uv)\n\nlean\n", encoding="utf-8"
    )
    apply.save_json(rules / "versions.json", {"pointer": 1, "FOO.md": 2,
                    "PYTHON_RULES.md": 7, "python/GUI.md": 1})
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        assert scan_projects([root], ("_old_",), plugin) == 0
    assert "kept: python/GUI.md" in output.getvalue(), output.getvalue()
    assert "new GUI" in apply.read_text(desktop / apply.RULES_FILE)

    print("self-test OK")
