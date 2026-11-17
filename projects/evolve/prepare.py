"""Convert the creature pictures to sprite includes before main.asm is assembled.

scripts/coco.py calls prepare(output) because coco.toml names this file. Each
creature PNG in art/creatures/ (1024x1024, transparent background) is put on
the board square's grey, then converted to a 48x40 gime-320x16 sprite with the
16 colour codes of art/game.contract.json, in register order. The old outputs
are removed first, so a failed conversion stops the assembly.

The words and the digits of font.py are packed into text.asm: two pixels in
each byte, the left pixel in the high bits.

The demo of demo.py goes into demo.asm: the glyphs of font.py as one bit for
each pixel (the program draws them), the margin words, the captions, the
boards and the steps.
"""

import subprocess
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from demo import CAPTIONS, IDLE_SCANS, STEPS
from font import DIGIT_INK, GLYPHS, WORDS
from layout import (
    CAPTION_ROW,
    KEYS,
    LINE_PITCH,
    MARGIN_LEFT,
    MARGIN_RIGHT,
    MARGIN_TOP_LEFT,
    MARGIN_TOP_RIGHT,
    MARGIN_TOP_ROW,
    centred,
)

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


# The demo's actions, and the arrows as the slide numbers them and as held bits.
ACTIONS = {"board": 0, "caption": 1, "key": 2, "move": 3, "end": 4}
SLIDE = {"U": 0, "D": 1, "L": 2, "R": 3}
HELD = {"-": 0, "U": 1, "D": 2, "L": 4, "R": 8}
CHARSET = sorted(GLYPHS)


def text_line(text: str, margin: int, row: int) -> str:
    """One line of words: its byte column, its row, its glyph numbers, $FF."""
    codes = [centred(text, margin) // 2, row] + [CHARSET.index(c) for c in text] + [0xFF]
    return "        fcb " + ",".join(f"${b:02X}" for b in codes)


def step_arguments(action: str, rest: list, boards: list, names: list) -> tuple[int, int]:
    """The two argument bytes of a demo step."""
    if action == "board":
        return boards.index(rest[0]), 0
    if action == "caption":
        return names.index(rest[0]), 0
    if action == "key":
        return HELD[rest[0]], 0
    if action == "move":
        return SLIDE[rest[0]], rest[1]
    return 0, 0


def write_demo(output: Path) -> None:
    lines = ["* Made by prepare.py from demo.py and font.py. Do not edit."]
    lines.append(f"IDLESCANS equ {IDLE_SCANS}")
    tallest = max(len(caption) for caption in CAPTIONS.values())
    lines.append(f"CAPY equ {CAPTION_ROW}")
    lines.append(f"CAPH equ {tallest * LINE_PITCH}")
    lines.append("* The glyphs: 8 rows each, one bit for each pixel, the left pixel in bit 7.")
    lines.append("font")
    for char in CHARSET:
        bits = [int(row.replace("#", "1").replace(".", "0"), 2) for row in GLYPHS[char]]
        lines.append("        fcb " + ",".join(f"${b:02X}" for b in bits) + f"  {char!r}")
    for key in "^v<>":
        lines.append(f"G_{'UDLR'['^v<>'.index(key)]} equ {CHARSET.index(key)}")
    lines.append("* The arrow keys: glyph, byte column, row, held bit.")
    keys = []
    for arrow in "UDLR":
        x, y = KEYS[arrow]
        keys += [f"G_{arrow}", str(x // 2), str(y), str(HELD[arrow])]
    lines.append("keys    fcb " + ",".join(keys))
    lines.append("* The words at the top of the margins. Each line: byte column, row,")
    lines.append("* glyph numbers, $FF. $FE ends the words.")
    lines.append("dtop")
    for number, text in enumerate(MARGIN_TOP_LEFT):
        lines.append(text_line(text, MARGIN_LEFT, MARGIN_TOP_ROW + number * LINE_PITCH))
    for number, text in enumerate(MARGIN_TOP_RIGHT):
        lines.append(text_line(text, MARGIN_RIGHT, MARGIN_TOP_ROW + number * LINE_PITCH))
    lines.append("        fcb $FE")
    names = list(CAPTIONS)
    lines.append("captions fdb " + ",".join(f"cap_{name}" for name in names))
    for name in names:
        lines.append(f"cap_{name}")
        for number, text in enumerate(CAPTIONS[name]):
            lines.append(text_line(text, MARGIN_LEFT, CAPTION_ROW + number * LINE_PITCH))
        lines.append("        fcb $FE")
    boards = [step[2] for step in STEPS if step[1] == "board"]
    lines.append("* The boards: 16 levels each, row by row.")
    lines.append("dboards")
    for board in boards:
        levels = [int(c, 16) for c in board.replace("/", "")]
        lines.append("        fcb " + ",".join(str(v) for v in levels))
    lines.append("* The steps: wait, action, two arguments.")
    lines.append("dsteps")
    for wait, action, *rest in STEPS:
        first, second = step_arguments(action, rest, boards, names)
        lines.append(f"        step {wait},{ACTIONS[action]},{first},{second}")
    (output / "demo.asm").write_text("\n".join(lines) + "\n")


def prepare(output: Path) -> None:
    from native import ROOT

    write_words(output)
    write_demo(output)
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
