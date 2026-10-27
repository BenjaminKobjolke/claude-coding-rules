"""Load update-all settings and discover configured repositories."""

import json
import os
import shutil
from pathlib import Path

NOISE_DIRS = {
    "node_modules", ".venv", "venv", "__pycache__", ".mypy_cache", ".ruff_cache"
}
SETTINGS_TEMPLATE = Path(__file__).resolve().parents[2] / "settings.example.json"
class SettingsError(ValueError):
    pass


def load_settings(path, warn=print):
    if not path.exists():
        example = path.with_name("settings.example.json")
        example.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SETTINGS_TEMPLATE, example)
        raise SettingsError(
            f"Settings not found. Copy {example} to settings.json and set your folders."
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SettingsError(f"Cannot read {path}: {exc}") from exc

    folders = data.get("folders")
    prefixes = data.get("ignore_prefixes", [])
    if (
        not isinstance(folders, list)
        or not folders
        or not all(isinstance(x, str) and x for x in folders)
    ):
        raise SettingsError("'folders' must be a non-empty list of strings.")
    if not isinstance(prefixes, list) or not all(
        isinstance(x, str) and x for x in prefixes
    ):
        raise SettingsError("'ignore_prefixes' entries must be non-empty strings.")

    existing = []
    for folder in map(Path, folders):
        if folder.is_dir():
            existing.append(folder)
        else:
            warn(f"warning: folder does not exist, skipping: {folder}")
    if not existing:
        raise SettingsError("None of the configured folders exist.")
    return existing, tuple(prefixes)


def find_repos(root, ignore_prefixes=()):
    """Yield git repos without descending into repos or ignored directories."""
    for dirpath, dirnames, _files in os.walk(root):
        current = Path(dirpath)
        if (current / ".git").exists():
            yield current
            dirnames[:] = []
            continue
        dirnames[:] = [
            name for name in dirnames
            if name not in NOISE_DIRS and not name.startswith(ignore_prefixes)
        ]

