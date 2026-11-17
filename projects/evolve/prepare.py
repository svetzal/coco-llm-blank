"""Convert the creature pictures to sprite includes before main.asm is assembled.

scripts/coco.py calls prepare(output) because coco.toml names this file. Each
creature PNG in art/creatures/ (1024x1024, transparent background) is put on
the board square's grey, then converted to a 48x40 gime-320x16 sprite with the
16 colour codes of art/game.contract.json, in register order. The old outputs
are removed first, so a failed conversion stops the assembly.

The words and the digits of font.py are packed into text.asm: two pixels in
each byte, the left pixel in the high bits.
"""

import subprocess
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from font import DIGIT_INK, GLYPHS, WORDS

CREATURES = HERE / "art/creatures"
# The contract's colour codes, register 0 first. Register 1 ($10, dark grey) is
# the board square, so the sprites are put on its measured colour.
CODES = "00,10,20,30,05,15,25,24,0E,12,21,0B,1C,2D,07,16"
SQUARE_RGB = (63, 63, 63)
# The trilobite is wide and low: crop it to the creature (the owner chose this).
BOXES = {"03-trilobite": "90,133,849,826"}


def word_rows(text: str, scale: int, ink: int) -> list[list[int]]:
    """The palette register of each pixel, row by row, at the scale."""
    rows = []
    for glyph_row in range(8):
        row = []
        for letter in text:
            for mark in GLYPHS[letter][glyph_row]:
                row += [ink if mark == "#" else 0] * scale
        rows += [row] * scale
    return rows


def write_words(output: Path) -> None:
    lines = ["* Made by prepare.py from font.py. Do not edit."]
    for label, text, scale, ink in WORDS:
        rows = word_rows(text, scale, ink)
        lines.append(f"t_{label}_bpr equ {len(rows[0]) // 2}")
        lines.append(f"t_{label}_rows equ {len(rows)}")
        lines.append(f"t_{label}")
        for row in rows:
            packed = [row[i] << 4 | row[i + 1] for i in range(0, len(row), 2)]
            for start in range(0, len(packed), 16):
                values = ",".join(f"${b:02X}" for b in packed[start : start + 16])
                lines.append(f"        fcb {values}")
    lines.append("* The digits 0 to 9: 8 rows of 4 bytes each.")
    lines.append("digits")
    for digit in "0123456789":
        for row in word_rows(digit, 1, DIGIT_INK):
            packed = [row[i] << 4 | row[i + 1] for i in range(0, len(row), 2)]
            lines.append("        fcb " + ",".join(f"${b:02X}" for b in packed))
    (output / "text.asm").write_text("\n".join(lines) + "\n")


def prepare(output: Path) -> None:
    from native import ROOT

    write_words(output)
    sources = sorted(CREATURES.glob("[0-9][0-9]-*.png"))
    if len(sources) != 11:
        raise SystemExit(f"expected 11 creature pictures in {CREATURES}, found {len(sources)}")
    for path in output.glob("c[0-9][0-9]*"):
        path.unlink()
    for source in sources:
        level = source.stem[:2]
        flat = output / f"c{level}-source.png"
        picture = Image.open(source).convert("RGBA")
        square = Image.new("RGBA", picture.size, (*SQUARE_RGB, 255))
        square.alpha_composite(picture)
        square.convert("RGB").save(flat)
        convert = [sys.executable, ROOT / "scripts/graphics.py", "convert", flat]
        convert += ["--mode", "gime-320x16", "--size", "48x40", "--codes", CODES]
        if source.stem in BOXES:
            convert += ["--box", BOXES[source.stem]]
        convert += ["--label", f"c{level}", "--out", output / f"c{level}"]
        subprocess.run(convert, check=True, stdout=subprocess.DEVNULL, timeout=120)
