"""Create deterministic visual stand-ins for editable designer artwork."""

import struct
import zlib


SVG_NAMESPACE = "http://www.w3.org/2000/svg"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def placeholder_svg(width: int, height: int) -> bytes:
    if width <= 0 or height <= 0:
        raise ValueError("Placeholder dimensions must be positive")
    content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!-- PLACEHOLDER: replace with final designer artwork. -->\n'
        f'<svg xmlns="{SVG_NAMESPACE}" viewBox="0 0 {width} {height}" '
        'id="placeholder">\n'
        f'  <rect width="{width}" height="{height}" fill="#bdbdbd"/>\n'
        f'  <path d="M0 0 L{width} {height} M{width} 0 L0 {height}" '
        'stroke="#666" stroke-width="2"/>\n'
        '</svg>\n'
    )
    return content.encode("utf-8")


def placeholder_png(size: int) -> bytes:
    if size <= 0:
        raise ValueError("Placeholder dimensions must be positive")
    pixels = bytearray()
    background = bytes((189, 189, 189))
    cross = bytes((102, 102, 102))
    for y in range(size):
        pixels.append(0)
        for x in range(size):
            pixels.extend(
                cross
                if abs(x - y) <= 1 or abs(x + y - size + 1) <= 1
                else background
            )
    header = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    return (
        PNG_SIGNATURE
        + _png_chunk(b"IHDR", header)
        + _png_chunk(b"IDAT", zlib.compress(pixels))
        + _png_chunk(b"IEND", b"")
    )


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data)) + kind + data
        + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    )
