"""Validate and atomically write icon image files."""

import math
import os
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as image:
        header = image.read(24)
    if (len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n"
            or header[8:16] != b"\x00\x00\x00\x0dIHDR"):
        raise ValueError(f"Invalid PNG header: {path}")
    width = int.from_bytes(header[16:20], "big")
    height = int.from_bytes(header[20:24], "big")
    if width == 0 or height == 0:
        raise ValueError(f"Invalid PNG dimensions: {path}")
    return width, height


def svg_aspect(path: Path) -> tuple[float, float]:
    data = path.read_bytes()
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError(f"SVG must be UTF-8 XML: {path}") from error
    if "<!DOCTYPE" in text.upper() or "<!ENTITY" in text.upper():
        raise ValueError(f"Unsafe SVG declaration: {path}")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as error:
        raise ValueError(f"Invalid SVG XML: {path}: {error}") from error
    if root.tag.rsplit("}", 1)[-1] != "svg":
        raise ValueError(f"SVG root is not <svg>: {path}")
    view_box = root.attrib.get("viewBox")
    try:
        values = [float(value) for value in view_box.replace(",", " ").split()]
    except (AttributeError, ValueError):
        values = []
    if (
        len(values) != 4
        or not all(math.isfinite(value) for value in values)
        or values[2] <= 0
        or values[3] <= 0
    ):
        raise ValueError(f"SVG needs a positive four-number viewBox: {path}")
    for element in root.iter():
        name = element.tag.rsplit("}", 1)[-1].lower()
        if name in ("image", "text", "filter", "mask"):
            raise ValueError(f"SVG cannot contain <{name}>: {path}")
    return values[2], values[3]


def check_safe_file(incoming: Path, source: Path) -> None:
    if not incoming.is_file() or any(
        path.is_symlink() for path in (incoming, *incoming.parents)
        if path != source and source in path.parents
    ):
        raise ValueError(f"Icon must be a regular file, not a link: {incoming}")
