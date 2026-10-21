"""Update every git repository that already has a coding-rules manifest."""

import argparse
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apply"))
import apply  # noqa: E402

NOISE_DIRS = {"node_modules", ".venv", "venv", "__pycache__", ".mypy_cache", ".ruff_cache"}
SETTINGS_TEMPLATE = Path(__file__).resolve().parents[2] / "settings.example.json"
GRAPHIFY = "implementation_flow_addons/graphify.md"
GRAPHIFY_FLOW = "implementation_flow_addons/graphify_flow.md"


class SettingsError(ValueError):
    pass


def load_settings(path, warn=print):
    if not path.exists():
        example = path.with_name("settings.example.json")
        example.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SETTINGS_TEMPLATE, example)
        raise SettingsError(f"Settings not found. Copy {example} to settings.json and set your folders.")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SettingsError(f"Cannot read {path}: {exc}") from exc

    folders = data.get("folders")
    prefixes = data.get("ignore_prefixes", [])
    if not isinstance(folders, list) or not folders or not all(isinstance(x, str) and x for x in folders):
        raise SettingsError("'folders' must be a non-empty list of strings.")
    if not isinstance(prefixes, list) or not all(isinstance(x, str) and x for x in prefixes):
        raise SettingsError("'ignore_prefixes' entries must be non-empty strings.")

    existing = []
    for folder in map(Path, folders):
        if folder.is_dir():
            existing.append(folder)
        else:
            warn(f"warning: folder does not exist, skipping: {folder}")
    if not existing:
        raise SettingsError("None of the configured folders exist.")
    return existing, tuple(prefixes)


def find_repos(root, ignore_prefixes=()):
    """Yield git repos without descending into repos or ignored directories."""
    for dirpath, dirnames, _files in os.walk(root):
        current = Path(dirpath)
        if (current / ".git").exists():
            yield current
            dirnames[:] = []
            continue
        dirnames[:] = [
            name for name in dirnames
            if name not in NOISE_DIRS and not name.startswith(ignore_prefixes)
        ]


def mapped_rules(manifest):
    rules = manifest.get("rules", {})
    if not isinstance(rules, dict):
        return {}
    return {apply.LEGACY_RELS.get(rel, rel): version for rel, version in rules.items()}


def classify_manifest(manifest, versions):
    """Return (outdated triples, decisions) for one manifest."""
    rules = mapped_rules(manifest)
    if GRAPHIFY in rules and GRAPHIFY_FLOW not in rules:
        rules[GRAPHIFY_FLOW] = 0

    outdated = []
    decisions = []
    for rel, applied in rules.items():
        current = versions.get(rel)
        if current is None:
            decisions.append(f"unrecognized rule {rel}")
        elif not isinstance(applied, int):
            decisions.append(f"invalid applied version for {rel}: {applied!r}")
        elif applied < current:
            outdated.append((rel, applied, current))
        elif applied > current:
            decisions.append(f"{rel} is ahead of source ({applied} > {current})")

    applied_pointer = manifest.get("pointerVersion", 0)
    current_pointer = versions.get("pointer", 1)
    if not isinstance(applied_pointer, int):
        decisions.append(f"invalid pointer version: {applied_pointer!r}")
    elif applied_pointer < current_pointer:
        outdated.append(("pointer", applied_pointer, current_pointer))
    elif applied_pointer > current_pointer:
        decisions.append(f"pointer is ahead of source ({applied_pointer} > {current_pointer})")
    return outdated, decisions


def update_project(project, plugin_root, manifest, versions):
    """Apply the manifest's existing selection, isolating failures per repo."""
    try:
        requested = list(mapped_rules(manifest))
        if GRAPHIFY in requested and GRAPHIFY_FLOW not in requested:
            requested.append(GRAPHIFY_FLOW)
        requested = [rel for rel in requested if rel in versions]
        return apply.run(project, plugin_root, requested, "keep")
    except Exception as exc:  # one broken checkout must not stop the bulk run
        return {"rules": [], "needs_user_decision": [], "errors": [str(exc)]}


def _details(items):
    return ", ".join(f"{rel} {old}→{new}" for rel, old, new in items)


def _report_items(items):
    """Flatten apply.run's structured findings for the machine-readable report."""
    flattened = []
    for item in items:
        if isinstance(item, dict):
            phase = item.get("phase", "unknown")
            detail = item.get("detail")
            if detail is None:
                detail = f"{item.get('file', '')}: {item.get('error', '')}".strip(": ")
            flattened.append(f"[{phase}] {detail}")
        else:
            flattened.append(str(item))
    return flattened


def check_project(project, plugin_root, versions, dry_run=False, explicit=False, report_path=None):
    """Inspect or update one project and return its normalized report entry."""
    entry = {
        "path": str(project) if report_path is None else report_path, "status": "", "outdated": [],
        "decisions": [], "errors": [], "kept": [], "_using": False,
    }
    if explicit and not project.is_dir():
        entry["status"] = "error"
        entry["errors"].append("folder does not exist")
        entry["_message"] = f"error: {project}: folder does not exist"
        return entry

    manifest_path = project / "coding-rules.json"
    if not manifest_path.exists():
        rules_file = (project / apply.RULES_FILE).exists()
        if not explicit and not rules_file:
            return None
        entry["status"] = "no_manifest"
        entry["rules_file"] = rules_file
        entry["_message"] = (
            f"no manifest: {project} — run /coding-rules:apply there once" if rules_file else None
        )
        return entry

    entry["_using"] = True
    try:
        manifest = apply.load_json(manifest_path, {})
        outdated, decisions = classify_manifest(manifest, versions)
    except Exception as exc:
        entry["status"] = "error"
        entry["errors"].append(str(exc))
        entry["_message"] = f"error: {project}: {exc}"
        return entry

    entry["outdated"] = [
        {"rule": rel, "applied": old, "current": new} for rel, old, new in outdated
    ]
    if decisions:
        entry["status"] = "needs_decision"
        entry["decisions"] = decisions
        entry["_message"] = f"needs decision: {project}: {'; '.join(decisions)}"
    elif not outdated:
        entry["status"] = "current"
        entry["_message"] = None
    elif dry_run:
        entry["status"] = "updated"
        entry["_message"] = f"would update: {project}: {_details(outdated)}"
    else:
        report = update_project(project, plugin_root, manifest, versions)
        raw_errors = report["errors"]
        raw_decisions = report["needs_user_decision"]
        entry["_raw_errors"] = raw_errors
        entry["_raw_decisions"] = raw_decisions
        if raw_errors:
            entry["status"] = "error"
            entry["errors"] = _report_items(raw_errors)
            entry["_message"] = f"error: {project}: {raw_errors}"
        elif raw_decisions:
            entry["status"] = "needs_decision"
            entry["decisions"] = _report_items(raw_decisions)
            entry["_message"] = f"needs decision: {project}: {raw_decisions}"
        else:
            entry["status"] = "updated"
            entry["kept"] = report.get("split_kept", [])
            suffix = f" (kept: {', '.join(entry['kept'])})" if entry["kept"] else ""
            entry["_message"] = f"updated: {project}: {_details(outdated)}{suffix}"
    return entry


def run_projects(projects, plugin_root, dry_run=False, as_json=False, label_count=None,
                 explicit=False, report_paths=None):
    """Run the shared updater and report either human or JSON output."""
    versions = apply.load_json(plugin_root / "rules" / "versions.json", {})
    entries = []
    for index, project in enumerate(projects):
        report_path = report_paths[index] if report_paths is not None else None
        entry = check_project(project, plugin_root, versions, dry_run, explicit, report_path)
        if entry is not None:
            entries.append(entry)

    totals = {
        "projects": len(projects) if label_count is None else label_count,
        "using": 0, "updated": 0, "current": 0, "needs_decision": 0,
        "no_manifest": 0, "errors": 0,
    }
    for entry in entries:
        if entry["_using"]:
            totals["using"] += 1
        status_key = "errors" if entry["status"] == "error" else entry["status"]
        totals[status_key] += 1

    if as_json:
        clean_entries = [
            {key: value for key, value in entry.items() if not key.startswith("_")}
            for entry in entries
        ]
        print(json.dumps({"dry_run": dry_run, "projects": clean_entries, "totals": totals}, indent=2))
    else:
        for entry in entries:
            message = entry.get("_message")
            if message:
                print(message)
        print(
            f"{totals['projects']} scanned, {totals['using']} using coding rules, "
            f"{totals['updated']} updated, {totals['current']} current, "
            f"{totals['needs_decision']} need a decision, {totals['errors']} errors"
        )
    return 1 if totals["errors"] else 0


def scan_projects(folders, ignore_prefixes, plugin_root, dry_run=False, as_json=False):
    repos = sorted({repo for folder in folders for repo in find_repos(folder, ignore_prefixes)})
    return run_projects(repos, plugin_root, dry_run, as_json, len(repos))


def main(argv=None, plugin_root=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--settings", type=Path, default=Path.home() / ".coding-rules" / "settings.json")
    parser.add_argument("--project", action="append", help="Project folder to update (repeatable)")
    parser.add_argument("--json", action="store_true", help="Print a machine-readable JSON report")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        self_test()
        return 0
    if args.project is not None:
        project_paths = []
        seen = set()
        for raw_path in args.project:
            if raw_path not in seen:
                seen.add(raw_path)
                project_paths.append(raw_path)
        projects = [Path(raw_path) for raw_path in project_paths]
        return run_projects(
            projects, plugin_root or Path(__file__).resolve().parents[2], args.dry_run,
            args.json, len(projects), explicit=True, report_paths=project_paths,
        )
    try:
        warn = print if not args.json else lambda message: print(message, file=sys.stderr)
        folders, prefixes = load_settings(args.settings, warn=warn)
    except SettingsError as exc:
        if args.json:
            print(json.dumps({"error": str(exc)}))
        else:
            print(f"error: {exc}")
        return 1
    return scan_projects(
        folders, prefixes, plugin_root or Path(__file__).resolve().parents[2], args.dry_run, args.json,
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
    explicit_paths = [str(stale_copy), str(current), str(no_manifest), str(missing_project),
                      str(current), current_spelling]
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        assert main([
            *sum((["--project", path] for path in explicit_paths), []),
            "--json", "--dry-run",
        ], plugin_root=plugin) == 1
    explicit_json = json.loads(output.getvalue())
    assert explicit_json["dry_run"] is True, explicit_json
    assert [item["path"] for item in explicit_json["projects"]] == [
        str(stale_copy), str(current), str(no_manifest), str(missing_project), current_spelling,
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
    assert apply.load_json(stale_update / "coding-rules.json", {})["rules"]["FOO.md"] == 2

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
    assert outdated == [(apply.FLOW_FILE, 0, 1)] and not decisions, (outdated, decisions)
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
    assert missing.with_name("settings.example.json").read_bytes() == SETTINGS_TEMPLATE.read_bytes()
    missing.write_text(json.dumps({"folders": [str(root)], "ignore_prefixes": [""]}), encoding="utf-8")
    try:
        load_settings(missing)
        raise AssertionError("empty ignore prefix should fail")
    except SettingsError:
        pass
    python_source = rules / "PYTHON_RULES.md"
    python_source.write_text("# Version\n6\n\n# Python Rules (uv)\n\n## GUI Framework\n\nold GUI\n", encoding="utf-8")
    apply.save_json(rules / "versions.json", {"pointer": 1, "FOO.md": 2, "PYTHON_RULES.md": 6})
    desktop = repo("desktop")
    (desktop / "pyproject.toml").write_text('dependencies = ["pyside6"]\n', encoding="utf-8")
    apply.run(desktop, plugin, ["PYTHON_RULES.md"], "neither")
    (rules / "python").mkdir()
    (rules / "python" / "GUI.md").write_text(
        "# Version\n1\n\n# Python Desktop GUI (PySide6)\n\nnew GUI\n", encoding="utf-8")
    python_source.write_text("# Version\n7\n\n# Python Rules (uv)\n\nlean\n", encoding="utf-8")
    apply.save_json(rules / "versions.json", {"pointer": 1, "FOO.md": 2,
                    "PYTHON_RULES.md": 7, "python/GUI.md": 1})
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        assert scan_projects([root], ("_old_",), plugin) == 0
    assert "kept: python/GUI.md" in output.getvalue(), output.getvalue()
    assert "new GUI" in apply.read_text(desktop / apply.RULES_FILE)

    print("self-test OK")


if __name__ == "__main__":
    raise SystemExit(main())
