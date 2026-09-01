"""Claude Code reminder hook for CODING_RULES.md. Serves two events:

- PostToolUse (matcher: ExitPlanMode) — plan accepted: always remind.
- PreToolUse (matcher: Edit|Write|MultiEdit) — first code edit of a session:
  remind once, tracked by a per-session marker file in the temp dir.

Plain stdout is NOT shown to Claude for either event; only the
hookSpecificOutput.additionalContext JSON field is injected.

Registered globally by the coding-rules plugin (hooks/hooks.json), so it runs in
every project and gates itself: silent unless the project has a CODING_RULES.md,
silent when <project>/.claude/hooks/coding-rules-reminder.off exists.
"""
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path

MARKER_PREFIX = "coding-rules-reminded-"
MARKER_MAX_AGE = 7 * 24 * 3600

PLAN_ACCEPTED = (
    "The plan was just accepted. MANDATORY before implementing: Read the "
    "project's CODING_RULES.md in full in this session and follow every "
    "applicable rule while writing code. If already read this session, "
    "re-confirm the rules relevant to the files you are about to change."
)
FIRST_EDIT = (
    "First code edit this session. If you have not read the project's "
    "CODING_RULES.md in this session, Read it in full before continuing "
    "and follow every applicable rule."
)


def emit(event, text):
    print(json.dumps({
        "hookSpecificOutput": {"hookEventName": event, "additionalContext": text}
    }))


def project_dir(data):
    """Project root. The session cwd can be a subfolder, so prefer the env var."""
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env)
    cwd = Path(data.get("cwd") or Path.cwd())
    for d in (cwd, *cwd.parents):
        if (d / "CODING_RULES.md").exists():
            return d
    return cwd


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return  # never block tools on malformed input
    project = project_dir(data)
    if not (project / "CODING_RULES.md").exists():
        return  # project has no coding rules installed
    if (project / ".claude" / "hooks" / "coding-rules-reminder.off").exists():
        return  # disabled via /coding-rules:hooks off
    event = data.get("hook_event_name", "")
    if event == "PostToolUse":
        emit("PostToolUse", PLAN_ACCEPTED)
    elif event == "PreToolUse":
        session = re.sub(r"[^A-Za-z0-9_-]", "", str(data.get("session_id", "")))
        if not session:
            return
        tmp = Path(tempfile.gettempdir())
        now = time.time()
        for stale in tmp.glob(MARKER_PREFIX + "*"):
            try:
                if now - stale.stat().st_mtime > MARKER_MAX_AGE:
                    stale.unlink()
            except OSError:
                pass
        marker = tmp / (MARKER_PREFIX + session)
        if marker.exists():
            return
        try:
            marker.touch()
        except OSError:
            pass
        emit("PreToolUse", FIRST_EDIT)


if __name__ == "__main__":
    main()
