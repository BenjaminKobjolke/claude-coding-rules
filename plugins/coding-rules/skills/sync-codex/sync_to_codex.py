"""Install the coding-rules skills into Codex (~/.codex/skills/).

Codex has no plugin marketplace; skills are plain folders with a SKILL.md.
This copies the plugin's apply/enforce skills there, adapted for Codex:
- ${CLAUDE_PLUGIN_ROOT}/ paths become paths relative to the skill folder
- the rules/ folder is bundled next to the apply skill
- /coding-rules:apply slash-command references become skill-name references

Run:  python sync_to_codex.py        (re-run any time to update)
Test: python sync_to_codex.py --self-test
"""

import re
import shutil
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[2]  # .../plugins/coding-rules
SKILLS_DIR = Path.home() / ".codex" / "skills"

RELATIVE_NOTE = "Paths in this skill are relative to this skill's folder.\n\n"


def adapt(body):
    """Rewrite Claude-plugin specifics for a standalone Codex skill."""
    body = re.sub(r"<!-- claude-code-only:start -->.*?<!-- claude-code-only:end -->\n?",
                  "", body, flags=re.DOTALL)
    body = body.replace("${CLAUDE_PLUGIN_ROOT}/", "")
    body = body.replace("`/coding-rules:apply`", "the `coding-rules-apply` skill")
    body = body.replace("/coding-rules:apply", "the coding-rules-apply skill")
    return body


def split_frontmatter(text):
    """Return (frontmatter_lines, body). Frontmatter is the leading --- block."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return [], text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines[1:i], "".join(lines[i + 1:]).lstrip("\n")
    return [], text


def build_skill(src_md, codex_name, dest_dir, with_rules):
    front, body = split_frontmatter(src_md.read_text(encoding="utf-8"))
    description = ""
    for line in front:
        if line.partition(":")[0].strip() == "description":
            description = line.partition(":")[2].strip()
    body = adapt(body)
    if with_rules:
        body = RELATIVE_NOTE + body
    dest_dir.mkdir(parents=True, exist_ok=True)
    (dest_dir / "SKILL.md").write_text(
        f"---\nname: {codex_name}\ndescription: {description}\n---\n\n{body}",
        encoding="utf-8",
    )
    if with_rules:
        shutil.copytree(PLUGIN_ROOT / "rules", dest_dir / "rules", dirs_exist_ok=True)
    print(f"skill: {codex_name} -> {dest_dir}")


def sync():
    build_skill(PLUGIN_ROOT / "skills" / "apply" / "SKILL.md",
                "coding-rules-apply", SKILLS_DIR / "coding-rules-apply", with_rules=True)
    build_skill(PLUGIN_ROOT / "skills" / "enforce" / "SKILL.md",
                "coding-rules-enforce", SKILLS_DIR / "coding-rules-enforce", with_rules=False)
    print(f"\nDone. Target: {SKILLS_DIR}")


def self_test():
    out = adapt("rules at `${CLAUDE_PLUGIN_ROOT}/rules/COMMON_RULES.md`, run `/coding-rules:apply` first")
    assert "`rules/COMMON_RULES.md`" in out, out
    assert "the `coding-rules-apply` skill first" in out, out
    assert "CLAUDE_PLUGIN_ROOT" not in out
    assert adapt("run /coding-rules:apply now") == "run the coding-rules-apply skill now"
    front, body = split_frontmatter("---\ndescription: d\n---\n\nBody.\n")
    assert front == ["description: d\n"] and body == "Body.\n", (front, repr(body))
    stripped = adapt("keep A\n<!-- claude-code-only:start -->\nhook stuff\n"
                     "<!-- claude-code-only:end -->\nkeep B\n")
    assert stripped == "keep A\nkeep B\n", repr(stripped)
    print("self-test OK")


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        self_test()
    else:
        sync()
