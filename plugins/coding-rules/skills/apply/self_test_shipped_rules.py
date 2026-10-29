"""Self-tests for shipped rule splits and content."""

from apply import check_versions
from apply import run
from apply_constants import RULES_FILE
from apply_constants import SPLITS
from file_io import load_json
from file_io import read_text
from file_io import save_json
from pathlib import Path
from rule_migration import project_uses
from self_test_rest_api_split import self_test as test_rest_api_split
import self_test_server_rendered_frontend as server_rendered_test
import re
import tempfile


def self_test():
    # Flutter v13 app-only rules move into a supplement on the v14 apply.
    # A demo application under example/ must not classify the package as an app.
    for app in (True, False):
        flutter_plugin = Path(tempfile.mkdtemp())
        flutter_rules = flutter_plugin / "rules"
        (flutter_rules / "flutter").mkdir(parents=True)
        old_flutter = (
            "# Version\n13\n\n# Flutter Rules (FVM + Mobile)\n\n"
            "general Flutter rules\n\n## Localization\n\nold i18n rules\n")
        new_flutter = (
            "# Version\n14\n\n# Flutter Rules (FVM + Mobile)\n\n"
            "general Flutter rules\n")
        (flutter_rules / "FLUTTER_RULES.md").write_text(old_flutter, encoding="utf-8")
        save_json(
            flutter_rules / "versions.json",
            {"pointer": 1, "FLUTTER_RULES.md": 13},
        )

        flutter_project = Path(tempfile.mkdtemp())
        if app:
            (flutter_project / "lib").mkdir()
            (flutter_project / "lib" / "main.dart").write_text(
                "void main() {}\n", encoding="utf-8"
            )
        else:
            (flutter_project / "pubspec.yaml").write_text(
                "name: sample_plugin\n", encoding="utf-8"
            )
            (flutter_project / "example" / "lib").mkdir(parents=True)
            (flutter_project / "example" / "lib" / "main.dart").write_text(
                "void main() {}\n", encoding="utf-8")
        run(flutter_project, flutter_plugin, ["FLUTTER_RULES.md"], "neither")

        (flutter_rules / "FLUTTER_RULES.md").write_text(new_flutter, encoding="utf-8")
        (flutter_rules / "flutter" / "APP.md").write_text(
            "# Version\n1\n\n# Flutter App Rules\n\nnew i18n rules\n", encoding="utf-8")
        save_json(
            flutter_rules / "versions.json",
            {"pointer": 1, "FLUTTER_RULES.md": 14, "flutter/APP.md": 1},
        )

        flutter_report = run(
            flutter_project, flutter_plugin, ["FLUTTER_RULES.md"], "keep"
        )
        assert flutter_report["split_kept"] == (
            ["flutter/APP.md"] if app else []
        ), flutter_report
        result = read_text(flutter_project / RULES_FILE)
        assert result.count("new i18n rules") == (1 if app else 0), result
        assert (
            "old i18n rules" not in result and "general Flutter rules" in result
        ), result
        expected_rules = ({"FLUTTER_RULES.md": 14, "flutter/APP.md": 1} if app
                          else {"FLUTTER_RULES.md": 14})
        assert (
            load_json(flutter_project / "coding-rules.json", {})["rules"]
            == expected_rules
        )
        again = run(flutter_project, flutter_plugin, ["FLUTTER_RULES.md"], "keep")
        assert again["split_kept"] == [] and all(
            item["status"] == "unchanged" for item in again["rules"]), again
        assert read_text(flutter_project / RULES_FILE) == result

    # C# v1 rules move the WinForms sections to an optional block on the v2 apply.
    for desktop in (True, False):
        csharp_plugin = Path(tempfile.mkdtemp())
        csharp_rules = csharp_plugin / "rules"
        (csharp_rules / "csharp").mkdir(parents=True)
        old_csharp = (
            "# Version\n1\n\n# C# Rules (.NET Framework / Windows Forms)\n\n"
            "general rules\n\n## Tray Icon Setup\n\nold tray rules\n"
        )
        new_csharp = "# Version\n2\n\n# C# Rules (.NET)\n\ngeneral rules\n"
        (csharp_rules / "CSHARP_RULES.md").write_text(old_csharp, encoding="utf-8")
        save_json(csharp_rules / "versions.json", {"pointer": 1, "CSHARP_RULES.md": 1})

        csharp_project = Path(tempfile.mkdtemp())
        app_dir = csharp_project / "MyApp"
        app_dir.mkdir()
        project_text = (
            "<Project><ItemGroup><Reference Include=\"System.Windows.Forms\" />"
            "</ItemGroup></Project>" if desktop else
            "<Project><PropertyGroup><OutputType>Exe</OutputType>"
            "</PropertyGroup></Project>"
        )
        (app_dir / "MyApp.csproj").write_text(project_text, encoding="utf-8")
        run(csharp_project, csharp_plugin, ["CSHARP_RULES.md"], "neither")

        (csharp_rules / "CSHARP_RULES.md").write_text(new_csharp, encoding="utf-8")
        (csharp_rules / "csharp" / "WINFORMS.md").write_text(
            "# Version\n1\n\n# C# Windows Forms Desktop Rules\n\nnew tray rules\n",
            encoding="utf-8",
        )
        save_json(
            csharp_rules / "versions.json",
            {"pointer": 1, "CSHARP_RULES.md": 2, "csharp/WINFORMS.md": 1},
        )

        split_report = run(csharp_project, csharp_plugin, ["CSHARP_RULES.md"], "keep")
        assert split_report["split_kept"] == (
            ["csharp/WINFORMS.md"] if desktop else []
        ), split_report
        result = read_text(csharp_project / RULES_FILE)
        assert result.count("# C# Rules") == 1 and "# C# Rules (.NET)" in result, result
        assert (
            "old tray rules" not in result and ("new tray rules" in result) == desktop
        ), result
        assert load_json(csharp_project / "coding-rules.json", {})["rules"] == (
            {"CSHARP_RULES.md": 2, "csharp/WINFORMS.md": 1}
            if desktop else {"CSHARP_RULES.md": 2}
        )
        result_before_second_run = result
        again = run(csharp_project, csharp_plugin, ["CSHARP_RULES.md"], "keep")
        assert again["split_kept"] == [] and all(
            item["status"] == "unchanged" for item in again["rules"]), again
        assert read_text(csharp_project / RULES_FILE) == result_before_second_run

    marker_project = Path(tempfile.mkdtemp())
    (marker_project / "MyApp").mkdir()
    (marker_project / "MyApp" / "MyApp.csproj").write_text(
        "<Project><PropertyGroup><UseWindowsForms>true</UseWindowsForms>"
        "</PropertyGroup></Project>",
        encoding="utf-8",
    )
    assert project_uses(marker_project, ("system.windows.forms", "usewindowsforms"))
    (marker_project / "MyApp" / "MyApp.csproj").write_text(
        "<Project><ItemGroup><Reference Include=\"System.Windows.Forms\" />"
        "</ItemGroup></Project>",
        encoding="utf-8",
    )
    assert project_uses(marker_project, ("system.windows.forms", "usewindowsforms"))
    assert not project_uses(Path(tempfile.mkdtemp()),
                            ("system.windows.forms", "usewindowsforms"))

    marker_project = Path(tempfile.mkdtemp())
    (marker_project / "pyproject.toml").write_text(
        'dependencies = ["PySide6>=6"]\n', encoding="utf-8"
    )
    assert project_uses(marker_project, ("pyside6",))
    assert not project_uses(marker_project, ("sqlalchemy",))
    (marker_project / "installer").mkdir()
    assert project_uses(marker_project, ("installer/",))
    assert not project_uses(Path(tempfile.mkdtemp()), ("installer/", "pyside6"))

    setup_plugin = Path(tempfile.mkdtemp())
    setup_dir = setup_plugin / "rules" / "example_setup_files"
    setup_dir.mkdir(parents=True)
    (setup_dir / "SETUP.md").write_text("# Version\n1\n\n# Setup\n", encoding="utf-8")
    save_json(
        setup_plugin / "rules" / "versions.json",
        {"example_setup_files/SETUP.md": 1},
    )
    check_versions(setup_plugin)
    for indexed in ({}, {"example_setup_files/SETUP.md": 2}):
        save_json(setup_plugin / "rules" / "versions.json", indexed)
        try:
            check_versions(setup_plugin)
            raise AssertionError("setup version mismatch was accepted")
        except SystemExit as exc:
            assert exc.code == 1

    shipped_root = Path(__file__).resolve().parents[2]
    shipped_versions = load_json(shipped_root / "rules" / "versions.json", {})
    assert "CPP_RULES.md" in shipped_versions
    assert "CPP_RULES.md" in read_text(shipped_root / "skills" / "apply" / "SKILL.md")

    delta_project = Path(tempfile.mkdtemp())
    first_delta = run(delta_project, shipped_root, ["COMMON_RULES.md"], "neither")
    assert any(item["rule"] == "COMMON_RULES.md" and item["status"] == "updated"
               for item in first_delta["rules"]), first_delta
    second_delta = run(
        delta_project, shipped_root, ["COMMON_RULES.md", "CPP_RULES.md"], "neither"
    )
    delta_statuses = {item["rule"]: item["status"] for item in second_delta["rules"]}
    assert delta_statuses["CPP_RULES.md"] == "updated", second_delta
    assert delta_statuses["COMMON_RULES.md"] == "unchanged", second_delta
    delta_manifest = load_json(delta_project / "coding-rules.json", {})
    assert "CPP_RULES.md" in delta_manifest["rules"], delta_manifest
    assert "# C++ Rules" in read_text(delta_project / "CODING_RULES.md")

    runner_flags = {
        "flutter_setup_files/tools/run_tests.bat": "flutter test --reporter expanded",
        "kotlin_setup_files/tools/run_tests.bat": "testDebugUnitTest",
        "kotlin_setup_files/tools/run_analysis.bat": "lintKotlin",
        "python_setup_files/tools/run_tests.bat": "pytest tests/ -v",
        "python_setup_files/tools/run_integration_tests.bat": (
            "pytest tests/integration -v"
        ),
        "php_setup_files/tools/tests.bat": "--debug",
        "php_setup_files/tools/tests-php.bat": "--debug",
        "wordpress_setup_files/tools/run_tests.bat": "--debug",
    }
    for rel, flag in runner_flags.items():
        runner = read_text(shipped_root / "rules" / rel)
        active_lines = [line.strip().lower() for line in runner.splitlines()
                        if flag.lower() in line.lower()
                        and not line.lstrip().lower().startswith(
                            ("rem", "::", "echo")
                        )]
        assert active_lines, f"{rel} is missing {flag}"
        assert not any(re.search(r"(?<![2])>(?!&)", line) for line in active_lines), \
            f"{rel} redirects runner output"
        if rel in (
            "php_setup_files/tools/tests-php.bat",
            "wordpress_setup_files/tools/run_tests.bat",
        ):
            plain_phpunit = [line.strip().lower() for line in runner.splitlines()
                             if "phpunit" in line.lower() and "--colors" in line.lower()
                             and "--debug" not in line.lower()
                             and not line.lstrip().lower().startswith(
                                 ("rem", "::", "echo")
                             )]
            assert not plain_phpunit, (
                f"{rel} runs PHPUnit without --debug: {plain_phpunit}"
            )
    for rel in SPLITS["PYTHON_RULES.md"][1]:
        assert rel in shipped_versions and (shipped_root / "rules" / rel).exists(), rel
    for rel in SPLITS["FLUTTER_RULES.md"][1]:
        assert rel in shipped_versions and (shipped_root / "rules" / rel).exists(), rel
    flutter_base = read_text(shipped_root / "rules" / "FLUTTER_RULES.md")
    assert all(term not in flutter_base for term in (
        "## Localization", "## 7) State Management (Cubit)",
        "## 8) HTTP Communication (Dio)", "## App Icons",
        "## 6) Required Batch Files", "install.bat"))
    assert all(term in flutter_base for term in (
        "## Mixins", "## Pin Android Dependencies", "## 5) Tests are mandatory",
        "--reporter expanded"))
    lean = read_text(shipped_root / "rules" / "PYTHON_RULES.md")
    assert all(heading not in lean for heading in (
        "## Template Engine", "## GUI Framework", "## Localization",
        "## Jinja2 Integration", "## Release Workflow",
        "## Windows Installer (NSIS)",
        "## 6) Database access uses SQLAlchemy ORM",
    ))
    assert all(term in lean for term in (
        "## CLI Menus", "## Project Setup Scripts", "MagicMock",
        "## Structured Logging", "## Self-Describing Classes",
    ))
    graph = read_text(
        shipped_root / "rules" / "implementation_flow_addons" / "graphify.md"
    )
    assert "One-time setup" not in graph and "Rules to paste" not in graph
    assert "## One-time setup" in read_text(
        shipped_root / "rules" / "graphify_setup_files" / "SETUP.md"
    )

    pin_terms = ("releaseRuntimeClasspath", "resolutionStrategy.force")
    for pinned in (
        shipped_root / "rules" / "FLUTTER_RULES.md",
        shipped_root / "skills" / "enforce" / "SKILL.md",
    ):
        assert all(term in read_text(pinned) for term in pin_terms), pinned

    python_web_service_path = "project_type/PYTHON_WEB_SERVICE.md"
    assert shipped_versions.get(python_web_service_path) == 2
    project_types = read_text(shipped_root / "rules" / "PROJECT_TYPES.md")
    assert (
        "## Python Web Service — `project_type/PYTHON_WEB_SERVICE.md`"
        in project_types
    )
    assert "Pair with `PYTHON_RULES.md`" in project_types
    assert "`DESIGN_RULES.md` applies" in project_types

    python_web_service = read_text(shipped_root / "rules" / python_web_service_path)
    assert all(term in python_web_service for term in (
        "FastAPI", "ASGI", "Route organization", "Pydantic",
        "response model", "Error handling", "environment", "secrets",
        "authentication", "unauthenticated", "static", "command-line",
        "pytest", "CLI",
    ))
    assert "does not require a separate frontend framework" in python_web_service
    assert "or frontend build tool" in python_web_service
    assert all(term not in python_web_service for term in (
        "Cycle ORM", "AbstractController", "ApiTestCase", "Hoppscotch",
        "PHP_RULES.md", "must use Vite", "must use npm",
    ))

    test_rest_api_split()

    server_rendered_test.self_test(shipped_root, shipped_versions)
