"""Focused, dependency-free checks for the icon transfer template."""

import importlib.util
import json
from pathlib import Path
import shutil
import tempfile


TEMPLATE = Path(__file__).resolve().parent


def _png(size: int, color: bytes = b"\xff\x00\x00") -> bytes:
    import struct
    import zlib

    signature = b"\x89PNG\r\n\x1a\n"
    rows = b"".join(b"\x00" + color * size for _ in range(size))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data)) + kind + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    header = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    return (
        signature + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(rows))
        + chunk(b"IEND", b"")
    )


def _setup(config_icons=None, extension=None):
    temp = tempfile.TemporaryDirectory()
    root = Path(temp.name)
    tools = root / "tools"
    tools.mkdir()
    shutil.copyfile(TEMPLATE / "icon_transfer.py", tools / "icon_transfer.py")
    shutil.copyfile(TEMPLATE / "icon_config.py", tools / "icon_config.py")
    shutil.copyfile(TEMPLATE / "icon_images.py", tools / "icon_images.py")
    shutil.copyfile(TEMPLATE / "icon_placeholders.py", tools / "icon_placeholders.py")
    icons = config_icons or [
        {
            "export": "launcher.png", "repo": "assets/launcher.png",
            "note": "Launcher icon", "regenerates_launcher": True,
        },
        {"export": "notice.png", "repo": "assets/notice.png",
         "note": "Notification icon"},
        {
            "export": "logo.svg", "repo": "assets/logo.svg",
            "note": "App logo", "fallback_png": "assets/logo.png",
        },
    ]
    config = {
        "title": "Example App", "readme_notes": ["Keep the originals."],
        "icons": icons,
    }
    if extension:
        config["extension"] = extension
    (tools / "icon_transfer.json").write_text(json.dumps(config), encoding="utf-8")
    (root / "assets").mkdir()
    (root / "assets/launcher.png").write_bytes(_png(4))
    (root / "assets/notice.png").write_bytes(_png(2, b"\x00\xff\x00"))
    (root / "assets/logo.png").write_bytes(_png(8, b"\x00\x00\xff"))
    (root / "assets/logo.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 8 8">'
        '<path d="M0 0h8v8H0z"/></svg>', encoding="utf-8"
    )
    spec = importlib.util.spec_from_file_location(
        f"icon_transfer_test_{id(temp)}", tools / "icon_transfer.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return temp, root, tools, module


def test_export_writes_sources_readme_title_and_notes():
    temp, root, _, engine = _setup()
    try:
        target = root / "handoff"
        engine.export_icons(root, target)
        assert {"launcher.png", "notice.png", "logo.svg", "README.txt"} <= {
            p.name for p in target.rglob("*") if p.is_file()
        }
        readme = (target / "README.txt").read_text(encoding="utf-8")
        assert "Editable icon sources for Example App" in readme
        assert "Keep the originals." in readme
    finally:
        temp.cleanup()


def test_export_then_unchanged_import():
    temp, root, _, engine = _setup()
    try:
        target = root / "handoff"
        engine.export_icons(root, target)
        result = engine.import_icons(root, target)
        assert result.updated == ()
        assert len(result.unchanged) == 3
    finally:
        temp.cleanup()


def test_changed_png_copies_and_size_change_warns():
    temp, root, _, engine = _setup()
    try:
        target = root / "handoff"
        engine.export_icons(root, target)
        (target / "launcher.png").write_bytes(_png(5, b"\x00\x00\x00"))
        result = engine.import_icons(root, target)
        assert "launcher.png" in result.updated
        assert engine.png_size(root / "assets/launcher.png") == (5, 5)
        assert any("launcher.png" in warning for warning in result.size_warnings)
    finally:
        temp.cleanup()


def test_unsafe_svg_rejected_before_any_copy():
    temp, root, _, engine = _setup()
    try:
        target = root / "handoff"
        engine.export_icons(root, target)
        (target / "launcher.png").write_bytes(_png(6))
        (target / "logo.svg").write_text(
            '<svg viewBox="0 0 8 8"><text>bad</text></svg>', encoding="utf-8"
        )
        try:
            engine.import_icons(root, target)
        except ValueError as error:
            assert "<text>" in str(error)
        else:
            raise AssertionError("unsafe SVG was accepted")
        assert engine.png_size(root / "assets/launcher.png") == (4, 4)
    finally:
        temp.cleanup()


def test_svg_filters_and_masks_are_rejected():
    for forbidden in ("filter", "mask"):
        temp, root, _, engine = _setup()
        try:
            target = root / "handoff"
            engine.export_icons(root, target)
            (target / "logo.svg").write_text(
                f'<svg viewBox="0 0 8 8"><{forbidden}/></svg>', encoding="utf-8"
            )
            try:
                engine.import_icons(root, target)
            except ValueError as error:
                assert f"<{forbidden}>" in str(error)
            else:
                raise AssertionError(f"SVG containing <{forbidden}> was accepted")
        finally:
            temp.cleanup()


def test_missing_svg_exports_placeholder_and_import_reports_it():
    temp, root, _, engine = _setup()
    try:
        (root / "assets/logo.svg").unlink()
        target = root / "handoff"
        engine.export_icons(root, target)
        result = engine.import_icons(root, target)
        assert "logo.svg" in result.placeholders
    finally:
        temp.cleanup()


def test_extra_file_is_unknown():
    temp, root, _, engine = _setup()
    try:
        target = root / "handoff"
        engine.export_icons(root, target)
        (target / "extra.txt").write_text("extra", encoding="utf-8")
        result = engine.import_icons(root, target)
        assert "extra.txt" in result.unknown
    finally:
        temp.cleanup()


def test_launcher_marker_is_cleared_after_successful_command():
    temp, root, tools, engine = _setup()
    try:
        fake = tools / "launcher.bat"
        fake.write_text("@echo off\r\nexit /b 0\r\n", encoding="utf-8")
        config_path = tools / "icon_transfer.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["launcher_command"] = "tools/launcher.bat"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        engine.CONFIG["launcher_command"] = config["launcher_command"]
        target = root / "handoff"
        engine.export_icons(root, target)
        (target / "launcher.png").write_bytes(_png(4, b"\x00\x00\x00"))
        engine.import_icons(root, target)
        assert engine.main(["import", str(target)]) == 0
        assert engine.png_size(root / "assets/launcher.png") == (4, 4)
        assert engine.PENDING_LAUNCHER == Path("tools/.icon_transfer_launcher_pending")
        assert not (root / engine.PENDING_LAUNCHER).exists()
    finally:
        temp.cleanup()


def test_extension_readme_and_import_writes():
    temp, root, tools, engine = _setup(extension="icon_extra")
    try:
        (tools / "icon_extra.py").write_text(
            "class Plan:\n"
            "    def __init__(self, root):\n"
            "        self.updated = ('extra.bin',)\n"
            "        self.unchanged = self.missing = self.placeholders = "
            "self.warnings = ()\n"
            "        self.known_paths = {'extra.bin'}\n"
            "        self.listed_count = 1\n"
            "        self.source_writes = "
            "((root / 'assets/extra.bin', b'extension'),)\n"
            "        self.tier_writes = self.source_deletes = ()\n"
            "def export_extra(root, target, png_size): return ['Extra artwork']\n"
            "def prepare_extra_import(root, source, png_size): return Plan(root)\n",
            encoding="utf-8",
        )
        target = root / "handoff"
        engine.export_icons(root, target)
        assert "Extra artwork" in (target / "README.txt").read_text(encoding="utf-8")
        result = engine.import_icons(root, target)
        assert "extra.bin" in result.updated
        assert (root / "assets/extra.bin").read_bytes() == b"extension"
    finally:
        temp.cleanup()


def test_duplicate_export_path_has_clear_error():
    icons = [
        {"export": "same.png", "repo": "a.png", "note": "A"},
        {"export": "same.png", "repo": "b.png", "note": "B"},
    ]
    temp = tempfile.TemporaryDirectory()
    try:
        tools = Path(temp.name) / "tools"
        tools.mkdir()
        shutil.copyfile(TEMPLATE / "icon_transfer.py", tools / "icon_transfer.py")
        shutil.copyfile(TEMPLATE / "icon_config.py", tools / "icon_config.py")
        shutil.copyfile(TEMPLATE / "icon_images.py", tools / "icon_images.py")
        shutil.copyfile(
            TEMPLATE / "icon_placeholders.py", tools / "icon_placeholders.py"
        )
        config = {"title": "Example", "icons": icons}
        (tools / "icon_transfer.json").write_text(json.dumps(config), encoding="utf-8")
        spec = importlib.util.spec_from_file_location(
            "duplicate_icon_transfer", tools / "icon_transfer.py"
        )
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except ValueError as error:
            assert "duplicate" in str(error).lower() and "export" in str(error).lower()
        else:
            try:
                module.load_config(tools / "icon_transfer.json")
            except ValueError as error:
                assert (
                    "duplicate" in str(error).lower()
                    and "export" in str(error).lower()
                )
            else:
                raise AssertionError("duplicate configuration unexpectedly loaded")
    finally:
        temp.cleanup()


def main():
    tests = [
        value for name, value in globals().items()
        if name.startswith("test_") and callable(value)
    ]
    for test in tests:
        test()
    print("Icon transfer engine checks passed.")


if __name__ == "__main__":
    main()
