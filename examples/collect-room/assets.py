"""Prepare assets.inc for main.asm: converted terrain art, the actor and header lettering.

scripts/coco.py calls prepare(output) before assembling, because coco.toml names
this file. The art is converted by experiments/assets/prepare.py and must match
the independent drawings in expected.py before anything is published.
"""

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


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
    """Use the validated asset preparer; map terrain IDs explicitly."""
    bundle = output / "prepared.json"
    include = output / "assets.inc"
    for path in (bundle, include):
        path.unlink(missing_ok=True)
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "experiments/assets/prepare.py"),
            "build",
            "--output",
            str(bundle),
        ],
        check=True,
        timeout=30,
    )
    data = json.loads(bundle.read_text())
    pictures = {a["asset_id"]: bytes.fromhex(a["hex"]) for a in data["assets"]}
    packed = [pictures[i] for i in data["terrain_to_asset"]]
    art = model().ART
    if tuple(packed) != art[:4]:
        raise ValueError("Terrain art changed: review the independent expected pixels first")
    values = b"".join(expand(picture) for picture in (*packed, art[4]))
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
