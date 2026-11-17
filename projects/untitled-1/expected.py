"""Independent model of Evolve (untitled-1): its screens and its rules.

Written from the layout rules and the game rules in the README, not from the
assembly's output. The key policy and the slide rules are modelled here, and
the model must agree with the boards written by hand in the key scripts.

The creature pixels come from the source pictures in art/creatures/ by the
model's own conversion, not from bytes that the build or the emulator made.
The letters come from the drawings in font.py, scaled here by the model's own
route. The model therefore checks placement, packing, the page crossings of
the screen window, the two screens and the display setup. It trusts
scripts/graphics.py, which has its own tests, for the conversion.
"""

import subprocess
import sys
import tempfile
from functools import cache
from pathlib import Path
from typing import NamedTuple

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from font import GLYPHS, WORDS

WIDTH, ROWS = 320, 192
SQUARE_W, SQUARE_H = 56, 48  # pixels; square on the display
BOARD_X = 48  # (320 - 4 * 56) / 2
CELL = (2, 2, 52, 44)  # grey cell inside a square: x, y, width, height
SPRITE = (4, 4, 48, 40)  # creature inside a square
BLACK, GREY, WHITE = 0, 1, 3  # palette registers
SCREEN_BYTES = 160 * 192
SCREENS = (0x00000, 0x08000)  # physical: screen A, screen B
# The title: the grey backdrop (x, y, width, height), the creatures' places
# (x, y in pixels, levels 1 to 11) and the rows of the words.
BACKDROP = (8, 44, 304, 104)
PHOTO = [(40 + 48 * i, 100) for i in range(5)] + [(16 + 48 * i, 52) for i in range(6)]
TITLE_ROW, PRESS_ROW = 12, 164
# The banner: a white frame and a black box (x, y, width, height).
FRAME, BOX = (56, 72, 208, 48), (58, 74, 204, 44)
RESULT_ROW, BANNER_PRESS_ROW = 80, 104

TOP = 11  # the human: it wins the game
ARROWS = "UDLR"
SEED = 0x7A35
FRAMES = 21
# Each build: its fixed layout (None: a new game) and whether a new microbe
# goes in the first empty square (True) or where the generator says.
BUILDS = {
    "": ("", None),
    "play": ("play.txt", None),
    "rules": ("keys.txt", [1, 1, 1, 1, 1, 1, 2, 0, 0, 3, 0, 3, 0, 2, 2, 2]),
    "win": ("win.txt", [0] * 12 + [10, 10, 0, 0]),
    "lose": ("lose.txt", [1, 2, 1, 2, 2, 1, 2, 1, 3, 4, 3, 4, 3, 1, 3, 0]),
}

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
# The colour of register 1 in each phase: grey in play, then the win code $12
# (register 9) or the loss code $07 (register 14).
PHASE_RGB = {"T": RENDERED[GREY], "P": RENDERED[GREY], "W": RENDERED[9], "L": RENDERED[14]}
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
        if mergeable and out[-1] == level:
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


def step(seed: int) -> int:
    """The 16-bit xorshift generator of the README: shifts 7, 9 and 8."""
    seed ^= (seed << 7) & 0xFFFF
    seed ^= seed >> 9
    return seed ^ ((seed << 8) & 0xFFFF)


class Game:
    """The game as the README states it, one scan at a time."""

    def __init__(self, layout: list[int] | None, first_empty: bool) -> None:
        self.first_empty = first_empty
        self.seed = SEED
        self.previous = ""
        self.changed = False
        if layout is None:
            self.board, self.phase = [0] * 16, "T"
        else:
            self.board, self.phase = list(layout), "P"

    def spawn(self) -> None:
        self.seed = step(self.seed)
        empty = [i for i, v in enumerate(self.board) if not v]
        if empty:
            k = 0 if self.first_empty else (self.seed & 0xFF) % len(empty)
            self.board[empty[k]] = 1

    def new_game(self) -> None:
        self.board, self.phase = [0] * 16, "P"
        self.spawn()
        self.spawn()
        self.changed = True

    def judge(self) -> None:
        grid = np.array(self.board).reshape(4, 4)
        if TOP in self.board:
            self.phase = "W"
        elif 0 not in self.board and not (
            (grid[:, 1:] == grid[:, :-1]).any() or (grid[1:] == grid[:-1]).any()
        ):
            self.phase = "L"

    def scan(self, keys: str, first: bool) -> None:
        self.changed = False
        held = "" if keys == "-" else keys
        pressed = "".join(k for k in held if k not in self.previous)
        self.previous = held
        if first:
            return  # the startup sample only seeds the history
        self.seed = step(self.seed)
        if self.phase != "P":
            if "F" in pressed:
                self.new_game()
            return
        arrows = "".join(k for k in held if k in ARROWS)
        if len(arrows) == 1 and arrows in pressed:
            after = move(self.board, arrows)
            if after != self.board:
                self.board = after
                self.spawn()
                self.judge()
                self.changed = True

    def scene(self) -> tuple:
        """What the picture shows: the title, or the board and any banner."""
        if self.phase == "T":
            return ("T",)
        return ("B", tuple(self.board), self.phase if self.phase in "WL" else "")


def parse_board(text: str) -> list[int]:
    return [int(c, 16) for c in text.replace("/", "")]


class Screens(NamedTuple):
    """The two screens at one checkpoint: what each holds, and which is shown."""

    held: tuple[tuple | None, tuple | None]  # None: black
    shown: int  # 0 screen A, 1 screen B
    phase: str


@cache
def states(variant: str) -> tuple[Screens, ...]:
    """The screens at each checkpoint, one for each scan.

    The program draws a new picture into the screen that is not shown, then
    shows it. It does this once at the start and after each change. Scans
    after the end of the script hold no keys. Where the script gives a board
    and a phase written by hand, the model must agree with them.
    """
    script, layout = BUILDS[variant]
    lines: list[list[str]] = []
    if script:
        lines = [
            line.split()
            for line in (HERE / script).read_text().splitlines()
            if line.strip() and not line.startswith("#")
        ]
    lines += [["-"]] * (FRAMES - len(lines))
    game = Game(layout, first_empty=layout is not None)
    held: list[tuple | None] = [None, game.scene()]  # the start draws screen B
    shown = 1
    result = []
    for number, words in enumerate(lines, start=1):
        game.scan(words[0], first=number == 1)
        if game.changed:
            shown = 1 - shown
            held[shown] = game.scene()
        if layout is not None:
            board, phase = words[1:3] if len(words) > 2 else (None, None)
            if board and (parse_board(board) != game.board or phase != game.phase):
                raise ValueError(
                    f"{script} line {number}: the rules give {game.board} {game.phase}, "
                    f"not {board} {phase}"
                )
        result.append(Screens((held[0], held[1]), shown, game.phase))
    return tuple(result)


@cache
def word(label: str) -> np.ndarray:
    """The palette registers of one word of font.py, at its scale."""
    _, text, scale, ink = next(w for w in WORDS if w[0] == label)
    marks = np.array(
        [[[c == "#" for c in GLYPHS[letter][row]] for letter in text] for row in range(8)]
    )
    small = marks.reshape(8, 8 * len(text))
    return np.kron(small, np.ones((scale, scale), dtype=bool)).astype(np.uint8) * ink


def put_word(screen: np.ndarray, label: str, y: int) -> None:
    """A word centred on the screen, at an even column (two pixels in a byte)."""
    pixels = word(label)
    x = 2 * (80 - pixels.shape[1] // 4)
    screen[y : y + pixels.shape[0], x : x + pixels.shape[1]] = pixels


def box(screen: np.ndarray, area: tuple[int, int, int, int], value: int) -> None:
    x, y, w, h = area
    screen[y : y + h, x : x + w] = value


@cache
def picture(scene: tuple | None) -> np.ndarray:
    """One screen as palette registers, 192 rows of 320 pixels."""
    screen = np.full((ROWS, WIDTH), BLACK, dtype=np.uint8)
    if scene is None:
        return screen
    if scene[0] == "T":
        box(screen, BACKDROP, GREY)
        for level, (x, y) in enumerate(PHOTO, start=1):
            screen[y : y + 40, x : x + 48] = sprite(level)
        put_word(screen, "evolve", TITLE_ROW)
        put_word(screen, "press", PRESS_ROW)
        return screen
    _, board, banner = scene
    for square, level in enumerate(board):
        x0 = BOARD_X + (square % 4) * SQUARE_W
        y0 = (square // 4) * SQUARE_H
        cx, cy, cw, ch = CELL
        screen[y0 + cy : y0 + cy + ch, x0 + cx : x0 + cx + cw] = GREY
        if level:
            sx, sy, sw, sh = SPRITE
            screen[y0 + sy : y0 + sy + sh, x0 + sx : x0 + sx + sw] = sprite(level)
    if banner:
        box(screen, FRAME, WHITE)
        box(screen, BOX, BLACK)
        put_word(screen, "win" if banner == "W" else "over", RESULT_ROW)
        put_word(screen, "press", BANNER_PRESS_ROW)
    return screen


def packed(scene: tuple | None) -> bytes:
    """Two pixels in each byte, the left pixel in the high bits (Tepolt PDF 38-39)."""
    pixels = picture(scene)
    return bytes((pixels[:, 0::2] << 4 | pixels[:, 1::2]).flatten())


def verify_ram(ram: bytes, symbols: dict[str, int], frame: int, variant: str, target: str) -> None:
    """Each screen holds the picture of the model: the shown one and the hidden one."""
    state = states(variant)[frame - 1]
    for number, (start, scene) in enumerate(zip(SCREENS, state.held, strict=True)):
        actual = ram[start : start + SCREEN_BYTES]
        expected = packed(scene)
        if actual != expected:
            first = next(i for i in range(SCREEN_BYTES) if actual[i] != expected[i])
            differ = sum(a != b for a, b in zip(actual, expected, strict=True))
            name = "AB"[number] + (" (shown)" if number == state.shown else " (hidden)")
            raise ValueError(
                f"screen {name}: {differ} of {SCREEN_BYTES} bytes differ; first at "
                f"${start + first:05X}: expected ${expected[first]:02X}, found ${actual[first]:02X}"
            )


def expected_frame(frame: int, variant: str = "", target: str = "coco3") -> np.ndarray:
    """The middle 512 samples of each 640-sample line of the shown screen."""
    state = states(variant)[frame - 1]
    colours = np.array(RENDERED, dtype=np.uint8)
    colours[GREY] = PHASE_RGB[state.phase]
    columns = (FULL_WIDTH_START + np.arange(CAPTURE_SAMPLES)) // 2
    return colours[picture(state.held[state.shown])[:, columns]]
