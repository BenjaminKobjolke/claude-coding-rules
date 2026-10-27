"""Shared constants for the coding rules apply operation."""

import re

MANAGED_COMMENT = (
    "<!-- Managed by /coding-rules:apply — do not edit rule blocks by hand -->"
)

# Two destinations. CODING_RULES.md holds code quality (binding always);
# IMPLEMENTATION_FLOW.md holds the orchestration steps, which an external
# orchestrator may run itself and therefore has to be able to ignore wholesale.
RULES_FILE = "CODING_RULES.md"
FLOW_FILE = "IMPLEMENTATION_FLOW.md"
FLOW_TITLE = "# Implementation Flow (All Languages)"
GRAPHIFY_FLOW_TITLE = "# graphify Flow Steps (Optional Addon)"
FLOW_RELS = {FLOW_FILE, "implementation_flow_addons/graphify_flow.md"}
FLOW_TITLES = {FLOW_TITLE, GRAPHIFY_FLOW_TITLE}

# Pre-split names, still found in already-applied projects and stale manifests.
LEGACY_FLOW_TITLE = "# AI Workflow Rules (All Languages)"
LEGACY_RELS = {
    "AI_RULES.md": FLOW_FILE,
    "ai_rules_addons/graphify.md": "implementation_flow_addons/graphify.md",
}
# Titles a source doc is also known by, so an old block isn't mistaken for
# user-authored content by split_orphan_tail during the migration.
HEADING_ALIASES = {
    FLOW_TITLE: {LEGACY_FLOW_TITLE},
    "# C# Rules (.NET)": {"# C# Rules (.NET Framework / Windows Forms)"},
    "# Essential Additional Rules (must-have)": {
        "# 8 Essential Additional Rules (must-have)"
    },
}

SPLITS = {"PYTHON_RULES.md": (7, {
    "python/WEB_TEMPLATES.md": ("jinja2", "flask"),
    "python/GUI.md": ("pyside6",),
    "python/LOCALIZATION.md": (
        "python-localization", "python_localization", "lang/en.json"
    ),
    "python/RELEASE.md": ("build_version.txt", "tools/release/"),
    "python/INSTALLER.md": ("installer/", "tools/build_installer.bat"),
    "python/DATABASE.md": ("sqlalchemy",),
}), "CSHARP_RULES.md": (2, {
    "csharp/WINFORMS.md": ("system.windows.forms", "usewindowsforms"),
}), "FLUTTER_RULES.md": (14, {
    "flutter/APP.md": ("lib/main.dart", "android/app/"),
}), "PHP_RULES.md": (5, {
    "php/APP.md": (
        "public/index.php", ".htaccess", "slim/slim", "twig/twig", "cycle/orm",
        "config/database.php.example",
    ),
}), "project_type/REST_API.md": (9, {
    "project_type/rest_api/JWT_AUTH.md": ("firebase/php-jwt",),
})}

POINTER_TITLE = "# Coding Rules (Pointer)"
POINTER_BLOCK_TEMPLATE = """# Version
{version}

# Coding Rules (Pointer)

This project's rules live in two files in the project root:

- `CODING_RULES.md` — code quality and conventions. BINDING for all code work in
  this repository, always.
- `IMPLEMENTATION_FLOW.md` — the end-to-end flow to follow when planning and
  implementing a change (checks, gates, Definition of Done).

MANDATORY: Before writing or editing ANY code, you MUST Read BOTH files in full
**in the current session**. Do not rely on memory of a previous session, a
summary, or partial reads.

If you are about to make a code change and have not read both files in this
session: STOP, read them, then continue.

An external tool may orchestrate the implementation itself. When a skill or run
states that the implementation is orchestrated, ignore `IMPLEMENTATION_FLOW.md`
entirely — the orchestrator runs those steps as its own phases. `CODING_RULES.md`
stays binding either way.

Next to `CODING_RULES.md`, apply also writes `CODING_RULES_PLAN.md`,
`CODING_RULES_REVIEW.md` and `CODING_RULES_CODE.md`. When an orchestrator's run
instructions name one of these step files, that file replaces `CODING_RULES.md`
for that run; without such an instruction, `CODING_RULES.md` stays binding in full.

Do not inline rules back into this file and do not use `@import` for either file —
they are intentionally referenced, not imported.
"""

# Both backends go through the same wrapper script (tools/coding_rules_delegate.*),
# so both need the same entries. Bare and ./-prefixed forms, because the allow
# entry is matched as a literal command prefix.
DELEGATE_PERMS = [
    "Bash(tools/coding_rules_delegate.sh:*)",
    "Bash(./tools/coding_rules_delegate.sh:*)",
    "PowerShell(tools/coding_rules_delegate.ps1:*)",
    "PowerShell(./tools/coding_rules_delegate.ps1:*)",
]

DELEGATION_PERMS = {
    "codex": DELEGATE_PERMS,
    "deepseek": DELEGATE_PERMS,
}

ATX_HEADING_RE = re.compile(r"^#{1,6} ")
MARKER_RE = re.compile(r"^<!-- (codex|deepseek): (enabled|disabled) -->$")
