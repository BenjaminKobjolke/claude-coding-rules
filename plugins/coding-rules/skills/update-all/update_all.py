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


def load_settings(path):
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
            print(f"warning: folder does not exist, skipping: {folder}")
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


def update_project(project, plugin_root, manifest):
    """Apply the manifest's existing selection, isolating failures per repo."""
    try:
        versions = apply.load_json(plugin_root / "rules" / "versions.json", {})
        requested = list(mapped_rules(manifest))
        if GRAPHIFY in requested and GRAPHIFY_FLOW not in requested:
            requested.append(GRAPHIFY_FLOW)
        requested = [rel for rel in requested if rel in versions]
        return apply.run(project, plugin_root, requested, "keep")
    except Exception as exc:  # one broken checkout must not stop the bulk run
        return {"rules": [], "needs_user_decision": [], "errors": [str(exc)]}


def _details(items):
    return ", ".join(f"{rel} {old}→{new}" for rel, old, new in items)


def scan_projects(folders, ignore_prefixes, plugin_root, dry_run=False):
    versions = apply.load_json(plugin_root / "rules" / "versions.json", {})
    repos = sorted({repo for folder in folders for repo in find_repos(folder, ignore_prefixes)})
    counts = {"using": 0, "updated": 0, "current": 0, "decision": 0, "errors": 0}

    for project in repos:
        manifest_path = project / "coding-rules.json"
        if not manifest_path.exists():
            if (project / apply.RULES_FILE).exists():
                print(f"no manifest: {project} — run /coding-rules:apply there once")
            continue
        counts["using"] += 1
        try:
            manifest = apply.load_json(manifest_path, {})
            outdated, decisions = classify_manifest(manifest, versions)
        except Exception as exc:
            print(f"error: {project}: {exc}")
            counts["errors"] += 1
            continue

        if decisions:
            print(f"needs decision: {project}: {'; '.join(decisions)}")
            counts["decision"] += 1
        elif not outdated:
            counts["current"] += 1
        elif dry_run:
            print(f"would update: {project}: {_details(outdated)}")
            counts["updated"] += 1
        else:
            report = update_project(project, plugin_root, manifest)
            if report["errors"]:
                print(f"error: {project}: {report['errors']}")
                counts["errors"] += 1
            elif report["needs_user_decision"]:
                print(f"needs decision: {project}: {report['needs_user_decision']}")
                counts["decision"] += 1
            else:
                print(f"updated: {project}: {_details(outdated)}")
                counts["updated"] += 1

    print(
        f"{len(repos)} scanned, {counts['using']} using coding rules, "
        f"{counts['updated']} updated, {counts['current']} current, "
        f"{counts['decision']} need a decision, {counts['errors']} errors"
    )
    return 1 if counts["errors"] else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--settings", type=Path, default=Path.home() / ".coding-rules" / "settings.json")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        self_test()
        return 0
    try:
        folders, prefixes = load_settings(args.settings)
    except SettingsError as exc:
        print(f"error: {exc}")
        return 1
    return scan_projects(folders, prefixes, Path(__file__).resolve().parents[2], args.dry_run)


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
    print("self-test OK")


if __name__ == "__main__":
    raise SystemExit(main())
