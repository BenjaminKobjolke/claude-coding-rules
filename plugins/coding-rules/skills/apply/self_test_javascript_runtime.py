"""Self-tests for runtime-aware migration of tailored JavaScript rules."""

import re
import tempfile
from pathlib import Path

from apply import run
from apply_constants import RULES_FILE
from file_io import load_json
from file_io import read_text
from file_io import save_json
from rule_blocks import read_coding_rules
from rule_blocks import split_orphan_tail
from rule_blocks import write_coding_rules


JAVASCRIPT_STACKS = (
    ("wordpress/BROWSER_JAVASCRIPT.md", "# WordPress Browser JavaScript Rules"),
    (
        "javascript/BROWSER_WIDGET.md",
        "# Browser Widget Rules (JavaScript, npm + webpack)",
    ),
    (
        "javascript/THUNDERBIRD_EXTENSION.md",
        "# JavaScript Rules (Thunderbird WebExtension)",
    ),
)


def self_test(shipped_root, shipped_versions):
    skill = read_text(shipped_root / "skills" / "apply" / "SKILL.md")
    section = re.search(
        r"(?ms)^### Tailored blocks and user-authored sections\n(.*?)(?=^## )",
        skill,
    )
    assert section, "apply skill is missing tailored block guidance"
    guidance = section.group(1)
    assert "Switch to the matching rules" in guidance
    assert re.search(r"Use the standard rules\*\*: default only when", guidance)
    for rule_path, _ in JAVASCRIPT_STACKS:
        assert rule_path in guidance, f"missing tailored migration for {rule_path}"

    for rule_path, title in JAVASCRIPT_STACKS:
        project = Path(tempfile.mkdtemp())
        (project / "tools").mkdir()
        setup_file = project / "tools" / "analyze_code.bat"
        setup_file.write_bytes(b"@echo off\r\nrem keep\r\n")
        common = read_text(shipped_root / "rules" / "COMMON_RULES.md")
        rules_file = project / RULES_FILE
        rules_file.write_text(
            "<!-- Managed by /coding-rules:apply — do not edit rule blocks by hand -->"
            "\n\n"
            + common
            + "\n# Version\n1\n\n# JavaScript Rules (Bun / Node, ESM)\n"
            "\n<!-- tailored -->\nproject-specific body\n\n"
            "# Project Notes\n\nkeep me\n",
            encoding="utf-8",
        )
        save_json(project / "coding-rules.json", {"rules": {
            "COMMON_RULES.md": shipped_versions["COMMON_RULES.md"],
            "JAVASCRIPT_RULES.md": 1,
        }})
        stale = run(project, shipped_root,
                    ["COMMON_RULES.md", "JAVASCRIPT_RULES.md"], "neither")
        assert any(item["status"] == "tailored-stale" for item in stale["rules"]), stale

        header, blocks = read_coding_rules(rules_file)
        js_block = next(block for block in blocks
                        if block["title"] == "# JavaScript Rules (Bun / Node, ESM)")
        source = read_text(shipped_root / "rules" / "JAVASCRIPT_RULES.md")
        _, orphan_tail = split_orphan_tail(js_block["text"], source)
        blocks.remove(js_block)
        if orphan_tail:
            blocks.append({"title": "# Project Notes", "text": orphan_tail.rstrip()})
        write_coding_rules(rules_file, header, blocks)
        manifest = load_json(project / "coding-rules.json", {})
        manifest["rules"].pop("JAVASCRIPT_RULES.md")
        save_json(project / "coding-rules.json", manifest)
        result = run(project, shipped_root, ["COMMON_RULES.md", rule_path], "neither")
        assert any(item["status"] == "updated" and item.get("rule") == rule_path
                   for item in result["rules"]), result
        final = read_text(rules_file)
        assert "# JavaScript Rules (Bun / Node, ESM)" not in final
        assert title in final and "keep me" in final
        final_manifest = load_json(project / "coding-rules.json", {})["rules"]
        assert rule_path in final_manifest
        assert "JAVASCRIPT_RULES.md" not in final_manifest
        assert setup_file.read_bytes() == b"@echo off\r\nrem keep\r\n"
