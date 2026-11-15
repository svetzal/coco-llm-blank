"""Convert tiles.png to tiles.asm with scripts/graphics.py, before main.asm is assembled.

scripts/coco.py calls prepare(output) because coco.toml names this file. The old
outputs are removed first, so a failed conversion leaves no include and the
assembly stops instead of using stale pictures.
"""

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "tiles.png"


def prepare(output: Path) -> None:
    from native import ROOT

    prefix = output / "tiles"
    for suffix in (".asm", ".bin", ".png"):
        prefix.with_suffix(suffix).unlink(missing_ok=True)
    # One source pixel is one RG6 pixel: keep every column and copy each pixel.
    convert = [sys.executable, ROOT / "scripts/graphics.py", "sheet", SOURCE, "--mode", "RG6"]
    convert += ["--cell", "8x8", "--size", "8x8", "--fit", "stretch", "--resample", "nearest"]
    convert += ["--label", "tiles", "--out", prefix]
    subprocess.run(convert, check=True, stdout=subprocess.DEVNULL, timeout=60)
