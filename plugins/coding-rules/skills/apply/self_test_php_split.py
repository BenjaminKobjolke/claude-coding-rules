"""Self-tests for PHP web-app rule splitting and Composer package detection."""

from apply import check_versions
from apply import run
from apply_constants import RULES_FILE
from apply_constants import SPLITS
from file_io import load_json
from file_io import read_text
from file_io import save_json
from pathlib import Path
from rule_migration import project_uses
import tempfile


def self_test():
    # PHP v4 web-app rules move into an optional block on the v5 apply.
    for app in (True, False):
        split_plugin = Path(tempfile.mkdtemp())
        split_rules = split_plugin / "rules"
        (split_rules / "php").mkdir(parents=True)
        old_php = (
            "# Version\n4\n\n# PHP Rules\n\ngeneral PHP rules\n\n"
            "## Template Engine\n\nold twig rules\n"
        )
        new_php = "# Version\n5\n\n# PHP Rules\n\ngeneral PHP rules\n"
        (split_rules / "PHP_RULES.md").write_text(old_php, encoding="utf-8")
        save_json(
            split_rules / "versions.json",
            {"pointer": 1, "PHP_RULES.md": 4},
        )

        project = Path(tempfile.mkdtemp())
        composer = (
            {"require": {"slim/slim": "^4"}}
            if app else
            {"type": "library", "require": {"guzzlehttp/guzzle": "^7"}}
        )
        save_json(project / "composer.json", composer)
        run(project, split_plugin, ["PHP_RULES.md"], "neither")

        (split_rules / "PHP_RULES.md").write_text(new_php, encoding="utf-8")
        (split_rules / "php" / "APP.md").write_text(
            "# Version\n1\n\n# PHP Web App Rules\n\nnew twig rules\n",
            encoding="utf-8",
        )
        save_json(
            split_rules / "versions.json",
            {"pointer": 1, "PHP_RULES.md": 5, "php/APP.md": 1},
        )

        report = run(project, split_plugin, ["PHP_RULES.md"], "keep")
        assert report["split_kept"] == (["php/APP.md"] if app else []), report
        result = read_text(project / RULES_FILE)
        assert ("new twig rules" in result) == app, result
        assert "old twig rules" not in result and "general PHP rules" in result, result
        expected_rules = (
            {"PHP_RULES.md": 5, "php/APP.md": 1}
            if app else {"PHP_RULES.md": 5}
        )
        assert load_json(project / "coding-rules.json", {})["rules"] == expected_rules
        again = run(project, split_plugin, ["PHP_RULES.md"], "keep")
        assert again["split_kept"] == [] and all(
            item["status"] == "unchanged" for item in again["rules"]
        ), again
        assert read_text(project / RULES_FILE) == result

    marker_project = Path(tempfile.mkdtemp())
    (marker_project / "composer.json").write_text(
        '{"require":{"slim/slim":"^4"}}', encoding="utf-8"
    )
    assert project_uses(marker_project, SPLITS["PHP_RULES.md"][1]["php/APP.md"])
    assert not project_uses(Path(tempfile.mkdtemp()), ("public/index.php",))
    (marker_project / "public").mkdir()
    (marker_project / "public" / "index.php").write_text("<?php", encoding="utf-8")
    assert project_uses(marker_project, ("public/index.php",))

    root = Path(__file__).resolve().parents[2]
    versions = load_json(root / "rules" / "versions.json", {})
    for rel in (*SPLITS["PHP_RULES.md"][1],):
        path = rel
        assert path in versions and (root / "rules" / path).exists(), path
    library = "project_type/PHP_LIBRARY.md"
    assert library in versions and (root / "rules" / library).exists(), library

    base = read_text(root / "rules" / "PHP_RULES.md")
    assert all(term not in base for term in (
        "## Web Server & Asset Paths", "## Template Engine", "## Localization",
        "## Database: Cycle ORM", "### Required Batch Files", "config/database.php",
    )), base
    assert all(term in base for term in (
        "## Code Quality", "## Logging", "## Self-Describing Classes",
        "## Optional rule files",
    )), base
    app_rules = read_text(root / "rules" / "php/APP.md")
    assert "## Template Engine" in app_rules and "### Required Batch Files" in app_rules
    library_rules = read_text(root / "rules" / library)
    assert all(term in library_rules for term in (
        "--debug", "exit /b %TESTRESULT%", "MockHandler",
    )), library_rules
    assert not any(
        line.strip().lower() == "pause" for line in library_rules.splitlines()
    )
    check_versions(root)
