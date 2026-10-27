"""Verbatim template from claude-coding-rules: rules/flutter_setup_files/icon_transfer/.

Projects never edit this file; project-specific behaviour belongs in the JSON
configuration or in the configured extension module.
"""

from dataclasses import dataclass, field
import filecmp
import importlib
import math
from pathlib import Path
import shutil
import subprocess
import sys

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

icon_config = importlib.import_module("icon_config")
icon_images = importlib.import_module("icon_images")
icon_placeholders = importlib.import_module("icon_placeholders")
IconFile = icon_config.IconFile
load_config = icon_config.load_config
atomic_write = icon_images.atomic_write
check_safe_file = icon_images.check_safe_file
png_size = icon_images.png_size
svg_aspect = icon_images.svg_aspect
placeholder_svg = icon_placeholders.placeholder_svg


CONFIG_PATH = TOOLS_DIR / "icon_transfer.json"


try:
    CONFIG = load_config(CONFIG_PATH)
    CONFIG_ERROR: Exception | None = None
except (FileNotFoundError, ValueError) as error:
    CONFIG = {}
    CONFIG_ERROR = error
ICON_FILES: tuple[IconFile, ...] = CONFIG.get("_icon_files", ())
PENDING_LAUNCHER = Path("tools/.icon_transfer_launcher_pending")


@dataclass(frozen=True)
class ExtraPlan:
    updated: tuple[str, ...] = ()
    unchanged: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()
    placeholders: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    known_paths: set[str] = field(default_factory=set)
    listed_count: int = 0
    source_writes: tuple[tuple[Path, bytes], ...] = ()
    tier_writes: tuple[tuple[Path, bytes], ...] = ()
    source_deletes: tuple[Path, ...] = ()


def reference_aspect(root: Path, icon: IconFile) -> tuple[float, float]:
    source = root / icon.repo_path
    if icon.kind == "svg":
        if source.is_file():
            return svg_aspect(source)
        if icon.fallback_png:
            width, height = png_size(root / icon.fallback_png)
            return float(width), float(height)
        return 1.0, 1.0
    width, height = png_size(source)
    return float(width), float(height)


def _load_extension(config: dict):
    return (
        importlib.import_module(config["extension"])
        if config.get("extension")
        else None
    )


def export_icons(root: Path, target: Path) -> int:
    if CONFIG_ERROR:
        raise CONFIG_ERROR
    target.mkdir(parents=True, exist_ok=True)
    readme = [
        f"Editable icon sources for {CONFIG['title']}", "",
        "Keep names and folders unchanged.", "Send the whole folder back.", "",
        "SVG rules: square or matching proportions; flat fills;",
        "convert text to outlines; no embedded images, filters or masks.",
        "PNG rules: keep PNG format and pixel dimensions unless the note says "
        "otherwise.",
        "",
    ]
    readme.extend(CONFIG.get("readme_notes", []))
    if CONFIG.get("readme_notes"):
        readme.append("")
    written = 0
    for icon in ICON_FILES:
        source = root / icon.repo_path
        destination = target / icon.export_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        if icon.kind == "svg":
            width, height = reference_aspect(root, icon)
            is_placeholder = not source.is_file()
            if is_placeholder:
                destination.write_bytes(placeholder_svg(round(width), round(height)))
            else:
                shutil.copyfile(source, destination)
                width, height = svg_aspect(destination)
            label = f"SVG viewBox {width:g}x{height:g}" + (
                " — PLACEHOLDER for designer" if is_placeholder else ""
            )
        else:
            if not source.is_file():
                raise FileNotFoundError(f"Missing icon source: {source}")
            shutil.copyfile(source, destination)
            width, height = png_size(source)
            label = f"PNG {width}x{height} px"
        written += 1
        readme.extend((f"{icon.export_path} ({label})", icon.note, ""))
    extension = _load_extension(CONFIG)
    if extension:
        readme.extend(extension.export_extra(root, target, png_size))
    (target / "README.txt").write_text("\n".join(readme), encoding="utf-8")
    return written


@dataclass(frozen=True)
class ImportResult:
    updated: tuple[str, ...]
    unchanged: tuple[str, ...]
    missing: tuple[str, ...]
    placeholders: tuple[str, ...]
    unknown: tuple[str, ...]
    size_warnings: tuple[str, ...]

    @property
    def launcher_sources_changed(self) -> bool:
        return any(
            icon.export_path in self.updated and icon.regenerates_launcher
            for icon in ICON_FILES
        )


def _is_placeholder(path: Path, icon: IconFile, root: Path) -> bool:
    if icon.kind == "png":
        return False
    width, height = reference_aspect(root, icon)
    return path.read_bytes() == placeholder_svg(round(width), round(height))


def import_icons(root: Path, source: Path) -> ImportResult:
    if CONFIG_ERROR:
        raise CONFIG_ERROR
    if not source.is_dir():
        raise ValueError(f"Icon source is not a folder: {source}")
    extension = _load_extension(CONFIG)
    extra = (
        extension.prepare_extra_import(root, source, png_size)
        if extension else ExtraPlan()
    )
    updated = list(extra.updated)
    unchanged = list(extra.unchanged)
    missing = list(extra.missing)
    placeholders = list(extra.placeholders)
    warnings = list(extra.warnings)
    copies: list[tuple[IconFile, Path]] = []
    listed_count = extra.listed_count

    for icon in ICON_FILES:
        incoming = source / icon.export_path
        if not incoming.exists() and not incoming.is_symlink():
            missing.append(icon.export_path)
            continue
        check_safe_file(incoming, source)
        listed_count += 1
        current = root / icon.repo_path
        if icon.kind == "svg":
            size = svg_aspect(incoming)
            reference = reference_aspect(root, icon)
            if _is_placeholder(incoming, icon, root):
                placeholders.append(icon.export_path)
                continue
            if not math.isclose(
                size[0] * reference[1], size[1] * reference[0], rel_tol=0.01
            ):
                warnings.append(
                    f"{icon.export_path}: viewBox {size[0]:g}x{size[1]:g} differs from "
                    f"reference {reference[0]:g}x{reference[1]:g}"
                )
        else:
            size = png_size(incoming)
            if _is_placeholder(incoming, icon, root):
                placeholders.append(icon.export_path)
                continue
            reference = png_size(current)
            if size != reference:
                warnings.append(
                    f"{icon.export_path}: {reference[0]}x{reference[1]} "
                    f"-> {size[0]}x{size[1]}"
                )
        is_unchanged = current.is_file() and filecmp.cmp(
            incoming, current, shallow=False
        )
        (unchanged if is_unchanged else updated).append(icon.export_path)
        if not is_unchanged:
            copies.append((icon, incoming))

    known = (
        {icon.export_path for icon in ICON_FILES}
        | set(extra.known_paths)
        | {"README.txt"}
    )
    unknown = tuple(sorted(
        path.relative_to(source).as_posix() for path in source.rglob("*")
        if path.is_file()
        and path.relative_to(source).as_posix() not in known
    ))
    if listed_count == 0:
        raise ValueError(f"No listed icon files found in {source}")

    pending_launcher = root / PENDING_LAUNCHER
    if any(
        icon.export_path in updated and icon.regenerates_launcher for icon in ICON_FILES
    ):
        pending_launcher.parent.mkdir(parents=True, exist_ok=True)
        pending_launcher.touch()
    for icon, incoming in copies:
        atomic_write(root / icon.repo_path, incoming.read_bytes())
    for destination, data in extra.source_writes:
        atomic_write(destination, data)
    for destination, data in extra.tier_writes:
        atomic_write(destination, data)
        updated.append(destination.relative_to(root).as_posix())
    for old_source in extra.source_deletes:
        old_source.unlink()
    return ImportResult(
        tuple(updated), tuple(unchanged), tuple(missing), tuple(placeholders),
        unknown, tuple(warnings),
    )


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[0] not in ("export", "import") or not argv[1].strip():
        print("Usage: icon_transfer.py export|import <folder>")
        return 1
    root = Path(__file__).resolve().parent.parent
    folder = Path(argv[1])
    try:
        if CONFIG_ERROR:
            raise CONFIG_ERROR
        if argv[0] == "export":
            written = export_icons(root, folder)
            print(f"Exported {written} icons to {folder}")
            return 0
        result = import_icons(root, folder)
        print(
            f"Updated {len(result.updated)}, unchanged {len(result.unchanged)}, "
            f"missing {len(result.missing)}, placeholder {len(result.placeholders)}, "
            f"unknown {len(result.unknown)}"
        )
        sections = (
            ("Updated", result.updated), ("Missing", result.missing),
            ("Placeholder (not drawn yet)", result.placeholders),
            ("Unknown", result.unknown), ("Size warning", result.size_warnings),
        )
        for label, names in sections:
            for name in names:
                print(f"{label}: {name}")
        print("Use git diff to review or undo imported changes.")
        pending_launcher = root / PENDING_LAUNCHER
        if pending_launcher.exists():
            command = CONFIG.get("launcher_command")
            if not command:
                print(
                    "Reminder: launcher icon sources changed; "
                    "regenerate launcher icons."
                )
                return 0
            result = subprocess.run(
                ["cmd", "/d", "/c", "call", str(root / command)],
                stdin=subprocess.DEVNULL, check=False,
            )
            if result.returncode == 0:
                pending_launcher.unlink()
            return result.returncode
        return 0
    except (ValueError, FileNotFoundError, OSError) as error:
        print(f"ERROR: {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
