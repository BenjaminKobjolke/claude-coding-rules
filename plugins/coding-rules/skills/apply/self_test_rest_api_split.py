"""Self-test for REST API JWT split migration."""

from apply import run
from apply_constants import RULES_FILE
from file_io import load_json
from file_io import read_text
from file_io import save_json
from pathlib import Path
from rule_migration import project_uses
import tempfile


def self_test():
    for has_jwt in (True, False):
        plugin_root = Path(tempfile.mkdtemp())
        rules_dir = plugin_root / "rules"
        (rules_dir / "project_type" / "rest_api").mkdir(parents=True)
        old_rest_api = (
            "# Version\n8\n\n# PHP REST API Rules\n\n"
            "shared API rules\n\n## JWT Authentication Middleware\n\n"
            "JWT migration marker\n"
        )
        rest_api = rules_dir / "project_type" / "REST_API.md"
        rest_api.write_text(old_rest_api, encoding="utf-8")
        save_json(
            rules_dir / "versions.json",
            {"project_type/REST_API.md": 8},
        )

        project = Path(tempfile.mkdtemp())
        composer = project / "composer.json"
        composer.write_text(
            '{"require":{"firebase/php-jwt":"^6"}}' if has_jwt else
            '{"require":{"slim/slim":"^4"}}',
            encoding="utf-8",
        )
        run(project, plugin_root, ["project_type/REST_API.md"], "neither")

        rest_api.write_text(
            "# Version\n9\n\n# PHP REST API Rules\n\n"
            "shared API rules\n",
            encoding="utf-8",
        )
        jwt_auth = rules_dir / "project_type" / "rest_api" / "JWT_AUTH.md"
        jwt_auth.write_text(
            "# Version\n1\n\n# PHP REST API — JWT Authentication\n\n"
            "JWT migration marker\n",
            encoding="utf-8",
        )
        save_json(
            rules_dir / "versions.json",
            {
                "project_type/REST_API.md": 9,
                "project_type/rest_api/JWT_AUTH.md": 1,
            },
        )

        assert project_uses(project, ("firebase/php-jwt",)) == has_jwt
        report = run(project, plugin_root, ["project_type/REST_API.md"], "keep")
        expected_kept = (
            ["project_type/rest_api/JWT_AUTH.md"] if has_jwt else []
        )
        assert report["split_kept"] == expected_kept, report
        result = read_text(project / RULES_FILE)
        assert result.count("JWT migration marker") == (1 if has_jwt else 0), result
        expected_manifest = {"project_type/REST_API.md": 9}
        if has_jwt:
            expected_manifest["project_type/rest_api/JWT_AUTH.md"] = 1
        assert (
            load_json(project / "coding-rules.json", {})["rules"]
            == expected_manifest
        )

        again = run(project, plugin_root, ["project_type/REST_API.md"], "keep")
        assert again["split_kept"] == [] and all(
            item["status"] == "unchanged" for item in again["rules"]
        ), again
        assert read_text(project / RULES_FILE) == result
