"""Semver release helper: the release label is the ``pyproject.toml`` version.

Each release bumps the last segment (``0.1.0`` -> ``0.1.1``). ``release-tool create``
(``versioning = semver``) runs ``tools/version_increment.bat`` before the build and
``tools/version_decrement.bat`` to roll back when the build fails;
``tools/version_get.bat`` prints the current version.

Usage: ``python version_number.py [get|increment|decrement]``
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

# tools/release/version_number.py -> project root is two parents up.
PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"
_VERSION_LINE = re.compile(r'^version\s*=\s*"([^"]+)"', re.MULTILINE)


def read_version(pyproject: Path = PYPROJECT) -> str:
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def shift_patch(step: int, pyproject: Path = PYPROJECT) -> str:
    current = read_version(pyproject)
    *head, patch = current.split(".")
    new_patch = int(patch) + step
    if new_patch < 0:
        raise ValueError(f"cannot move {current} below patch 0")
    new_version = ".".join([*head, str(new_patch)])

    # Bytes keep the file's own line endings; the first matching line is [project]'s.
    text = pyproject.read_bytes().decode("utf-8")
    match = next(m for m in _VERSION_LINE.finditer(text) if m[1] == current)
    text = text[: match.start(1)] + new_version + text[match.end(1) :]
    pyproject.write_bytes(text.encode("utf-8"))
    return new_version


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    action = args[0] if args else "get"
    if action == "get":
        print(read_version())
    elif action == "increment":
        print(shift_patch(1))
    elif action == "decrement":
        print(shift_patch(-1))
    else:
        print("usage: python version_number.py [get|increment|decrement]")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
