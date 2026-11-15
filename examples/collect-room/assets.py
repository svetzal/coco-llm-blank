"""Prepare assets.inc for main.asm: converted terrain art, the actor and header lettering.

scripts/coco.py calls prepare(output) before assembling, because coco.toml names
this file. scripts/graphics.py converts terrain.png (floor, wall, collectible and
exit, left to right), and the result must match the independent drawings in
expected.py before anything is published.
"""

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "terrain.png"


def model():
    from coco import load_expected

    return load_expected(HERE)


def headers() -> bytes:
    """Prepare original 5x7 lettering into three eight-scanline strips."""
    font = json.loads((HERE / "letters.json").read_text())
    output = bytearray()
    for message in model().MESSAGES:
        rows = [0] * 8
        for column, char in enumerate(message):
            for y, bits in enumerate(font[char]):
                rows[y] |= bits << (251 - (column * 6 + 16))
        output.extend(b"".join(row.to_bytes(32, "big") for row in rows))
    return bytes(output)


def expand(picture: bytes) -> bytes:
    """Duplicate each source pixel horizontally and each row vertically."""
    return b"".join(
        int("".join(bit * 2 for bit in f"{row:08b}"), 2).to_bytes(2, "big") * 2 for row in picture
    )


def prepare(output: Path) -> None:
    """Convert the terrain drawing; terrain ID N is cell N of the sheet."""
    from native import ROOT

    terrain = output / "terrain"
    include = output / "assets.inc"
    for path in (terrain.with_suffix(".bin"), include):
        path.unlink(missing_ok=True)
    # One source pixel is one RG6 pixel: keep every column and copy each pixel.
    convert = [sys.executable, ROOT / "scripts/graphics.py", "sheet", SOURCE, "--mode", "RG6"]
    convert += ["--cell", "8x8", "--size", "8x8", "--fit", "stretch", "--resample", "nearest"]
    convert += ["--out", terrain]
    subprocess.run(convert, check=True, stdout=subprocess.DEVNULL, timeout=60)
    data = terrain.with_suffix(".bin").read_bytes()
    packed = [data[i : i + 8] for i in range(0, len(data), 8)]
    art = model().ART
    if tuple(packed) != art[:4]:
        raise ValueError("Terrain art changed: review the independent expected pixels first")
    values = b"".join(expand(picture) for picture in (*packed, art[4]))
    # The two guard bytes exist only for the check.
    lines = ["asset_guard_before fcb $a5", "art"]
    for label, block in (("", values), ("headers", headers())):
        if label:
            lines.append(label)
        lines.extend(
            "        fcb " + ",".join(f"${n:02x}" for n in block[i : i + 16])
            for i in range(0, len(block), 16)
        )
    lines.append("asset_guard_after fcb $a5")
    include.write_text("\n".join(lines) + "\n")
