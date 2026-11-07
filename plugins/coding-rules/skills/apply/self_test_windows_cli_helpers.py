"""Self-tests for the Windows command-line helper collection rule."""

import re

from file_io import load_json
from file_io import read_text


def self_test(shipped_root, shipped_versions):
    rule_path = "project_type/WINDOWS_CLI_HELPERS.md"
    assert shipped_versions.get(rule_path) == 1
    rule = read_text(shipped_root / "rules" / rule_path)
    assert rule.startswith("# Version\n1\n")
    assert all(term in rule.lower() for term in (
        "%~dp0", "setlocal", "exit /b", "-encoding utf8", "$lastexitcode",
        "vendored", ".graphifyignore",
    ))

    versions = load_json(shipped_root / "rules" / "versions.json", {})
    assert versions.get(rule_path) == 1

    project_types = read_text(shipped_root / "rules" / "PROJECT_TYPES.md")
    assert re.search(r"(?m)^## Windows Command-Line Helpers(?:\s|$)", project_types)

    apply_skill = read_text(shipped_root / "skills" / "apply" / "SKILL.md")
    detection = re.search(
        r"(?m)^- Windows command-line helper collection:(.*(?:\n  .*)*)",
        apply_skill,
    )
    assert detection, "apply skill is missing the Windows helper detection section"
    detection = detection.group(0).lower()
    assert all(term in detection for term in (
        "project_type/windows_cli_helpers.md", "common_rules.md",
        "autohotkey_rules.md", "pyproject.toml", "python_rules.md",
    ))
