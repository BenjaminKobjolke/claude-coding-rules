"""Self-tests for Python rule split behavior."""

from apply import run
from apply_constants import MANAGED_COMMENT
from apply_constants import RULES_FILE
from file_io import load_json
from file_io import read_text
from file_io import save_json
from file_io import write_text
from pathlib import Path
import tempfile


def self_test():
    # Python v6 inline sections move to optional blocks on the first v7 apply.
    for desktop in (True, False):
        split_plugin = Path(tempfile.mkdtemp())
        split_rules = split_plugin / "rules"
        (split_rules / "python").mkdir(parents=True)
        old_python = (
            "# Version\n6\n\n# Python Rules (uv)\n\n## GUI Framework\n\nold GUI\n\n"
            "# 8 Essential Additional Rules (must-have)\n\nold essentials\n"
        )
        new_python = (
            "# Version\n7\n\n# Python Rules (uv)\n\n"
            "# Essential Additional Rules (must-have)\n\nnew essentials\n"
        )
        (split_rules / "PYTHON_RULES.md").write_text(old_python, encoding="utf-8")
        save_json(split_rules / "versions.json", {"pointer": 1, "PYTHON_RULES.md": 6})
        split_project = Path(tempfile.mkdtemp())
        if desktop:
            (split_project / "pyproject.toml").write_text(
                'dependencies = ["PySide6>=6"]\n', encoding="utf-8"
            )
        run(split_project, split_plugin, ["PYTHON_RULES.md"], "neither")
        with (split_project / RULES_FILE).open("a", encoding="utf-8") as f:
            f.write("\n# Project Notes\n\nkeep this\n")
        (split_rules / "PYTHON_RULES.md").write_text(new_python, encoding="utf-8")
        (split_rules / "python" / "GUI.md").write_text(
            "# Version\n1\n\n# Python Desktop GUI (PySide6)\n\n"
            "## GUI Framework\n\nGUI rules\n", encoding="utf-8"
        )
        (split_rules / "python" / "DATABASE.md").write_text(
            "# Version\n1\n\n# Python Database Access (SQLAlchemy)\n\nDB rules\n",
            encoding="utf-8",
        )
        save_json(split_rules / "versions.json", {"pointer": 1, "PYTHON_RULES.md": 7,
                  "python/GUI.md": 1, "python/DATABASE.md": 1})
        split_report = run(split_project, split_plugin, ["PYTHON_RULES.md"], "keep")
        assert split_report["split_kept"] == (
            ["python/GUI.md"] if desktop else []
        ), split_report
        result = read_text(split_project / RULES_FILE)
        assert ("GUI rules" in result) == desktop and "DB rules" not in result, result
        assert (
            "old GUI" not in result
            and result.count("# Essential Additional Rules") == 1
        ), result
        assert "# Project Notes" in result and "keep this" in result, result
        assert load_json(split_project / "coding-rules.json", {})["rules"] == (
            {"PYTHON_RULES.md": 7, "python/GUI.md": 1}
            if desktop else {"PYTHON_RULES.md": 7}
        )
        again = run(split_project, split_plugin, ["PYTHON_RULES.md"], "keep")
        assert again["split_kept"] == [] and all(
            x["status"] == "unchanged" for x in again["rules"]
        ), again
        assert read_text(split_project / RULES_FILE) == result

    fresh = Path(tempfile.mkdtemp())
    (fresh / "pyproject.toml").write_text(
        'dependencies = ["pyside6"]\n', encoding="utf-8"
    )
    fresh_report = run(fresh, split_plugin, ["PYTHON_RULES.md"], "neither")
    assert fresh_report["split_kept"] == [], fresh_report

    tailored_project = Path(tempfile.mkdtemp())
    write_text(
        tailored_project / RULES_FILE,
        MANAGED_COMMENT + "\n\n"
        + old_python.replace(
            "# Python Rules (uv)\n", "# Python Rules (uv)\n<!-- tailored -->\n"
        ),
    )
    (tailored_project / "pyproject.toml").write_text(
        'dependencies = ["pyside6"]\n', encoding="utf-8"
    )
    save_json(tailored_project / "coding-rules.json", {"rules": {"PYTHON_RULES.md": 6}})
    tailored_report = run(
        tailored_project, split_plugin, ["PYTHON_RULES.md"], "neither"
    )
    assert tailored_report["split_kept"] == []
    assert tailored_report["rules"][0]["status"] == "tailored-stale"
    assert read_text(tailored_project / RULES_FILE).endswith(old_python.replace(
        "# Python Rules (uv)\n", "# Python Rules (uv)\n<!-- tailored -->\n"))

    legacy_project = Path(tempfile.mkdtemp())
    (legacy_project / "pyproject.toml").write_text(
        'dependencies = ["pyside6"]\n', encoding="utf-8"
    )
    write_text(
        legacy_project / "CLAUDE.md", old_python + "\n# Project Notes\n\nkeep me\n"
    )
    legacy_report = run(legacy_project, split_plugin, ["PYTHON_RULES.md"], "neither")
    assert legacy_report["split_kept"] == ["python/GUI.md"], legacy_report
    assert "old GUI" not in read_text(legacy_project / "CLAUDE.md")
    assert "# Project Notes\n\nkeep me" in read_text(legacy_project / "CLAUDE.md")
    assert "GUI rules" in read_text(legacy_project / RULES_FILE)

    tailored_legacy = Path(tempfile.mkdtemp())
    tailored_text = old_python.replace(
        "# Python Rules (uv)\n", "# Python Rules (uv)\n<!-- tailored -->\n"
    )
    write_text(tailored_legacy / "CLAUDE.md", tailored_text)
    tailored_legacy_report = run(
        tailored_legacy, split_plugin, ["PYTHON_RULES.md"], "neither"
    )
    assert tailored_legacy_report["split_kept"] == []
    assert any(
        "Tailored legacy block" in d["detail"]
        for d in tailored_legacy_report["needs_user_decision"]
    )
    assert tailored_text in read_text(tailored_legacy / "CLAUDE.md")

