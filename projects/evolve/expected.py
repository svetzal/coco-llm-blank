"""Independent model of Evolve: its screens and its rules.

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
from font import DIGIT_INK, GLYPHS, WORDS

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
# The scores in the black margins: "SCORE" and its 5 digits at x 4; "BEST"
# at x 280 and its 5 digits at x 276. Labels at row 8, digits at row 20.
SCORE_LABEL, BEST_LABEL, SCORE_DIGITS, BEST_DIGITS = 4, 280, 4, 276
LABEL_ROW, DIGIT_ROW = 8, 20

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


def slide_line(line: list[int]) -> tuple[list[int], int, int]:
    """One line, the edge of the move first: close up, then merge equal pairs once.

    Each merge scores 2 to the power of the new level. Also give the highest
    level that a merge made (0: no merge).
    """
    out: list[int] = []
    points = top = 0
    mergeable = False
    for level in (v for v in line if v):
        if mergeable and out[-1] == level:
            out[-1] += 1
            points += 2 ** out[-1]
            top = max(top, out[-1])
            mergeable = False
        else:
            out.append(level)
            mergeable = True
    return out + [0] * (4 - len(out)), points, top


def move(board: list[int], arrow: str) -> tuple[list[int], int, int]:
    grid = np.array(board).reshape(4, 4)
    turns = {"L": 0, "U": 1, "R": 2, "D": 3}[arrow]  # turn the edge to the left
    turned = np.rot90(grid, turns)
    lines = [slide_line(list(row)) for row in turned]
    moved = np.array([line for line, _, _ in lines])
    points = sum(p for _, p, _ in lines)
    top = max(t for _, _, t in lines)
    return [int(v) for v in np.rot90(moved, -turns).flatten()], points, top


# The sounds of the README, as notes of (Hz, ms). A merge to level L plays
# note L-2 of the C major scale from C5. A level not seen before in this game
# plays notes L-2, L and L+2 of the scale instead.
SCALE = [523, 587, 659, 698, 784, 880, 988, 1047, 1175, 1319, 1397, 1568, 1760, 1976]
WIN_SOUND = ((1047, 80), (1319, 80), (1568, 80), (2093, 240))
LOSE_SOUND = ((784, 150), (659, 150), (523, 300))


def merge_sound(level: int, new: bool) -> tuple[tuple[int, int], ...]:
    note = level - 2
    if new:
        return ((SCALE[note], 40), (SCALE[note + 2], 40), (SCALE[note + 4], 80))
    return ((SCALE[note], 40),)


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
        self.score = self.best = 0
        self.sounds: list[tuple[tuple[int, int], ...]] = []  # each sound started
        if layout is None:
            self.board, self.phase = [0] * 16, "T"
        else:
            self.board, self.phase = list(layout), "P"
        self.seen = max(self.board)  # the highest level seen in this game

    def spawn(self) -> None:
        self.seed = step(self.seed)
        empty = [i for i, v in enumerate(self.board) if not v]
        if empty:
            k = 0 if self.first_empty else (self.seed & 0xFF) % len(empty)
            self.board[empty[k]] = 1

    def new_game(self) -> None:
        self.board, self.phase, self.score = [0] * 16, "P", 0
        self.spawn()
        self.spawn()
        self.seen = max(self.board)
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
            after, points, top = move(self.board, arrows)
            if after != self.board:
                self.board = after
                self.score += points
                self.spawn()
                self.judge()
                self.best = max(self.best, self.score)
                self.changed = True
                self.chime(top)

    def chime(self, top: int) -> None:
        """The sound of a move: a loss, a win, a new creature, a merge or none."""
        if self.phase == "L":
            self.sounds.append(LOSE_SOUND)
        elif self.phase == "W":
            self.sounds.append(WIN_SOUND)
        elif top:
            self.sounds.append(merge_sound(top, new=top > self.seen))
            self.seen = max(self.seen, top)

    def scene(self) -> tuple:
        """What the picture shows: the title, or the board and any banner."""
        if self.phase == "T":
            return ("T",)
        banner = self.phase if self.phase in "WL" else ""
        return ("B", tuple(self.board), banner, self.score, self.best)


def parse_board(text: str) -> list[int]:
    return [int(c, 16) for c in text.replace("/", "")]


class Screens(NamedTuple):
    """The two screens at one checkpoint: what each holds, and which is shown."""

    held: tuple[tuple | None, tuple | None]  # None: black
    shown: int  # 0 screen A, 1 screen B
    phase: str
    sounds: tuple  # every sound started up to this scan


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
            board, phase, score = words[1:4] if len(words) > 3 else (None, None, None)
            given = (parse_board(board), phase, int(score)) if board else None
            if given and given != (game.board, game.phase, game.score):
                raise ValueError(
                    f"{script} line {number}: the rules give {game.board} {game.phase} "
                    f"{game.score}, not {board} {phase} {score}"
                )
        result.append(Screens((held[0], held[1]), shown, game.phase, tuple(game.sounds)))
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


def put_word(screen: np.ndarray, label: str, y: int, x: int | None = None) -> None:
    """A word at column x, or centred at an even column (two pixels in a byte)."""
    pixels = word(label)
    if x is None:
        x = 2 * (80 - pixels.shape[1] // 4)
    screen[y : y + pixels.shape[0], x : x + pixels.shape[1]] = pixels


def put_number(screen: np.ndarray, value: int, x: int) -> None:
    """The five low digits, with leading zeros, from column x at the digit row."""
    for place, digit in enumerate(f"{value % 100000:05d}"):
        marks = np.array([[c == "#" for c in row] for row in GLYPHS[digit]], dtype=np.uint8)
        left = x + 8 * place
        screen[DIGIT_ROW : DIGIT_ROW + 8, left : left + 8] = marks * DIGIT_INK


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
    _, board, banner, score, best = scene
    put_word(screen, "score", LABEL_ROW, SCORE_LABEL)
    put_word(screen, "best", LABEL_ROW, BEST_LABEL)
    put_number(screen, score, SCORE_DIGITS)
    put_number(screen, best, BEST_DIGITS)
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


# The sound timer: one count is 4 / 14,318,180 s with the fast input, and a
# period is the reload value plus 2 counts on the 1986 GIME (the sound guide,
# guidance/techniques/sound.md). Each period is one edge: half a wave.
COUNT_HZ = 14_318_180 / 4
SILENCE_MS = 10  # a longer gap between edges ends a sound
PITCH_TOLERANCE = 0.01
# The envelope of the README: the amplitude in each eighth of a note, in DAC
# units. The last step lasts to the end of the note.
ENVELOPE = (0x18, 0x20, 0x1C, 0x18, 0x14, 0x10, 0x0C, 0x08)
STEP_TOLERANCE = 0.1


def timer_note(hz: int, ms: int) -> tuple[float, int, int]:
    """The frequency that the timer makes for a note, its number of edges, and
    the number of edges in each step of the envelope."""
    reload = int(COUNT_HZ / 2 / hz) - 2
    return COUNT_HZ / 2 / (reload + 2), 2 * hz * ms // 1000, hz * ms // 4000


def amplitude(edge: int, per_step: int) -> int:
    return ENVELOPE[min(edge // per_step, len(ENVELOPE) - 1)]


class Edges(NamedTuple):
    at: np.ndarray  # sample numbers
    size: np.ndarray  # the change of the mixer output


def sound_edges(samples: np.ndarray) -> Edges:
    """The DAC edges of the sounds.

    Changes at most 8 samples apart are one edge: the highest note has an
    edge every 21 samples, and the end of a sound puts the DAC at rest just
    after its last edge (4 samples after it, measured). The first edge is the program's setup, which puts
    the DAC at rest. It is not part of a sound.
    """
    values = samples.astype(int)
    changes = np.flatnonzero(np.diff(values))
    if len(changes) == 0:
        return Edges(changes, changes)
    groups = np.split(changes, np.flatnonzero(np.diff(changes) > 8) + 1)
    at = np.array([g[0] for g in groups])
    size = np.array([abs(values[g[-1] + 1] - values[g[0]]) for g in groups])
    return Edges(at[1:], size[1:])


def heard_notes(edges: Edges, notes, rate: int, short: bool) -> tuple[list, list] | None:
    """The pitch of each note, and the steps of the edges inside each note.

    Give None if the edges do not fit the notes. Each note must have its number
    of edges and its pitch within 1%. If short is true, the sound may stop
    early: the edges may be only its start. A step is (the measured change,
    the change that the envelope gives). The first edge of a note leaves the
    note before it, and the last edge of a sound goes to rest. They are not
    compared.
    """
    heard, steps = [], []
    first = 0
    for number, (hz, ms) in enumerate(notes):
        pitch, count, per_step = timer_note(hz, ms)
        part = edges.at[first : first + count]
        if len(part) > 2:
            hz_heard = rate / 2 / ((part[-1] - part[0]) / (len(part) - 1))
            if abs(hz_heard - pitch) > PITCH_TOLERANCE * pitch:
                return None
            heard.append(round(float(hz_heard), 1))
        inner = len(part) - 1 if number == len(notes) - 1 else len(part)
        for edge in range(1, inner):
            given = amplitude(edge - 1, per_step) + amplitude(edge, per_step)
            steps.append((int(edges.size[first + edge]), given))
        first += len(part)
        if len(part) < count:
            break
    if first != len(edges.at) or (not short and first != sum(timer_note(*n)[1] for n in notes)):
        return None
    return heard, steps


def burst_notes(burst: Edges, sounds, rate: int, playing: bool) -> tuple[list, list] | None:
    """One burst of edges: one sound, or a sound that the next sound cut short.

    The last sound in the burst may still play at the end of the recording.
    """
    if len(sounds) == 1:
        return heard_notes(burst, sounds[0], rate, short=playing)
    for cut in range(1, len(burst.at)):
        before = heard_notes(Edges(burst.at[:cut], burst.size[:cut]), sounds[0], rate, True)
        if before is None:
            continue
        after = heard_notes(Edges(burst.at[cut:], burst.size[cut:]), sounds[1], rate, playing)
        if after is not None:
            return before[0] + after[0], before[1] + after[1]
    return None


def verify_sound(sound, frame: int, variant: str) -> dict[str, object]:
    """Every sound started up to this scan, note by note, in the mixer output.

    The edges fall into bursts separated by silence. A burst is one sound, or
    a sound that the next move cut short and the sound of that move. Each note
    must have its number of edges and its pitch within 1%. The last sound may
    still play at the snapshot: the recording can end in it.

    The size of each edge inside a note follows the envelope. The mixer's
    scale is not known, so the check takes the median ratio of the measured
    to the given change as the scale. Each edge must be within 10% of it.
    """
    expected = list(states(variant)[frame - 1].sounds)
    edges = sound_edges(sound.samples)
    gap = SILENCE_MS * sound.rate // 1000
    splits = np.flatnonzero(np.diff(edges.at) > gap) + 1
    bursts = (
        [Edges(a, z) for a, z in zip(np.split(edges.at, splits), np.split(edges.size, splits))]
        if len(edges.at)
        else []
    )
    heard: list[float] = []
    steps: list[tuple[int, int]] = []
    cuts = 0
    for number, burst in enumerate(bursts, start=1):
        playing = number == len(bursts) and len(sound.samples) - burst.at[-1] < gap
        for size in (1, 2):
            sounds = expected[:size]
            fit = burst_notes(burst, sounds, sound.rate, playing) if len(sounds) == size else None
            if fit is not None:
                break
        else:
            raise ValueError(
                f"Scan {frame}: sound {number} in the mixer output ({len(burst.at)} edges) "
                f"does not fit the next expected sounds {expected[:2]}."
            )
        heard += fit[0]
        steps += fit[1]
        cuts += size - 1
        del expected[:size]
    if expected:
        raise ValueError(
            f"Scan {frame}: {len(expected)} expected sounds are not in the mixer output."
        )
    result = {"frame": frame, "sounds": len(bursts) + cuts, "cut_short": cuts, "notes_hz": heard}
    if not steps:
        return result
    ratios = np.array([measured / given for measured, given in steps])
    scale = float(np.median(ratios))
    worst = float(np.abs(ratios / scale - 1).max())
    if worst > STEP_TOLERANCE:
        raise ValueError(
            f"Scan {frame}: an edge differs from the envelope by {worst:.0%} "
            f"({len(steps)} edges, scale {scale:.1f} for each DAC unit)."
        )
    return result | {"envelope_edges": len(steps), "mixer_per_dac_unit": round(scale, 2)}
