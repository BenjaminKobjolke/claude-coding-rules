"""Self-tests for the shipped server-rendered frontend rule."""

import re

from file_io import read_text


def self_test(shipped_root, shipped_versions):
    server_rendered_path = "project_type/SERVER_RENDERED_FRONTEND.md"
    assert shipped_versions.get(server_rendered_path) == 3
    server_rendered = read_text(shipped_root / "rules" / server_rendered_path)
    assert all(term in server_rendered for term in (
        "server-side routing", "route names", "Twig", "template rendering",
        "application configuration", "static assets", "media assets",
        "deployment boundaries", "local database",
    ))
    assert "only when the application consumes a separate API" in server_rendered
    assert "Frontend Only — Never Change the API From Here (BINDING)" not in (
        server_rendered
    )

    project_types = read_text(shipped_root / "rules" / "PROJECT_TYPES.md")
    section = re.search(
        r"(?ms)^## Server-Rendered PHP Frontend.*?(?=^## |\Z)",
        project_types,
    )
    assert section is not None
    section_text = section.group()
    assert "not REST APIs or frontend SPAs" in section_text
    assert "PHP web applications that route requests and render HTML on the server" in (
        section_text
    )
    assert "`php/APP.md`" in section_text
    assert "Add `DESIGN_RULES.md` because the project has a UI" in section_text
    assert "`SCSS_RULES.md`" in section_text
    assert "`TYPESCRIPT_RULES.md`" in section_text

    apply_skill = read_text(shipped_root / "skills" / "apply" / "SKILL.md")
    assert "server-rendered php/twig web apps" in apply_skill.lower()
    assert "do not select `project_type/rest_api.md`" in apply_skill.lower()
    assert "do not select `project_type/frontend.md`" in apply_skill.lower()
    assert "project_type/server_rendered_frontend.md" in apply_skill.lower()
