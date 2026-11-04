"""Self-tests for the shipped API contract repo rule."""

import re

from file_io import load_json
from file_io import read_text


def self_test(shipped_root, shipped_versions):
    rule_path = "project_type/API_CONTRACT.md"
    assert shipped_versions.get(rule_path) == 1
    rule = read_text(shipped_root / "rules" / rule_path)
    assert rule.startswith("# Version\n1\n")
    assert all(term in rule.lower() for term in (
        "api_to_client", "client_to_api", "submodule", "never rename",
    ))

    versions = load_json(shipped_root / "rules" / "versions.json", {})
    assert versions.get(rule_path) == 1

    project_types = read_text(shipped_root / "rules" / "PROJECT_TYPES.md")
    assert re.search(r"(?m)^## API Contract(?:\s|$)", project_types)

    apply_skill = read_text(shipped_root / "skills" / "apply" / "SKILL.md")
    detection = re.search(
        r"(?m)^- API contract repo:(.*(?:\n  .*)*)",
        apply_skill,
    )
    assert detection, "apply skill is missing the API contract detection section"
    detection = detection.group(0).lower()
    assert "root `*.json` contract files" in detection
    assert "`readme.md` naming the producer and consumers" in detection
    assert all(manifest in detection for manifest in (
        "`composer.json`", "`pyproject.toml`", "`pubspec.yaml`", "`package.json`",
    ))
    assert "gets `project_type/api_contract.md`" in detection
    assert "with `common_rules.md` only" in detection
    assert "skip language rules" in detection
