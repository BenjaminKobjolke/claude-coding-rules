"""Self-tests for the shipped landing-page content repo rule."""

import re

from file_io import read_text


def self_test(shipped_root, shipped_versions):
    rule_path = "project_type/LANDING_PAGE_CONTENT.md"
    assert shipped_versions.get(rule_path) == 1
    rule = read_text(shipped_root / "rules" / rule_path)
    assert all(term in rule for term in (
        "content repo", "sections", "PARTIALS.md", "optional param", "en.json",
        "de.json", "remove the key", "{site}/public/", "clear", "scssphp",
        "config.php", ".deployignore", "page render",
    ))
    assert all(term not in rule for term in (
        "Cycle ORM", "phpstan.neon", "AbstractController", "ApiTestCase",
    ))

    project_types = read_text(shipped_root / "rules" / "PROJECT_TYPES.md")
    section = re.search(
        r"(?ms)^## Landing Page Content.*?(?=^## |\Z)", project_types,
    )
    assert section is not None
    section_text = section.group()
    assert all(term in section_text for term in (
        "`COMMON_RULES.md`", "`DESIGN_RULES.md`", "`SCSS_RULES.md`",
        "Skip `PHP_RULES.md` and `php/APP.md`",
    ))

    apply_skill = read_text(shipped_root / "skills" / "apply" / "SKILL.md")
    assert all(term in apply_skill.lower() for term in (
        "project_type/landing_page_content.md", "templates/index.twig",
        "composer.json",
    ))
