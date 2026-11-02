"""Self-tests for shipped language rules and optional rule variants."""

from apply import run
from file_io import load_json
from file_io import read_text
from pathlib import Path
import tempfile


def self_test():
    shipped_root = Path(__file__).resolve().parents[2]
    shipped_versions = load_json(shipped_root / "rules" / "versions.json", {})
    apply_skill = read_text(shipped_root / "skills" / "apply" / "SKILL.md")
    language_rules = (
        ("CPP_RULES.md", "# C++ Rules"),
        ("RUST_RULES.md", "# Rust Rules"),
        ("rust/SLINT.md", "# Slint Desktop UI Rules (Rust)"),
        (
            "implementation_flow_addons/mcp_server_rust.md",
            "# MCP Server over stdio (Rust, Optional Addon)",
        ),
    )

    delta_project = Path(tempfile.mkdtemp())
    first_delta = run(delta_project, shipped_root, ["COMMON_RULES.md"], "neither")
    assert any(
        item["rule"] == "COMMON_RULES.md" and item["status"] == "updated"
        for item in first_delta["rules"]
    ), first_delta

    for rule, title in language_rules:
        assert rule in shipped_versions, rule
        assert rule in apply_skill, rule
        report = run(
            delta_project, shipped_root, ["COMMON_RULES.md", rule], "neither"
        )
        statuses = {item["rule"]: item["status"] for item in report["rules"]}
        assert statuses[rule] == "updated", report
        assert statuses["COMMON_RULES.md"] == "unchanged", report
        manifest = load_json(delta_project / "coding-rules.json", {})
        assert rule in manifest["rules"], manifest
        assert title in read_text(delta_project / "CODING_RULES.md")

    assert "rust/SLINT.md" in read_text(
        shipped_root / "rules" / "DESIGN_RULES.md"
    )
    common_rules = read_text(shipped_root / "rules" / "COMMON_RULES.md")
    assert "## Upstream Forks" in common_rules
    assert "| Rust" in common_rules
