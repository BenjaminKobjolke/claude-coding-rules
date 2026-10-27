"""Load and validate icon transfer configuration."""

from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class IconFile:
    export_path: str
    repo_path: str
    note: str
    fallback_png: str | None = None
    regenerates_launcher: bool = False

    @property
    def kind(self) -> str:
        return Path(self.export_path).suffix[1:].lower()


def _required_text(entry: dict, key: str, index: int) -> str:
    value = entry.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"icons[{index}] is missing required key '{key}'")
    return value


def load_config(path: Path) -> dict:
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise FileNotFoundError(
            f"Missing {path}; create tools/icon_transfer.json from "
            "icon_transfer.example.json"
        ) from error
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Invalid icon transfer JSON in {path}: {error}") from error
    if not isinstance(config, dict):
        raise ValueError("icon_transfer.json must contain a JSON object")
    if not isinstance(config.get("title"), str) or not config["title"].strip():
        raise ValueError("icon_transfer.json is missing required key 'title'")
    icons = config.get("icons")
    if not isinstance(icons, list):
        raise ValueError("icon_transfer.json is missing required key 'icons' (a list)")
    exports: set[str] = set()
    repos: set[str] = set()
    parsed = []
    for index, entry in enumerate(icons):
        if not isinstance(entry, dict):
            raise ValueError(f"icons[{index}] must be an object")
        export = _required_text(entry, "export", index)
        repo = _required_text(entry, "repo", index)
        note = _required_text(entry, "note", index)
        kind = Path(export).suffix[1:].lower()
        if kind not in ("png", "svg"):
            raise ValueError(f"icons[{index}] kind must be png or svg: {export}")
        if export in exports:
            raise ValueError(f"Duplicate export path: {export}")
        if repo in repos:
            raise ValueError(f"Duplicate repo path: {repo}")
        exports.add(export)
        repos.add(repo)
        fallback = entry.get("fallback_png")
        if fallback is not None and (
            not isinstance(fallback, str) or not fallback.strip()
        ):
            raise ValueError(
                f"icons[{index}] key 'fallback_png' must be a non-empty path"
            )
        parsed.append(
            IconFile(
                export,
                repo,
                note,
                fallback,
                bool(entry.get("regenerates_launcher", False)),
            )
        )
    config["_icon_files"] = tuple(parsed)
    notes = config.get("readme_notes", [])
    if not isinstance(notes, list) or any(not isinstance(note, str) for note in notes):
        raise ValueError("'readme_notes' must be a list of strings")
    command = config.get("launcher_command")
    if command is not None and (not isinstance(command, str) or not command.strip()):
        raise ValueError("'launcher_command' must be a non-empty path")
    extension = config.get("extension")
    if extension is not None and (
        not isinstance(extension, str) or not extension.strip()
    ):
        raise ValueError("'extension' must be a module name")
    return config
