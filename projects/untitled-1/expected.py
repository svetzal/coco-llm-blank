"""Independent model of the untitled-1 board and its rules.

Written from the layout rules and the game rules in the README, not from the
assembly's output. The key policy and the slide rules are modelled here, and
the model must agree with the boards written by hand in keys.txt. The creature pixels come from the source pictures in
art/creatures/ by the model's own conversion, not from bytes that the build or
the emulator made. The model therefore checks placement, packing, the page
crossings of the screen window and the display setup. It trusts
scripts/graphics.py, which has its own tests, for the conversion.
"""

import subprocess
import sys
import tempfile
from functools import cache
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

WIDTH, ROWS = 320, 192
SQUARE_W, SQUARE_H = 56, 48  # pixels; square on the display
BOARD_X = 48  # (320 - 4 * 56) / 2
CELL = (2, 2, 52, 44)  # grey cell inside a square: x, y, width, height
SPRITE = (4, 4, 48, 40)  # creature inside a square
BLACK, GREY = 0, 1  # palette registers

# The opening layout: levels row by row, 0 is empty.
OPENING = [1, 1, 1, 1, 1, 1, 2, 0, 0, 3, 0, 3, 11, 11, 10, 10]
TOP = 11  # the last creature does not merge
ARROWS = "UDLR"

# The contract's codes in register order, and their gime-composite colours as
# `graphics.py palettes` lists them (measured in XRoar 1.13.1).
CODES = "00,10,20,30,05,15,25,24,0E,12,21,0B,1C,2D,07,16"
RENDERED = [
    (20, 20, 20), (63, 63, 63), (154, 154, 154), (255, 255, 255),
    (117, 29, 2), (231, 93, 31), (255, 176, 83), (255, 200, 46),
    (0, 67, 21), (71, 145, 5), (99, 255, 48), (34, 28, 222),
    (34, 127, 241), (67, 248, 255), (155, 18, 60), (255, 79, 75),
]  # fmt: skip
SQUARE_RGB = RENDERED[GREY]
BOXES = {"03-trilobite": "90,133,849,826"}

# A full-width line is 640 samples, two for each pixel. XRoar 1.13.1 centres
# the 512-sample capture on the 640-sample active area (update_viewport in
# src/vo_render.c), so it starts at sample 64. The window is set once for each
# field (src/tcc1014/tcc1014.c), so the program waits some fields after the
# mode change before its first snapshot. Measured: edges at sample 36 for
# pixel 50 from the second field on.
CAPTURE_SAMPLES, FULL_WIDTH_START = 512, 64


@cache
def sprite(level: int) -> np.ndarray:
    """The 40x48 palette registers of one creature, on the square's grey."""
    source = min((HERE / "art/creatures").glob(f"{level:02d}-*.png"))
    picture = Image.open(source).convert("RGBA")
    flat = Image.new("RGBA", picture.size, (*SQUARE_RGB, 255))
    flat.alpha_composite(picture)
    with tempfile.TemporaryDirectory() as work:
        png = Path(work) / "flat.png"
        flat.convert("RGB").save(png)
        command = [sys.executable, str(ROOT / "scripts/graphics.py"), "convert", str(png)]
        command += ["--mode", "gime-320x16", "--size", "48x40", "--codes", CODES]
        if source.stem in BOXES:
            command += ["--box", BOXES[source.stem]]
        command += ["--label", "s", "--out", str(Path(work) / "s")]
        subprocess.run(command, check=True, capture_output=True, timeout=120)
        data = np.frombuffer((Path(work) / "s.bin").read_bytes(), dtype=np.uint8)
    return np.stack([data >> 4, data & 15], axis=1).reshape(40, 48)


def slide_line(line: list[int]) -> list[int]:
    """One line, the edge of the move first: close up, then merge equal pairs once."""
    out: list[int] = []
    mergeable = False
    for level in (v for v in line if v):
        if mergeable and out[-1] == level and level < TOP:
            out[-1] += 1
            mergeable = False
        else:
            out.append(level)
            mergeable = True
    return out + [0] * (4 - len(out))


def move(board: list[int], arrow: str) -> list[int]:
    grid = np.array(board).reshape(4, 4)
    turns = {"L": 0, "U": 1, "R": 2, "D": 3}[arrow]  # turn the edge to the left
    turned = np.rot90(grid, turns)
    moved = np.array([slide_line(list(row)) for row in turned])
    return [int(v) for v in np.rot90(moved, -turns).flatten()]


def parse_board(text: str) -> list[int]:
    return [int(c, 16) for c in text.replace("/", "")]


@cache
def boards(variant: str) -> tuple[tuple[int, ...], ...]:
    """The board at each checkpoint: one for each keys.txt line.

    A move needs exactly one arrow held that was not held at the scan before.
    The first line only seeds that history.
    """
    if variant != "keys":
        return (tuple(OPENING),) * 21
    lines = [
        line.split()
        for line in (HERE / "keys.txt").read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]
    board, previous, result = list(OPENING), "", []
    for number, (keys, written, *_) in enumerate(lines, start=1):
        held = "" if keys == "-" else "".join(k for k in keys if k in ARROWS)
        if number > 1 and len(held) == 1 and held not in previous:
            board = move(board, held)
        previous = held
        if board != parse_board(written):
            raise ValueError(f"keys.txt line {number}: the rules give {board}, not {written}")
        result.append(tuple(board))
    return tuple(result)


def picture(board: tuple[int, ...]) -> np.ndarray:
    """The whole screen as palette registers, 192 rows of 320 pixels."""
    screen = np.full((ROWS, WIDTH), BLACK, dtype=np.uint8)
    for square, level in enumerate(board):
        x0 = BOARD_X + (square % 4) * SQUARE_W
        y0 = (square // 4) * SQUARE_H
        cx, cy, cw, ch = CELL
        screen[y0 + cy : y0 + cy + ch, x0 + cx : x0 + cx + cw] = GREY
        if level:
            sx, sy, sw, sh = SPRITE
            screen[y0 + sy : y0 + sy + sh, x0 + sx : x0 + sx + sw] = sprite(level)
    return screen


def expected_screen(frame: int, variant: str = "") -> bytes:
    """Two pixels in each byte, the left pixel in the high bits (Tepolt PDF 38-39)."""
    pixels = picture(boards(variant)[frame - 1])
    return bytes((pixels[:, 0::2] << 4 | pixels[:, 1::2]).flatten())


def expected_frame(frame: int, variant: str = "", target: str = "coco3") -> np.ndarray:
    """The middle 512 samples of each 640-sample line."""
    colours = np.array(RENDERED, dtype=np.uint8)
    columns = (FULL_WIDTH_START + np.arange(CAPTURE_SAMPLES)) // 2
    return colours[picture(boards(variant)[frame - 1])[:, columns]]
