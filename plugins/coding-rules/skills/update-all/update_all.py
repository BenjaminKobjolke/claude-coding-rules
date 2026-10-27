"""Update every git repository that already has a coding-rules manifest."""

import argparse
import json
import sys
from pathlib import Path

from project_discovery import (
    SettingsError, find_repos, load_settings,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apply"))
import apply  # noqa: E402

GRAPHIFY = "implementation_flow_addons/graphify.md"
GRAPHIFY_FLOW = "implementation_flow_addons/graphify_flow.md"

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
        decisions.append(
            f"pointer is ahead of source ({applied_pointer} > {current_pointer})"
        )
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


def check_project(
    project, plugin_root, versions, dry_run=False, explicit=False, report_path=None
):
    """Inspect or update one project and return its normalized report entry."""
    entry = {
        "path": str(project) if report_path is None else report_path,
        "status": "", "outdated": [],
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
            (f"no manifest: {project} — run /coding-rules:apply there once"
             if rules_file else None)
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
        entry = check_project(
            project, plugin_root, versions, dry_run, explicit, report_path
        )
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
        print(json.dumps(
            {"dry_run": dry_run, "projects": clean_entries, "totals": totals},
            indent=2,
        ))
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
    repos = sorted(
        {repo for folder in folders for repo in find_repos(folder, ignore_prefixes)}
    )
    return run_projects(repos, plugin_root, dry_run, as_json, len(repos))


def main(argv=None, plugin_root=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--settings", type=Path, default=Path.home() / ".coding-rules" / "settings.json"
    )
    parser.add_argument(
        "--project", action="append", help="Project folder to update (repeatable)"
    )
    parser.add_argument(
        "--json", action="store_true", help="Print a machine-readable JSON report"
    )
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
        warn = (
            print if not args.json else lambda message: print(message, file=sys.stderr)
        )
        folders, prefixes = load_settings(args.settings, warn=warn)
    except SettingsError as exc:
        if args.json:
            print(json.dumps({"error": str(exc)}))
        else:
            print(f"error: {exc}")
        return 1
    return scan_projects(
        folders, prefixes, plugin_root or Path(__file__).resolve().parents[2],
        args.dry_run, args.json,
    )


def self_test():
    # Import lazily because tests import update_all, avoiding a startup cycle.
    from update_all_self_test import self_test as run_self_test

    run_self_test()


if __name__ == "__main__":
    raise SystemExit(main())
