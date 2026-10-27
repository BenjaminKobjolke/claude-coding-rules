"""Filter applied coding-rule blocks into generated per-step rule files."""

import re
from typing import TypedDict

STEP_FILES = {
    "plan": "CODING_RULES_PLAN.md",
    "review": "CODING_RULES_REVIEW.md",
    "code": "CODING_RULES_CODE.md",
}
STEP_MARKER_PREFIX = "<!-- steps:"
STEPS_RE = re.compile(r"^<!-- steps: ([a-z]+(?:, *[a-z]+)*) -->$")
ATX_HEADING_RE = re.compile(r"^(#{1,6})\s+.+$")


class RuleBlock(TypedDict):
    title: str | None
    text: str


def _parse_step_marker(marker: str) -> set[str]:
    """Parse a step marker and reject malformed or unknown steps."""
    match = STEPS_RE.fullmatch(marker.strip())
    if match is None:
        raise ValueError(f"invalid step marker: {marker.strip()}")
    steps = {part.strip() for part in match.group(1).split(",")}
    unknown = steps - STEP_FILES.keys()
    if unknown:
        raise ValueError(f"unknown step marker token(s): {', '.join(sorted(unknown))}")
    return steps


def _step_marker(
    lines: list[str], heading_index: int
) -> tuple[set[str] | None, int | None]:
    """Return a heading's marker and its line index, skipping blank lines."""
    marker_index = heading_index + 1
    while marker_index < len(lines) and not lines[marker_index].strip():
        marker_index += 1
    if marker_index == len(lines):
        return None, None
    marker = lines[marker_index].strip()
    if not marker.startswith(STEP_MARKER_PREFIX):
        return None, None
    return _parse_step_marker(marker), marker_index


def filter_block(text: str, step: str) -> str:
    """Keep text visible to one run type, honoring heading-scoped markers."""
    if step not in STEP_FILES:
        raise ValueError(f"unknown step: {step}")
    lines = text.splitlines(keepends=True)
    output = []
    skipped_level = None
    in_fence = False
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if stripped.startswith("```"):
            if skipped_level is None:
                output.append(line)
            in_fence = not in_fence
            index += 1
            continue
        heading = None if in_fence else ATX_HEADING_RE.match(stripped)
        if skipped_level is not None:
            if heading and len(heading.group(1)) <= skipped_level:
                skipped_level = None
            else:
                index += 1
                continue
        if heading:
            level = len(heading.group(1))
            steps, marker_index = _step_marker(lines, index)
            if steps is not None:
                if step not in steps:
                    skipped_level = level
                    index += 1
                    continue
                output.extend(lines[index:marker_index + 1])
                index = marker_index + 1
                continue
        output.append(line)
        index += 1

    filtered = "".join(output)
    remainder = [line.strip() for line in filtered.splitlines()
                 if line.strip() and line.strip() != "# Version"]
    if len(remainder) <= 1 and (not remainder or remainder[0].isdigit()):
        return ""
    return filtered


def step_blocks(blocks: list[RuleBlock]) -> dict[str, list[RuleBlock]]:
    """Return filtered non-empty rule blocks keyed by generated filename."""
    result = {}
    for step, filename in STEP_FILES.items():
        filtered = []
        for block in blocks:
            text = filter_block(block["text"], step)
            if text:
                filtered.append({"title": block["title"], "text": text})
        result[filename] = filtered
    return result


def step_header(header: str, step: str) -> str:
    """Add provenance to the complete header used for a step-specific file."""
    if step not in STEP_FILES:
        raise ValueError(f"unknown step: {step}")
    note = (f"<!-- Step file for {step} runs, generated from CODING_RULES.md — "
            "CODING_RULES.md stays the complete rule set -->")
    return header.rstrip("\n") + ("\n" if header else "") + note + "\n"


def check_markers(text: str) -> None:
    """Validate all non-fenced step markers in a shipped rule file."""
    lines = text.splitlines()
    in_fence = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or not stripped.startswith(STEP_MARKER_PREFIX):
            continue
        _parse_step_marker(stripped)


def self_test() -> None:
    block = """# Version
1

# All steps
common

## Code recipe
<!-- steps: code -->
recipe

## Keep planning
planning

### Review detail
<!-- steps: review -->
review detail

## Comment examples
# ordinary comment
```md
<!-- steps: bogus -->
```
"""
    assert "common" in filter_block(block, "plan")
    assert "recipe" not in filter_block(block, "plan")
    assert "recipe" not in filter_block(block, "review")
    assert "recipe" in filter_block(block, "code")
    assert "planning" in filter_block(block, "code")
    assert "review detail" not in filter_block(block, "code")
    assert "planning" in filter_block(block, "review")
    assert "# ordinary comment" in filter_block(block, "plan")
    assert "<!-- steps: bogus -->" in filter_block(block, "plan")
    check_markers(block)

    whole = "# Version\n1\n\n# Hidden\n<!-- steps: code -->\nsecret\n"
    assert filter_block(whole, "plan") == ""
    assert (
        step_blocks([{"title": "# Hidden", "text": whole}])["CODING_RULES_PLAN.md"]
        == []
    )
    try:
        check_markers("# X\n<!-- steps: code, typo -->\n")
    except ValueError:
        pass
    else:
        raise AssertionError("unknown step token must fail")
    try:
        check_markers("# X\n<!-- steps: code\n")
    except ValueError:
        pass
    else:
        raise AssertionError("malformed marker must fail")
