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

Run:  python apply.py --project <dir> --plugin-root <dir> --rules A.md,B.md
      [--delegation codex|deepseek|neither|keep] [--json]
Test: python apply.py --self-test
Guard: python apply.py --check-versions [--plugin-root <dir>]
"""

import argparse
import json
import sys
from pathlib import Path

import step_rules

from apply_constants import DELEGATION_PERMS, FLOW_FILE, LEGACY_RELS, RULES_FILE
from file_io import load_json, read_text, save_json, write_text
from project_setup import (
    apply_pointer, install_delegate_wrappers, merge_json_permissions,
)
from project_setup import rebuild_headers, uninstall_local_hooks
from rule_blocks import block_is_tailored, parse_source_version_title, process_rules
from rule_blocks import read_coding_rules, reconcile_manifest, write_coding_rules
from rule_migration import build_title_index, destination_for, migrate_flow_blocks
from rule_migration import migrate_legacy, split_supplements


# -------------------------------------------------------------- CLAUDE.md


def run(project, plugin_root, requested_rules, delegation):
    versions = load_json(plugin_root / "rules" / "versions.json", {})
    manifest_path = project / "coding-rules.json"
    manifest = load_json(manifest_path, {})
    manifest.setdefault("rules", {})
    # Pre-split manifests key the flow rules by their old paths -- rename on
    # load so a migrated project reports `unchanged`, not a full re-apply.
    manifest["rules"] = {
        LEGACY_RELS.get(rel, rel): ver for rel, ver in manifest["rules"].items()
    }

    report = {
        "rules": [], "split_kept": [], "pointer": None, "delegation": None,
        "hooks": None, "needs_user_decision": [], "errors": [], "step_files": [],
    }

    # Phase B: migrate legacy blocks out of CLAUDE.md
    claude_path = project / "CLAUDE.md"
    claude_text = read_text(claude_path) if claude_path.exists() else ""
    title_to_rel = build_title_index(plugin_root, versions)
    claude_text, migrated, unrecognized, tailored = migrate_legacy(
        claude_text, title_to_rel, plugin_root)
    requested = list(
        dict.fromkeys(LEGACY_RELS.get(rel, rel) for rel in requested_rules)
    )
    for rel in tailored:
        if rel in requested:
            requested.remove(rel)
        report["needs_user_decision"].append(
            {"phase": "B", "detail": (
                f"Tailored legacy block in CLAUDE.md: {rel} — hand-merge required"
            )})
    for rel, ver in migrated.items():
        manifest["rules"].setdefault(rel, ver)
        if rel not in requested:
            requested.append(rel)
    for title in unrecognized:
        report["needs_user_decision"].append(
            {"phase": "B", "detail": (
                f"Unrecognized versioned block in CLAUDE.md: {title}"
            )})

    # Phase C: version-merge rule blocks into their destination file
    crm_path = project / RULES_FILE
    flow_path = project / FLOW_FILE
    crm_header, crm_blocks = read_coding_rules(crm_path)
    flow_header, flow_blocks = read_coding_rules(flow_path)
    crm_blocks, flow_blocks, _moved = migrate_flow_blocks(crm_blocks, flow_blocks)
    report["split_kept"] = split_supplements(
        project, crm_blocks, migrated, manifest["rules"], requested, title_to_rel)
    requested.extend(report["split_kept"])

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
            report["needs_user_decision"].append(
                {"phase": "C", "detail": f"{item['rule']}: {item['detail']}"}
            )
        elif item["status"] == "error":
            report["errors"].append(
                {"phase": "C", "detail": f"{item['rule']}: {item['detail']}"}
            )

    # Reconcile: record any recognized block already on disk that wasn't in
    # --rules this run (e.g. added by an earlier install), so the manifest
    # never lags behind what's actually in the files.
    manifest["rules"] = reconcile_manifest(
        crm_blocks + flow_blocks, manifest["rules"], title_to_rel
    )

    # Phase D2: delegation markers (they live in IMPLEMENTATION_FLOW.md)
    new_crm_header, new_flow_header, resolved_delegation = rebuild_headers(
        crm_header, flow_header, delegation)
    write_coding_rules(crm_path, new_crm_header, crm_blocks)
    generated_blocks = step_rules.step_blocks(crm_blocks)
    for step, filename in step_rules.STEP_FILES.items():
        blocks = generated_blocks[filename]
        step_path = project / filename
        if blocks:
            write_coding_rules(
                step_path, step_rules.step_header(new_crm_header, step), blocks
            )
            report["step_files"].append(filename)
        elif step_path.exists():
            step_path.unlink()
    if flow_blocks or flow_path.exists():
        write_coding_rules(flow_path, new_flow_header, flow_blocks)
    manifest["delegation"] = resolved_delegation
    report["delegation"] = resolved_delegation
    if resolved_delegation in DELEGATION_PERMS:
        install_delegate_wrappers(project, plugin_root)
        settings_local = project / ".claude" / "settings.local.json"
        changed, err = merge_json_permissions(
            settings_local, DELEGATION_PERMS[resolved_delegation]
        )
        if err:
            report["errors"].append(
                {"phase": "D2", "file": str(settings_local), "error": err}
            )

    # Phase D: pointer block in CLAUDE.md
    pointer_version = versions.get("pointer", 1)
    new_claude_text, resolved_pointer_version, pointer_status = apply_pointer(
        claude_text, manifest.get("pointerVersion"), pointer_version)
    write_text(claude_path, new_claude_text)
    manifest["pointerVersion"] = resolved_pointer_version
    report["pointer"] = pointer_status
    if pointer_status == "conflict":
        report["needs_user_decision"].append(
            {"phase": "D", "detail": (
                f"CLAUDE.md pointer version {manifest.get('pointerVersion')} "
                f"> source {pointer_version}"
            )})

    # Phase E: the reminder hooks ship with the plugin — clear any legacy local install
    manifest.pop("python", None)
    hook_status = uninstall_local_hooks(project)
    report["hooks"] = hook_status
    if hook_status == "error":
        report["errors"].append(
            {"phase": "E", "file": str(project / ".claude" / "settings.json"),
             "error": "invalid_json"})

    manifest["pluginRoot"] = str(plugin_root)
    save_json(manifest_path, manifest)
    return report


def print_report(report):
    for item in report["rules"]:
        print(f"  rule {item['rule']}: {item['status']}")
    if report["split_kept"]:
        print(f"  kept: {', '.join(report['split_kept'])}")
    if report.get("step_files"):
        print(f"  step files: {', '.join(report['step_files'])}")
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
    rule docs subject to this check. Unversioned setup templates are skipped."""
    versions_path = plugin_root / "rules" / "versions.json"
    versions = load_json(versions_path, {})
    problems = []
    seen = set()
    for md in sorted((plugin_root / "rules").rglob("*.md")):
        text = read_text(md)
        first_line = text.splitlines()[0].strip() if text.strip() else ""
        if first_line != "# Version":
            continue
        rel = md.relative_to(plugin_root / "rules").as_posix()
        seen.add(rel)
        try:
            step_rules.check_markers(text)
            version, _ = parse_source_version_title(text)
        except ValueError as e:
            problems.append(f"{rel}: invalid rule file ({e})")
            continue
        if rel not in versions:
            problems.append(f"{rel}: missing from versions.json")
        elif versions[rel] != version:
            problems.append(
                f"{rel}: versions.json has {versions[rel]}, header has {version}"
            )
        if block_is_tailored(text):
            problems.append(
                f"{rel}: shipped source contains a '<!-- tailored -->' marker "
                "(project-only marker)"
            )
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
    step_rules.self_test()

    # Import lazily because tests import apply, which would cycle during startup.
    from self_test_blocks import self_test as test_blocks
    from self_test_project_setup import self_test as test_project_setup
    from self_test_python_split import self_test as test_python_split
    from self_test_shipped_rules import self_test as test_shipped_rules

    for test in (
        test_blocks, test_project_setup, test_python_split, test_shipped_rules
    ):
        test()
    print("self-test OK")

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project")
    parser.add_argument("--plugin-root")
    parser.add_argument("--rules", default="")
    parser.add_argument(
        "--delegation", default="keep", choices=["codex", "deepseek", "neither", "keep"]
    )
    parser.add_argument(
        "--python", default="python", help=argparse.SUPPRESS
    )  # accepted, ignored: hooks ship with the plugin now
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--check-versions", action="store_true")
    args = parser.parse_args(argv)

    if args.self_test:
        self_test()
        return
    if args.check_versions:
        plugin_root = (
            Path(args.plugin_root)
            if args.plugin_root
            else Path(__file__).resolve().parents[2]
        )
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
