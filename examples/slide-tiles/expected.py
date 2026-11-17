"""Independent model of the slide: both screens and the picture at each flip.

Written from the board, the tile pictures, the moves and the slide rule in
README.md, not from the assembly. Each flip is a checkpoint. A move is N + 2
flips: the start, steps 1 to N, then step N on the other screen. The shown
screen holds the picture just drawn. The other screen holds the picture of
the flip before it.

Variants: "" (CG6, 4 steps), "steps8" (CG6, 8 steps) and "gime16" (GIME
320x192 with 16 colours, 4 steps, a CoCo 3 with a 6309 and 512 KiB).
"""

import numpy as np
from graphics import XROAR, XROAR_COCO3, VdgColour

ROWS = 192
SQUARE_ROWS = 48
TILE_TOP, TILE_ROWS, EDGE_ROWS = 4, 40, 4
# Colour names, in palette order for the GIME and in colour-code order for CG6.
GAP, CELL, YELLOW, RED = "gap", "cell", "yellow", "red"


class Layout:
    """Bytes per row, board start, square width, tile offset and width (bytes)."""

    def __init__(
        self,
        per_row: int,
        board: int,
        square: int,
        tile_x: int,
        tile_w: int,
        codes: dict[str, int],
        pixels_per_byte: int,
    ):
        self.per_row, self.board, self.square = per_row, board, square
        self.tile_x, self.tile_w = tile_x, tile_w
        self.codes, self.pixels_per_byte = codes, pixels_per_byte

    def byte(self, colour: str) -> int:
        """Every pixel of the byte in one colour code."""
        bits = 8 // self.pixels_per_byte
        return sum(self.codes[colour] << (bits * i) for i in range(self.pixels_per_byte))


# CG6, colour set 0: green 0, yellow 1, blue 2, red 3 (MC6847 PDF 21).
CG6 = Layout(32, 0, 8, 2, 4, {CELL: 0, YELLOW: 1, GAP: 2, RED: 3}, 4)
# GIME 320x192x16: palette registers 0-3 (Tepolt PDF 38-39, 41-42).
GIME = Layout(160, 24, 28, 2, 24, {GAP: 0, CELL: 1, YELLOW: 2, RED: 3}, 2)

# Kind, start square, end square. Squares are numbered row by row from 0.
MOVES = [
    [
        (1, 1, 0),
        (2, 3, 1),
        (1, 4, 4),
        (1, 5, 4),
        (2, 6, 5),
        (2, 7, 5),
        (2, 11, 8),
        (1, 12, 12),
        (1, 14, 12),
    ],
    [
        (1, 0, 12),
        (2, 1, 13),
        (2, 5, 13),
        (1, 2, 10),
        (2, 10, 14),
        (1, 3, 7),
        (2, 7, 11),
        (1, 15, 15),
    ],
]


def layout(variant: str) -> Layout:
    return GIME if variant == "gime16" else CG6


def steps(variant: str) -> int:
    return 8 if variant == "steps8" else 4


def empty_board(lay: Layout) -> list[list[str]]:
    """Rows of byte colours: gaps around each square, margins in the gap colour."""
    rows = []
    for y in range(ROWS):
        row = []
        for x in range(lay.per_row):
            inside = lay.board <= x < lay.board + 4 * lay.square
            column = (x - lay.board) % lay.square
            gap_row = y % SQUARE_ROWS in (0, 1, SQUARE_ROWS - 2, SQUARE_ROWS - 1)
            row.append(CELL if inside and 0 < column < lay.square - 1 and not gap_row else GAP)
        rows.append(row)
    return rows


def tile_origin(lay: Layout, square: int) -> tuple[int, int]:
    return lay.board + (square % 4) * lay.square + lay.tile_x, (
        square // 4
    ) * SQUARE_ROWS + TILE_TOP


def toward(start: int, end: int, k: int, n: int) -> int:
    """k/N of the way from start to end, rounded toward the start."""
    return start + (end - start) * k // n if end >= start else start - (start - end) * k // n


def draw_tile(rows: list[list[str]], lay: Layout, kind: int, x: int, y: int) -> None:
    edge, inside = (RED, YELLOW) if kind == 1 else (YELLOW, RED)
    for i in range(TILE_ROWS):
        for j in range(lay.tile_w):
            on_edge = i < EDGE_ROWS or i >= TILE_ROWS - EDGE_ROWS or j in (0, lay.tile_w - 1)
            rows[y + i][x + j] = edge if on_edge else inside


def picture(variant: str, move: int, k: int) -> list[list[str]]:
    """Step k of a move (0 is the start): the tiles that stay, then the moving
    tiles in list order, each k/N of the way. No tiles overlap at the start."""
    lay, n = layout(variant), steps(variant)
    rows = empty_board(lay)
    tiles = MOVES[move]
    staying = [t for t in tiles if t[1] == t[2]]
    moving = [t for t in tiles if t[1] != t[2]]
    for kind, start, end in staying + moving:
        (x0, y0), (x1, y1) = tile_origin(lay, start), tile_origin(lay, end)
        draw_tile(rows, lay, kind, toward(x0, x1, k, n), toward(y0, y1, k, n))
    return rows


def flip_picture(variant: str, flip: int) -> list[list[str]]:
    """The picture that flip number `flip` (from 1) shows."""
    per_move = steps(variant) + 2
    index, j = divmod(flip - 1, per_move)
    return picture(variant, index % len(MOVES), min(j, steps(variant)))


def screen_bytes(variant: str, flip: int) -> bytes:
    lay = layout(variant)
    return bytes(lay.byte(c) for row in flip_picture(variant, flip) for c in row)


# Where each screen is in the snapshot. Screen A is shown after an even flip.
# CG6: CPU $0400 and $2400. BASIC's map puts CPU $xxxx at physical $7xxxx on
# a 512 KiB CoCo 3 and at $1xxxx on a 128 KiB one (Tepolt PDF 56 and 29).
# GIME16: physical $00000 and $08000.
OFFSETS = {"coco1": 0, "coco2": 0, "coco2b": 0, "coco3": 0x10000, "coco3-6309": 0x70000}


def screen_address(variant: str, target: str, screen: int) -> int:
    if variant == "gime16":
        return (0x00000, 0x08000)[screen]
    return OFFSETS[target] + (0x0400, 0x2400)[screen]


def verify_ram(ram: bytes, symbols: dict[str, int], frame: int, variant: str, target: str) -> None:
    """The shown screen holds this flip's picture; the other, the flip before."""
    size = layout(variant).per_row * ROWS
    for flip, screen in ((frame, frame % 2), (frame - 1, (frame - 1) % 2)):
        if flip < 1:
            continue
        at = screen_address(variant, target, screen)
        if ram[at : at + size] != screen_bytes(variant, flip):
            raise ValueError(f"The screen at ${at:05X} does not hold the picture of flip {flip}.")


# Measured, not sourced: XRoar's rendered colour of each GIME code through
# coco.py's capture, as in examples/gime-graphics.
GIME_CODES = {GAP: 0x00, CELL: 0x12, YELLOW: 0x24, RED: 0x16}
GIME_RENDERED = {0x00: (20, 20, 20), 0x12: (71, 145, 5), 0x24: (255, 200, 46), 0x16: (255, 79, 75)}
# A 160-byte line is 640 samples, two for each pixel. XRoar 1.13.1 centres
# the 512-sample capture on the 640-sample line (update_viewport in
# src/vo_render.c), so the capture starts at sample 64. This check measures
# it: with 62, the rendered check fails by two samples.
FULL_WIDTH_START, CAPTURE = 64, 512
VDG_NAMES = {
    CELL: VdgColour.GREEN,
    YELLOW: VdgColour.YELLOW,
    GAP: VdgColour.BLUE,
    RED: VdgColour.RED,
}
# A CG6 pixel spans 2 half-clocks and coco.py takes 2 samples for each, so
# one byte (4 pixels) spans 16 samples (as in examples/first-screen).
SAMPLES_PER_CG6_BYTE = 16


def expected_frame(frame: int, variant: str, target: str) -> np.ndarray:
    """The rendered 512x192 picture of the shown screen."""
    rows = flip_picture(variant, frame)
    if variant == "gime16":
        colours = {c: GIME_RENDERED[GIME_CODES[c]] for c in GIME_CODES}
        columns = [(FULL_WIDTH_START + s) * 320 // 640 // 2 for s in range(CAPTURE)]
    else:
        palette = XROAR_COCO3 if target.startswith("coco3") else XROAR
        colours = {c: palette.rgb(name, 0) for c, name in VDG_NAMES.items()}
        columns = [s // SAMPLES_PER_CG6_BYTE for s in range(CAPTURE)]
    return np.array([[colours[row[x]] for x in columns] for row in rows], dtype=np.uint8)
