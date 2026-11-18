"""Independent model of Arena Blaster: the rules for each frame, the arena and the sprites.

Written from the rules and the design in README.md and the art in sprites.txt. It does
not use main.asm, assets.py, the assembled bytes or a captured snapshot. It reads the
key script and simulates each frame. Then it draws each screen pixel by pixel and packs
the pixels itself.

Frame N is drawn into the hidden screen and then shown. Odd frames are at $2400 and even
frames at $0400. The model keeps both screens. A new screen (the arena, the title or the
initials) goes into the hidden screen, and into the other screen at the start of the
next frame that draws into it. Then each frame draws its part into the hidden screen:
in a game the whole picture, on the title the prompt, for the initials the letters and
the cursor.
"""

import copy
import functools
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from graphics import MODES, XROAR, render

HERE = Path(__file__).resolve().parent
WIDTH, HEIGHT = 128, 192
# CG6 colour set 0 codes (MC6847 PDF 21 Figure 22).
GREEN, YELLOW, BLUE, RED = 0, 1, 2, 3
CODES = {"G": GREEN, "Y": YELLOW, "B": BLUE, "R": RED}
SCREENS = {1: 0x2400, 0: 0x0400}  # frame number % 2
SCREEN_BYTES = 6144
# The arena from README.md: walls on rows 12 and 187 and pixel columns 3 and 124.
WALL_TOP, WALL_BOTTOM, WALL_LEFT, WALL_RIGHT = 12, 187, 3, 124
MIN_X, END_X, MIN_Y, END_Y = 4, 124, 13, 187
PLAYER_W, PLAYER_H = 6, 10
START = (61, 95)
SHOT_SLOTS, SHOT_DELAY = 10, 2
# Movement keys and shoot keys: (dx, dy) for each key letter in the key script.
MOVE = {"W": (0, -1), "S": (0, 1), "A": (-1, 0), "D": (1, 0)}
SHOOT = {"O": (0, -1), "L": (0, 1), "K": (-1, 0), ";": (1, 0)}
# (row, column) of each script key in the matrix: Tandy PDF 75. C is the
# wrong-key control.
MATRIX = {
    "A": (0, 1),
    "D": (0, 4),
    "C": (0, 3),
    "K": (1, 3),
    "L": (1, 4),
    "O": (1, 7),
    "S": (2, 3),
    "W": (2, 7),
    ";": (5, 3),
}
# The scanner's labels in RAM that the check compares.
STATE_FIELDS = ("px", "py", "delay")
SLOT_SIZE = 11  # on, x, y, vx, vy, sprite (2), maxx, maxy, w, h
# Enemies (README.md "Levels and enemies").
ENEMY_SLOTS, ENEMY_SIZE = 24, 4  # type, x, y, tick
ENEMY_W, ENEMY_H = 6, 10
GRUNT, HUNTER, SHOOTER = 1, 2, 3
PERIOD = {GRUNT: 2, HUNTER: 1, SHOOTER: 3}
SPRITE = {GRUNT: "grunt", HUNTER: "hunter", SHOOTER: "shooter"}
# Enemy bullets (README.md "Shooters").
BULLET_SLOTS, BULLET_SIZE = 4, 5  # on, x, y, vx, vy
BULLET_W, BULLET_H, BULLET_VX, BULLET_VY = 3, 4, 3, 6
SEED = 0xACE1
# Test-harness controls of each variant (coco.toml), and its first level.
CONTROLS = {
    "": set(),
    "moves": {"SKIP_TITLE", "NO_READY", "NO_ENEMIES"},
    "hit": {"SKIP_TITLE", "NO_READY", "FIXED_ENEMIES", "STILL"},
    "touch": {"SKIP_TITLE", "FIXED_ENEMIES"},
    "hunter": {"SKIP_TITLE", "NO_READY", "NO_ENEMIES", "HUNTER_SOON", "NO_DEATH"},
    "level1": {"SKIP_TITLE"},
    "level3": {"SKIP_TITLE", "NO_DEATH"},
    "level5": {"SKIP_TITLE", "NO_DEATH"},
    "shooter": {"SKIP_TITLE", "NO_READY", "ONE_SHOOTER"},
    "pickups": {"SKIP_TITLE", "NO_READY", "FIXED_ENEMIES", "STILL"},
    "bomb": {"SKIP_TITLE", "NO_READY", "FIXED_ENEMIES", "STILL"},
    "double": {"SKIP_TITLE", "NO_READY", "NO_ENEMIES"},
    "spread": {"SKIP_TITLE", "NO_READY", "NO_ENEMIES"},
    "star": {"SKIP_TITLE", "NO_READY", "NO_ENEMIES"},
    "level10": {"SKIP_TITLE"},
    "slow": {"SKIP_TITLE", "NO_READY", "NO_ENEMIES"},
    "heavy": {"SKIP_TITLE", "NO_READY", "NO_ENEMIES"},
    "blitz": {"SKIP_TITLE", "NO_READY", "FIXED_ENEMIES", "NO_DEATH"},
    "level8": {"SKIP_TITLE", "NO_DEATH"},
    "jinxdrop": {"SKIP_TITLE", "NO_READY", "FIXED_ENEMIES", "STILL"},
    "demo": {"DEMO_SOON"},
    "demoshoot": {"DEMO_SOON"},
    "demohunter": {"DEMO_SOON"},
    "demoshooter": {"DEMO_SOON"},
    "demopoints": {"DEMO_SOON"},
    "demodouble": {"DEMO_SOON"},
    "demospread": {"DEMO_SOON"},
    "demostar": {"DEMO_SOON"},
    "demobomb": {"DEMO_SOON"},
    "demoslow": {"DEMO_SOON"},
    "demoheavy": {"DEMO_SOON"},
    "demoblitz": {"DEMO_SOON"},
    "over": {"SKIP_TITLE", "NO_READY"},
    "scores": {"NO_READY", "FIXED_ENEMIES"},
}
START_LEVEL = {"level3": 3, "level5": 5, "level10": 10, "pickups": 4, "level8": 8, "jinxdrop": 8}
# Things to collect (README.md "Things to collect").
PK_POINTS, PK_DOUBLE, PK_SPREAD, PK_STAR, PK_BOMB = 1, 2, 3, 4, 5
PK_SLOW, PK_HEAVY, PK_BLITZ = 6, 7, 8  # jinxes
PICKUP_SPRITE = {
    1: "pk_points",
    2: "pk_double",
    3: "pk_spread",
    4: "pk_star",
    5: "pk_bomb",
    6: "pk_slow",
    7: "pk_heavy",
    8: "pk_blitz",
}
PICKUP_W, PICKUP_H = 6, 7
PICKUP_LEVEL, BOMB_LEVEL = 4, 6
PICKUP_FRAMES, BLINK_FRAMES = 150, 60
BOMB_X, BOMB_Y = 40, 60
DROP_ORDER = [
    PK_POINTS,
    PK_DOUBLE,
    PK_SLOW,
    PK_BOMB,
    PK_SPREAD,
    PK_HEAVY,
    PK_POINTS,
    PK_STAR,
    PK_BOMB,
    PK_BLITZ,
    PK_DOUBLE,
]
JINX_LEVEL, JINX_TIME, BLITZ_FRAMES, BLITZ_HUNTERS = 8, 150, 60, 3
JINX_HINT = ("SOME GIFTS BITE", 8)
# The band: the names at byte columns 8 and 17, bars of 6 bytes on rows 9-10.
NAME = {
    PK_DOUBLE: "DOUBLE",
    PK_SPREAD: "SPREAD",
    PK_STAR: "STAR",
    PK_SLOW: "SLOW",
    PK_HEAVY: "HEAVY",
    PK_BLITZ: "BLITZ",
}
NAME_GIFT, NAME_JINX, BAR_ROW, BAR_BYTES, GIFT_STEP, JINX_STEP = 8, 17, 9, 6, 50, 25
# The 8 directions in turn from up, clockwise, as (dx, dy).
RING = [(0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1)]
SHOTS_OF = {0: 1, PK_DOUBLE: 2, PK_SPREAD: 4, PK_STAR: 8}
DROP_EVERY = {"pickups": 1, "jinxdrop": 1}
FIRST_DROP = {"jinxdrop": 2}
FIRST_POWER = {"double": PK_DOUBLE, "spread": PK_SPREAD, "star": PK_STAR, "slow": PK_SPREAD}
POWER_TIME = {"double": 100, "spread": 100, "star": 100}
FIXED_PICKUP = {"bomb": PK_BOMB, "blitz": PK_BLITZ}
FIRST_JINX = {"slow": PK_SLOW, "heavy": PK_HEAVY}
START_LIVES = {"over": 1, "scores": 1}
START_SCORE = {"hit": 990, "scores": 5000}
# Score and lives (README.md "Score and lives").
POINTS = {GRUNT: 10, HUNTER: 50, SHOOTER: 30}
EXTRA_EVERY = 1000
LIVES = 3
DYING_FRAMES, OVER_FRAMES = 45, 90
HUD_ROW, ICONS = 3, 6
SCRIPTS = {
    "moves": "moves.txt",
    "hit": "hit.txt",
    "scores": "scores.txt",
    "shooter": "shooter.txt",
    "pickups": "pickups.txt",
    "bomb": "bomb.txt",
    "jinxdrop": "pickups.txt",
    "double": "powers.txt",
    "spread": "powers.txt",
    "star": "powers.txt",
    "slow": "jinxes.txt",
    "heavy": "jinxes.txt",
    "blitz": "blitz.txt",
    "demoshoot": "demoshoot.txt",
}
# Title and high scores (README.md "Title and high scores").
TITLE, PLAY, ENTRY = 0, 1, 2
TABLE = [
    (10000, "ZAP"),
    (9000, "ACE"),
    (8000, "MAX"),
    (7000, "JET"),
    (6000, "SKY"),
    (5000, "REX"),
    (4000, "ION"),
    (3000, "VOX"),
    (2000, "KIT"),
    (1000, "DOT"),
]
REPEAT_FIRST, REPEAT_NEXT = 12, 4
NO_RANK = 0xFF
# The first levels (README.md "Levels and enemies"): grunts, frames until the first
# hunter, frames between hunters (0 = no hunters), the hint and its byte column,
# shooters, frames between bullets (0 = no bullets).
TEACH = {
    1: (4, 0, 0, "SHOOT THE GRUNTS", 8, 0, 0),
    2: (8, 0, 0, "HOLD TWO KEYS FOR DIAGONALS", 2, 0, 0),
    3: (6, 60, 240, "HUNTERS ARE FAST", 8, 0, 0),
    4: (10, 210, 210, "COLLECT THE POWER UPS", 5, 0, 0),
    5: (12, 180, 180, "SHOOTERS FIRE BACK", 7, 2, 60),
    6: (13, 150, 150, "BOMBS CLEAR THE AREA", 6, 3, 36),
}
READY_FRAMES = 60
# The demo (README.md "Demo"): after IDLE_FRAMES title frames with no game key, the
# next part plays. A scene: the caption (big name at a byte column, a line in green at
# a byte column), the player, the bullet wait, the first hunter wait, the hunter
# wait, the seed, the pickup (type, x, y), the power, the jinx, the enemies (type,
# x, y) and the script (held keys, frames).
IDLE_FRAMES = 300
IDLE_SOON = 30
PROMPT_COL = 9
FIRST_SCENE = {"demohunter": 1, "demoshooter": 2}


@dataclass
class Scene:
    name: str
    name_column: int
    line: str
    line_column: int
    player: tuple[int, int]
    enemies: list[tuple[int, int, int]]
    script: list[tuple[str, int]]
    fire: int = 0
    first: int = 0
    wait: int = 0
    seed: int = 0xACE1
    pickup: tuple[int, int, int] = (0, 0, 0)
    power: int = 0
    jinx: int = 0


SCENES = {
    "grunt": Scene(
        "GRUNT",
        11,
        "SLOW  10 POINTS",
        8,
        (61, 150),
        [(1, 61, 30), (1, 21, 50), (1, 101, 50)],
        [("", 4), ("O", 8), ("A", 10), ("O", 8), ("D", 18), ("O", 8), ("", 16)],
    ),
}
SCENES["hunter"] = Scene(
    "HUNTER",
    10,
    "FAST  50 POINTS",
    8,
    (61, 95),
    [],
    [("", 18), (";", 6), ("", 50), ("K", 8), ("", 16)],
    first=10,
    wait=50,
    seed=0x1234,
)
SCENES["shooter"] = Scene(
    "SHOOTER",
    9,
    "FIRES BACK  30 POINTS",
    5,
    (61, 150),
    [(3, 61, 30)],
    [("", 12), ("D", 8), ("", 14), ("A", 8), ("O", 10), ("", 16)],
    fire=20,
)
SCENES["points"] = Scene(
    "POINTS",
    10,
    "COLLECT FOR 100",
    8,
    (40, 92),
    [],
    [("", 6), ("D", 22), ("", 14)],
    pickup=(PK_POINTS, 80, 94),
)
SCENES["double"] = Scene(
    "DOUBLE",
    10,
    "SHOTS GO TWO WAYS",
    7,
    (52, 95),
    [(1, 8, 95), (1, 114, 95)],
    [("", 4), ("D", 4), ("", 10), (";", 6), ("", 30)],
    pickup=(PK_DOUBLE, 64, 96),
)
SCENES["spread"] = Scene(
    "SPREAD",
    10,
    "SHOTS GO FOUR WAYS",
    7,
    (61, 95),
    [(1, 61, 20), (1, 61, 170), (1, 8, 95), (1, 114, 95)],
    [("", 4), ("S", 4), ("", 10), ("O", 6), ("", 30)],
    pickup=(PK_SPREAD, 60, 108),
)
SCENES["star"] = Scene(
    "STAR",
    12,
    "SHOTS GO EIGHT WAYS",
    6,
    (49, 95),
    [
        (1, 61, 15),
        (1, 61, 175),
        (1, 5, 95),
        (1, 117, 95),
        (1, 23, 19),
        (1, 99, 19),
        (1, 23, 171),
        (1, 99, 171),
    ],
    [("", 4), ("D", 6), ("", 10), ("O", 6), ("", 30)],
    pickup=(PK_STAR, 60, 96),
)
SCENES["bomb"] = Scene(
    "BOMB",
    12,
    "CLEARS THE AREA",
    8,
    (61, 95),
    [(1, 30, 60), (1, 92, 60), (1, 30, 130), (1, 92, 130), (1, 61, 50), (1, 61, 140)],
    [("", 10), ("D", 4), ("", 30)],
    pickup=(PK_BOMB, 72, 96),
)
SCENES["slow"] = Scene(
    "SLOW",
    12,
    "JINX  SLOWER SHOTS",
    7,
    (49, 150),
    [(1, 61, 15), (1, 61, 40), (1, 61, 65)],
    [("", 4), ("D", 6), ("", 6), ("O", 40), ("", 16)],
    pickup=(PK_SLOW, 60, 151),
)
SCENES["heavy"] = Scene(
    "HEAVY",
    11,
    "JINX  SLOWER STEPS",
    7,
    (49, 95),
    [(1, 117, 30)],
    [("", 4), ("D", 6), ("", 4), ("A", 32), (";", 8), ("", 16)],
    pickup=(PK_HEAVY, 60, 96),
)
SCENES["blitz"] = Scene(
    "BLITZ",
    11,
    "JINX  HUNTERS RUSH IN",
    5,
    (49, 95),
    [],
    [("", 4), ("D", 4), ("", 4), ("O;", 14), ("K", 14), (";", 10), ("", 16)],
    pickup=(PK_BLITZ, 60, 96),
    seed=0x2718,
)
PARTS = [
    ["grunt", "hunter", "shooter"],
    ["points", "double", "spread"],
    ["star", "bomb"],
    ["slow", "heavy", "blitz"],
]
FIRST_PART = {
    "demopoints": 1,
    "demodouble": 1,
    "demospread": 1,
    "demostar": 2,
    "demobomb": 2,
    "demoslow": 3,
    "demoheavy": 3,
    "demoblitz": 3,
}
FIRST_SCENE.update(
    {"demodouble": 1, "demospread": 2, "demobomb": 1, "demoheavy": 1, "demoblitz": 2}
)
# Sound effects from README.md "Sound": (mode, period, volume, fields) records. Each
# field plays one record, so each frame plays two.
SQUARE, NOISE = 0, 0x80


def square(*notes: tuple[int, int, int]) -> list[tuple[int, int, int, int]]:
    return [(SQUARE, p, v, f) for p, v, f in notes]


EFFECTS = {
    "shot": (1, square((8, 24, 1), (10, 22, 1), (13, 18, 1), (17, 14, 1), (22, 10, 1))),
    "boom": (
        2,
        [
            (NOISE, p, v, 1)
            for p, v in ((2, 44), (2, 40), (3, 34), (3, 28), (4, 22), (4, 16), (5, 10), (6, 6))
        ],
    ),
    "hunter": (3, square((10, 26, 2), (14, 26, 2), (10, 26, 2), (14, 26, 2))),
    "level": (
        4,
        square((30, 28, 3), (22, 28, 3), (16, 28, 3), (11, 28, 3), (11, 20, 1), (11, 12, 1)),
    ),
    "extra": (4, square(*[(15, 30, 2), (10, 30, 2)] * 3, (10, 20, 2))),
    "pickup": (4, square((31, 26, 2), (23, 26, 2), (16, 26, 3), (16, 14, 2))),
    "jinx": (4, square((16, 26, 3), (23, 26, 3), (31, 26, 3), (40, 26, 4), (40, 14, 2))),
    "bomb": (
        5,
        [
            (NOISE, p, v, 2)
            for p, v in (
                (1, 62),
                (1, 58),
                (2, 54),
                (2, 50),
                (3, 44),
                (4, 38),
                (5, 32),
                (6, 26),
                (8, 20),
                (10, 14),
                (12, 8),
            )
        ],
    ),
    "zap": (1, square((12, 22, 1), (16, 18, 1), (20, 14, 1))),
    "death": (
        5,
        [
            (NOISE, p, v, 1)
            for p, v in (
                (1, 60),
                (1, 56),
                (2, 52),
                (2, 48),
                (3, 44),
                (3, 40),
                (4, 36),
                (4, 32),
                (5, 28),
                (6, 24),
                (7, 20),
                (8, 16),
                (9, 12),
                (10, 8),
            )
        ],
    ),
    "start": (
        6,
        square(
            (48, 28, 4),
            (38, 28, 4),
            (31, 28, 4),
            (23, 28, 6),
            (31, 28, 3),
            (23, 28, 12),
            (23, 18, 4),
            (23, 10, 4),
        ),
    ),
    "over": (
        6,
        square((32, 28, 20), (40, 28, 20), (43, 28, 20), (48, 28, 30), (48, 20, 15), (48, 12, 15)),
    ),
}
SAFE_X, SAFE_Y = 28, 45


def sprites(file: str = "sprites.txt") -> dict[str, list[str]]:
    art: dict[str, list[str]] = {}
    name = ""
    for line in (HERE / file).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("["):
            name = line[1:-1]
            art[name] = []
        else:
            art[name].append(line)
    return art


ART = sprites()
FONT = sprites("font.txt")


@dataclass
class Shot:
    x: int
    y: int
    vx: int
    vy: int
    name: str


@dataclass
class Enemy:
    kind: int
    x: int
    y: int
    tick: int


@dataclass
class Game:
    x: int = START[0]
    y: int = START[1]
    delay: int = 0
    slots: list[Shot | None] = field(default_factory=lambda: [None] * SHOT_SLOTS)
    level: int = 1
    seed: int = SEED
    hunter_wait: int = 0
    hunter_timer: int = 0
    enemies: list[Enemy | None] = field(default_factory=lambda: [None] * ENEMY_SLOTS)
    controls: frozenset = frozenset()
    last_vertical: tuple[int, ...] = ()
    effect: str = ""
    record: int = 0
    priority: int = 0
    hold: int = 0
    sound: tuple[int, int, int, int] | None = None  # the record of the second field
    score: int = 0
    next_extra: int = EXTRA_EVERY
    lives: int = LIVES
    dying: int = 0
    over: int = 0
    ready: int = 0
    bullets: list[list[int] | None] = field(default_factory=lambda: [None] * BULLET_SLOTS)
    fire_wait: int = 0
    fire_timer: int = 0
    shooter_turn: int = 0
    pickup: list[int] | None = None  # type, x, y, frames left
    pk_next: int = 0
    drop_count: int = 0
    power: int = 0
    power_timer: int = 0
    jinx: int = 0
    jinx_timer: int = 0
    variant: str = ""
    phase: int = PLAY
    table: list[tuple[int, str]] = field(default_factory=lambda: list(TABLE))
    rank: int = 0
    new_rank: int = NO_RANK
    initials: list[str] = field(default_factory=lambda: ["\0"] * 3)
    pos: int = 0
    rpt: int = 0
    old_fire: frozenset = frozenset()
    fire_new: frozenset = frozenset()
    setup: bool = False  # a new screen in this frame
    idle: int = 0
    demo: bool = False
    part: int = 0
    scenes: list[str] = field(default_factory=list)  # the scenes left in the part
    script: list[tuple[str, int]] = field(default_factory=list)  # the keys left
    dcount: int = 0
    dkeys: str = ""
    skip: int = 0  # FIRST_SCENE, until the first demo

    def start_sound(self, name: str) -> None:
        if EFFECTS[name][0] >= self.priority:
            self.priority = EFFECTS[name][0]
            self.effect, self.record, self.hold = name, 0, 0

    def sound_frame(self) -> None:
        """One field: keep the record for its fields, then take the next one."""
        if self.hold > 1:
            self.hold -= 1
            return
        self.sound = None
        if self.effect:
            records = EFFECTS[self.effect][1]
            if self.record < len(records):
                self.sound = records[self.record]
                self.hold = self.sound[3]
                self.record += 1
            else:
                self.effect, self.priority, self.hold = "", 0, 0

    def add_score(self, points: int) -> None:
        self.score = (self.score + points) % 1_000_000
        if self.score >= self.next_extra:
            self.lives += 1
            self.next_extra += EXTRA_EVERY
            self.start_sound("extra")

    def rand_step(self) -> None:
        """16-bit shift right; a 1 bit out gives exclusive-or with $B400."""
        out = self.seed & 1
        self.seed >>= 1
        if out:
            self.seed ^= 0xB400

    def rand(self) -> int:
        for _ in range(8):
            self.rand_step()
        return self.seed & 0xFF

    def random_x(self) -> int:
        while (r := self.rand() & 127) > END_X - ENEMY_W - MIN_X:
            pass
        return MIN_X + r

    def random_y(self) -> int:
        while (r := self.rand()) > END_Y - ENEMY_H - MIN_Y:
            pass
        return MIN_Y + r


def spawn_level_enemies(game: Game, grunts: int, shooters: int) -> None:
    for slot in range(grunts + shooters):
        while True:
            x = game.random_x()
            y = game.random_y()
            if not (abs(x - START[0]) <= SAFE_X and abs(y - START[1]) <= SAFE_Y):
                break
        game.enemies[slot] = Enemy(GRUNT if slot < grunts else SHOOTER, x, y, slot % 2 + 1)


def start_level(game: Game) -> None:
    game.x, game.y = START
    clear_arena(game)
    if game.variant in FIXED_PICKUP:
        game.pickup = [FIXED_PICKUP[game.variant], 60, 60, PICKUP_FRAMES]
    if "NO_READY" not in game.controls:
        game.ready = READY_FRAMES
    if game.level in TEACH:
        grunts, game.hunter_timer, game.hunter_wait, _, _, shooters, fire = TEACH[game.level]
    else:
        shooters = min(4, game.level - 3)
        grunts = min(20, 4 + 2 * game.level) - shooters
        fire = max(24, 84 - 8 * game.level)
        game.hunter_wait = game.hunter_timer = max(45, 330 - 30 * game.level)
    game.fire_wait = game.fire_timer = fire
    if "HUNTER_SOON" in game.controls:
        game.hunter_wait = game.hunter_timer = 15
    if "FIXED_ENEMIES" in game.controls:
        game.hunter_wait = game.hunter_timer = game.fire_wait = 0
        game.enemies[0] = Enemy(GRUNT, 100, 90, 1)
        game.enemies[1] = Enemy(HUNTER, 100, 40, PERIOD[HUNTER])
        return
    if "ONE_SHOOTER" in game.controls:
        game.hunter_wait = game.hunter_timer = 0
        game.fire_wait = game.fire_timer = 20
        game.enemies[0] = Enemy(SHOOTER, START[0], 30, PERIOD[SHOOTER])
        return
    if "NO_ENEMIES" in game.controls:
        game.fire_wait = 0
        return
    spawn_level_enemies(game, grunts, shooters)


def clear_arena(game: Game) -> None:
    game.delay = 0
    game.slots = [None] * SHOT_SLOTS
    game.enemies = [None] * ENEMY_SLOTS
    game.bullets = [None] * BULLET_SLOTS
    game.shooter_turn = 0xFF
    game.pickup = None


def start_demo(game: Game) -> None:
    """The next part: the arena, one life that cannot end, level 1, score 0."""
    game.phase, game.demo, game.setup = PLAY, True, True
    game.lives, game.level, game.score, game.next_extra = 1, 1, 0, EXTRA_EVERY
    game.scenes = list(PARTS[game.part])[game.skip :]
    game.skip = 0
    game.part = (game.part + 1) % len(PARTS)
    start_scene(game)


def start_scene(game: Game) -> None:
    scene = SCENES[game.scenes[0]]
    game.x, game.y = scene.player
    clear_arena(game)
    game.fire_wait = game.fire_timer = scene.fire
    game.hunter_timer, game.hunter_wait = scene.first, scene.wait
    game.seed = scene.seed
    if scene.pickup[0]:
        game.pickup = [*scene.pickup, PICKUP_FRAMES]
    game.power, game.power_timer = scene.power, POWER_TIME.get(game.variant, 300)
    game.jinx, game.jinx_timer = scene.jinx, JINX_TIME
    game.script, game.dcount = list(scene.script), 0
    game.ready = READY_FRAMES
    for slot, (kind, x, y) in enumerate(scene.enemies):
        game.enemies[slot] = Enemy(kind, x, y, PERIOD[kind])


def demo_keys(game: Game) -> str | None:
    """The keys of the demo player for this frame, or None at the end of the script."""
    if game.dcount == 0:
        if not game.script:
            return None
        game.dkeys, game.dcount = game.script.pop(0)
    game.dcount -= 1
    return game.dkeys


def setup_title(game: Game) -> None:
    game.phase, game.demo, game.idle, game.setup = TITLE, False, 0, True


def power_on(variant: str) -> Game:
    """The program clears its state, then shows the title (or starts a game at once)."""
    if "SKIP_TITLE" in CONTROLS[variant]:
        return new_game(variant)
    return Game(
        x=0,
        y=0,
        level=0,
        lives=0,
        next_extra=0,
        phase=TITLE,
        controls=frozenset(CONTROLS[variant]),
        variant=variant,
        part=FIRST_PART.get(variant, 0),
        skip=FIRST_SCENE.get(variant, 0),
    )


def game_end(game: Game) -> None:
    """After the pause of game over: the initials if the score gets a place."""
    game.new_rank = NO_RANK
    game.rank = next((i for i, (s, _) in enumerate(game.table) if game.score > s), 10)
    game.setup = True
    if game.rank < 10:
        game.phase, game.pos, game.rpt, game.initials = ENTRY, 0, 0, ["A"] * 3
    else:
        setup_title(game)


def entry(game: Game, keys: str) -> None:
    """W or S changes the letter: at once, then after 12 frames, then each 4 frames."""
    up, down = "W" in keys, "S" in keys
    if up != down:
        change = game.rpt == 0
        if change:
            game.rpt = REPEAT_FIRST
        else:
            game.rpt -= 1
            if game.rpt == 0:
                change, game.rpt = True, REPEAT_NEXT
        if change:
            letter = ord(game.initials[game.pos]) - ord("A") + (1 if up else -1)
            game.initials[game.pos] = chr(ord("A") + letter % 26)
            game.start_sound("shot")
    else:
        game.rpt = 0
    if game.fire_new:
        game.pos += 1
        if game.pos < 3:
            game.start_sound("shot")
        else:
            game.table.insert(game.rank, (game.score, "".join(game.initials)))
            game.table.pop()
            game.new_rank = game.rank
            game.start_sound("level")
            setup_title(game)


def new_game(variant: str, game: Game | None = None) -> Game:
    """A new game: at power-on, or after the pause that follows game over."""
    if game is None:
        game = Game(controls=frozenset(CONTROLS[variant]))
    game.score = START_SCORE.get(variant, 0)
    game.next_extra = EXTRA_EVERY
    game.lives = START_LIVES.get(variant, LIVES)
    game.variant = variant
    game.drop_count = DROP_EVERY.get(variant, 6)
    game.pk_next = FIRST_DROP.get(variant, 0)
    game.power = FIRST_POWER.get(variant, 0)
    game.power_timer = POWER_TIME.get(variant, 300)
    game.jinx = FIRST_JINX.get(variant, 0)
    game.jinx_timer = JINX_TIME
    game.level = START_LEVEL.get(variant, 1)
    game.start_sound("start")
    start_level(game)
    return game


def toward(value: int, target: int, most: int) -> int:
    return value + max(-most, min(most, target - value))


def move_enemies(game: Game) -> None:
    if "STILL" in game.controls:
        return
    for enemy in game.enemies:
        if enemy:
            enemy.tick -= 1
            if enemy.tick == 0:
                enemy.tick = PERIOD[enemy.kind]
                enemy.x = toward(enemy.x, game.x, 1)
                enemy.y = toward(enemy.y, game.y, 2)


def spawn_hunter(game: Game) -> None:
    if game.hunter_wait == 0:
        return
    if game.hunter_timer > 0:
        game.hunter_timer -= 1
    if game.hunter_timer > 0 or not new_hunter(game):
        return
    game.hunter_timer = game.hunter_wait
    game.start_sound("hunter")


def new_hunter(game: Game) -> bool:
    """A hunter in the first free slot on a random edge, but not near the player."""
    if None not in game.enemies:
        return False
    side = game.rand() & 3
    if side < 2:
        x, y = game.random_x(), (MIN_Y, END_Y - ENEMY_H)[side]
    else:
        y = game.random_y()
        x = (MIN_X, END_X - ENEMY_W)[side - 2]
    if abs(x - game.x) < 20 and abs(y - game.y) < 30:
        return False
    game.enemies[game.enemies.index(None)] = Enemy(HUNTER, x, y, PERIOD[HUNTER])
    return True


def overlap(ax: int, ay: int, aw: int, ah: int, bx: int, by: int, bw: int, bh: int) -> bool:
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


def hit_enemies(game: Game) -> None:
    for i, shot in enumerate(game.slots):
        if not shot:
            continue
        w, h = size(shot.name)
        for j, enemy in enumerate(game.enemies):
            if enemy and overlap(shot.x, shot.y, w, h, enemy.x, enemy.y, ENEMY_W, ENEMY_H):
                game.enemies[j] = None
                game.slots[i] = None
                game.start_sound("boom")
                game.add_score(POINTS[enemy.kind])
                drop_pickup(game, enemy)
                break


def touched(game: Game) -> bool:
    if "NO_DEATH" in game.controls or game.demo:
        return False
    return any(
        e and overlap(e.x, e.y, ENEMY_W, ENEMY_H, game.x, game.y, PLAYER_W, PLAYER_H)
        for e in game.enemies
    ) or any(
        b and overlap(b[0], b[1], BULLET_W, BULLET_H, game.x, game.y, PLAYER_W, PLAYER_H)
        for b in game.bullets
    )


def move_bullets(game: Game) -> None:
    for i, b in enumerate(game.bullets):
        if b:
            b[0] += b[2]
            b[1] += b[3]
            if not (MIN_X <= b[0] <= END_X - BULLET_W and MIN_Y <= b[1] <= END_Y - BULLET_H):
                game.bullets[i] = None


def enemy_fire(game: Game) -> None:
    """Each fire wait, the next shooter after the last one in slot order fires at the
    player, if a bullet slot is free."""
    if game.fire_wait == 0:
        return
    game.fire_timer -= 1
    if game.fire_timer:
        return
    game.fire_timer = game.fire_wait
    for _ in range(ENEMY_SLOTS):
        game.shooter_turn = game.shooter_turn + 1 if game.shooter_turn + 1 < ENEMY_SLOTS else 0
        enemy = game.enemies[game.shooter_turn]
        if enemy and enemy.kind == SHOOTER:
            break
    else:
        return
    if None not in game.bullets:
        return
    ax, ay = abs(game.x - enemy.x), abs(game.y - enemy.y)
    vx = BULLET_VX if game.x >= enemy.x else -BULLET_VX
    vy = BULLET_VY if game.y >= enemy.y else -BULLET_VY
    if ax > ay:
        vy = 0
    elif ay // 4 > ax:
        vx = 0
    x = enemy.x + (ENEMY_W - BULLET_W) // 2
    y = enemy.y + (ENEMY_H - BULLET_H) // 2
    game.bullets[game.bullets.index(None)] = [x, y, vx, vy]
    game.start_sound("zap")


def direction(keys: str, table: dict[str, tuple[int, int]]) -> tuple[int, int]:
    """Sum of the held keys: opposite keys cancel."""
    dx = sum(table[k][0] for k in set(keys) if k in table)
    dy = sum(table[k][1] for k in set(keys) if k in table)
    return dx, dy


def shot_sprite(dx: int, dy: int) -> str:
    if dy == 0:
        return "shot_horizontal"
    if dx == 0:
        return "shot_vertical"
    return "shot_back" if dx == dy else "shot_forward"


def size(name: str) -> tuple[int, int]:
    return len(ART[name][0]), len(ART[name])


def inside(x: int, y: int, name: str) -> bool:
    w, h = size(name)
    return MIN_X <= x and x + w <= END_X and MIN_Y <= y and y + h <= END_Y


def advance_death(game: Game) -> None:
    game.dying -= 1
    if game.dying == 0:
        game.lives -= 1
        if game.lives == 0:
            game.start_sound("over")
            game.over = OVER_FRAMES
        else:
            game.power = game.jinx = 0
            start_level(game)


def advance_demo(game: Game) -> None:
    demo = demo_keys(game)
    if demo is not None:
        play(game, demo)
    elif len(game.scenes) > 1:
        game.scenes.pop(0)
        start_scene(game)
    else:
        setup_title(game)


def advance_title(game: Game, keys: str, variant: str) -> None:
    if game.fire_new:
        game.phase, game.setup, game.demo = PLAY, True, False
        new_game(variant, game)
    elif any(k in MOVE or k in SHOOT for k in keys):
        game.idle = 0
    else:
        game.idle += 1
        if game.idle == (IDLE_SOON if "DEMO_SOON" in game.controls else IDLE_FRAMES):
            start_demo(game)


def step(game: Game, keys: str, variant: str) -> None:
    """One frame of the rules in README.md."""
    game.rand_step()
    keys = read_keys(keys)
    if {"O", "K", "W", "S"} <= set(keys):
        # K and O held, and W and S read as held: keep the last vertical keys.
        keys = "".join(k for k in keys if k not in "WS") + "".join(game.last_vertical)
    else:
        game.last_vertical = tuple(k for k in "WS" if k in keys)
    fire = frozenset(k for k in keys if k in SHOOT)
    game.fire_new, game.old_fire = fire - game.old_fire, fire
    if game.phase == TITLE:
        advance_title(game, keys, variant)
    elif game.demo and game.fire_new:
        game.phase, game.setup, game.demo = PLAY, True, False
        new_game(variant, game)
    elif game.phase == ENTRY:
        entry(game, keys)
    elif game.over:
        game.over -= 1
        if game.over == 0:
            game_end(game)
    elif game.dying:
        advance_death(game)
    elif game.ready:
        game.ready -= 1
    elif game.demo:
        advance_demo(game)
    else:
        play(game, keys)
    game.sound_frame()  # the first field of the frame
    game.sound_frame()  # the second field: this record plays at the checkpoint


def play(game: Game, keys: str) -> None:
    dx, dy = direction(keys, MOVE)
    scale = 1 if game.jinx == PK_HEAVY else 2  # heavy: half the step
    game.x = min(max(game.x + scale * dx, MIN_X), END_X - PLAYER_W)
    game.y = min(max(game.y + 2 * scale * dy, MIN_Y), END_Y - PLAYER_H)
    for i, shot in enumerate(game.slots):
        if shot:
            shot.x += shot.vx
            shot.y += shot.vy
            if not inside(shot.x, shot.y, shot.name):
                game.slots[i] = None
    move_bullets(game)
    fire(game, keys)
    move_enemies(game)
    spawn_hunter(game)
    enemy_fire(game)
    hit_enemies(game)
    update_pickup(game)
    if touched(game):
        game.start_sound("death")
        game.dying = DYING_FRAMES
    elif not any(game.enemies) and "NO_ENEMIES" not in game.controls and not game.demo:
        game.start_sound("level")
        game.level += 1
        start_level(game)


def read_keys(held: str) -> str:
    """The keys that the scanner reads: a key reads as held when its row and its column
    connect through held keys (the matrix has no diodes; Tandy PDF 75)."""
    pressed = {MATRIX[k] for k in held if k in MATRIX}
    rows = {r for r, _ in pressed}
    reach = {r: {r} for r in rows}
    changed = True
    while changed:
        changed = False
        for r in rows:
            cols = {c for rr, c in pressed if rr in reach[r]}
            more = {rr for rr, c in pressed if c in cols} - reach[r]
            if more:
                reach[r] |= more
                changed = True
    return "".join(
        k
        for k, (r, c) in MATRIX.items()
        if r in rows and any((rr, c) in pressed for rr in reach[r])
    )


def fire(game: Game, keys: str) -> None:
    """A power counts down. Then the shoot delay. Then shots in 1, 2, 4 or 8 directions,
    at even steps around the ring from the direction of the keys."""
    if game.power:
        game.power_timer -= 1
        if game.power_timer == 0:
            game.power = 0
    if game.jinx:
        game.jinx_timer -= 1
        if game.jinx_timer == 0:
            game.jinx = 0
    if game.delay > 0:
        game.delay -= 1
        return
    fx, fy = direction(keys, SHOOT)
    if (fx, fy) == (0, 0):
        return
    count = SHOTS_OF[game.power]
    first = RING.index((fx, fy))
    fired = False
    for k in range(count):
        dx, dy = RING[(first + k * 8 // count) % 8]
        if None not in game.slots:
            continue
        name = shot_sprite(dx, dy)
        w, h = size(name)
        shot = Shot(
            game.x + (PLAYER_W - w) // 2, game.y + (PLAYER_H - h) // 2, 6 * dx, 12 * dy, name
        )
        game.slots[game.slots.index(None)] = shot
        fired = True
    if fired:
        game.delay = 2 * SHOT_DELAY + 1 if game.jinx == PK_SLOW else SHOT_DELAY
        game.start_sound("shot")


def drop_pickup(game: Game, enemy: Enemy) -> None:
    """From level 4, each 6th enemy that a shot removes leaves a pickup, if none is there."""
    if game.level < PICKUP_LEVEL:
        return
    game.drop_count -= 1
    if game.drop_count:
        return
    game.drop_count = DROP_EVERY.get(game.variant, 6)
    if game.pickup:
        return
    while True:
        kind = DROP_ORDER[game.pk_next]
        game.pk_next = (game.pk_next + 1) % len(DROP_ORDER)
        if kind < PK_SLOW or game.level >= JINX_LEVEL:
            break
    if kind == PK_BOMB and game.level < BOMB_LEVEL:
        kind = PK_POINTS
    game.pickup = [kind, enemy.x & ~3, enemy.y + (ENEMY_H - PICKUP_H) // 2, PICKUP_FRAMES]


def detonate_bomb(game: Game) -> None:
    for i, e in enumerate(game.enemies):
        if e and abs(e.x - game.x) < BOMB_X and abs(e.y - game.y) < BOMB_Y:
            game.enemies[i] = None
            game.add_score(POINTS[e.kind])
    game.bullets = [None] * BULLET_SLOTS
    game.start_sound("bomb")


def update_pickup(game: Game) -> None:
    if not game.pickup:
        return
    kind, x, y, _ = game.pickup
    if not overlap(x, y, PICKUP_W, PICKUP_H, game.x, game.y, PLAYER_W, PLAYER_H):
        game.pickup[3] -= 1
        if game.pickup[3] == 0:
            game.pickup = None
        return
    game.pickup = None
    if kind == PK_POINTS:
        game.add_score(50)
        game.add_score(50)
    elif kind == PK_BOMB:
        detonate_bomb(game)
        return
    elif kind >= PK_SLOW:
        game.jinx, game.jinx_timer = kind, JINX_TIME
        if kind == PK_BLITZ:
            game.jinx_timer = BLITZ_FRAMES
            for _ in range(BLITZ_HUNTERS):
                new_hunter(game)
        game.start_sound("jinx")
        return
    else:
        game.power, game.power_timer = kind, POWER_TIME.get(game.variant, 300)
    game.start_sound("pickup")


def journey(name: str = "journey.txt") -> list[tuple[str, tuple[int, int] | None]]:
    """Held keys for each frame, and the player position where the script gives one."""
    steps = []
    for line in (HERE / name).read_text().splitlines():
        parts = line.split("#")[0].split()
        if parts:
            keys = "" if parts[0] == "-" else parts[0]
            position = len(parts) >= 3 and parts[1].isdigit() and parts[2].isdigit()
            steps.append((keys, (int(parts[1]), int(parts[2])) if position else None))
    return steps


def games(frames: int, variant: str) -> list[Game]:
    """The state after each frame 0..frames. Frame 0 is the start."""
    return [g for g, _ in _games(MAX_FRAMES, variant)[: frames + 1]]


def screens(frame: int, variant: str) -> dict[int, np.ndarray]:
    """Pixel codes of screen A (0) and screen B (1) at the checkpoint of a frame."""
    return _games(MAX_FRAMES, variant)[frame][1]


MAX_FRAMES = 200


@functools.cache
def _games(frames: int, variant: str) -> list[tuple[Game, dict[int, np.ndarray]]]:
    script = journey(SCRIPTS[variant]) if variant in SCRIPTS else []
    game = power_on(variant)
    first = still(game)
    bufs = {0: first, 1: first}
    result = [(copy.deepcopy(game), bufs)]
    fresh = None  # the screen that does not have the new screen yet
    for n in range(frames):
        keys, position = script[n] if n < len(script) else ("", None)
        game.setup = False
        step(game, keys, variant)
        hidden = (n + 1) % 2
        # A new screen goes into the hidden screen only. The other screen gets it at
        # the start of the next frame that draws into it.
        if game.setup:
            bufs, fresh = {**bufs, hidden: still(game)}, 1 - hidden
        elif fresh == hidden:
            bufs, fresh = {**bufs, hidden: still(game)}, None
        bufs = {**bufs, hidden: changing(game, bufs[hidden], n + 1)}
        if position is not None and position != (game.x, game.y):
            raise ValueError(
                f"journey.txt line for frame {n + 1} gives {position}, the rules give "
                f"{(game.x, game.y)}: correct the script or the rules."
            )
        result.append((copy.deepcopy(game), bufs))
    return result


def arena() -> np.ndarray:
    codes = np.full((HEIGHT, WIDTH), BLUE, dtype=np.uint8)
    codes[[WALL_TOP, WALL_BOTTOM], WALL_LEFT : WALL_RIGHT + 1] = RED
    codes[WALL_TOP : WALL_BOTTOM + 1, [WALL_LEFT, WALL_RIGHT]] = RED
    return codes


def stamp(codes: np.ndarray, name: str, left: int, top: int) -> None:
    for y, row in enumerate(ART[name]):
        for x, char in enumerate(row):
            if char != ".":
                codes[top + y, left + x] = CODES[char]


def draw_ready_banner(codes: np.ndarray, game: Game) -> None:
    if game.ready and game.demo:
        scene = SCENES[game.scenes[0]]
        text(codes, scene.name, 60, scene.name_column, big=True)
        text(codes, scene.line, 76, scene.line_column, "G")
    elif game.ready:
        text(codes, f"LEVEL {game.level}", 60, 9, big=True)
        if game.level in TEACH:
            text(codes, TEACH[game.level][3], 76, TEACH[game.level][4], "G")
        elif game.level == JINX_LEVEL:
            text(codes, JINX_HINT[0], 76, JINX_HINT[1], "G")


def picture(game: Game | None, frame: int = 0) -> np.ndarray:
    """Pixel codes: the arena, then the shots and the enemies in slot order, then the player."""
    codes = arena()
    if game is not None:
        for shot in game.slots:
            if shot:
                stamp(codes, shot.name, shot.x, shot.y)
        for b in game.bullets:
            if b:
                stamp(codes, "bullet", b[0], b[1])
        if game.pickup:
            kind, x, y, left = game.pickup
            if left >= BLINK_FRAMES or not left & 4:
                stamp(codes, PICKUP_SPRITE[kind], x, y)
        for enemy in game.enemies:
            if enemy:
                stamp(codes, SPRITE[enemy.kind], enemy.x, enemy.y)
        stamp(codes, "player", game.x, game.y)
        draw_ready_banner(codes, game)
        hud(codes, game, frame)
    return codes


def hud(codes: np.ndarray, game: Game, frame: int = 0) -> None:
    """The 6-digit score at pixels 4-27 and the reserve lives from pixel 120 to the
    left, on rows HUD_ROW to HUD_ROW + 4. Glyphs from font.txt cover every pixel."""

    def glyph(name: str, left: int) -> None:
        for y, row in enumerate(FONT[name]):
            for x, char in enumerate(row):
                codes[HUD_ROW + y, left + x] = CODES[char]

    if game.demo:  # the prompt flashes at the rate of the title prompt; no names
        text(codes, "SHOOT TO START" if (frame - 1) & 16 == 0 else "", HUD_ROW, PROMPT_COL)
        return
    for k, digit in enumerate(f"{game.score:06d}"):
        glyph(digit, 4 + 4 * k)
    for i in range(min(max(game.lives - 1, 0), ICONS)):
        glyph("life", 120 - 4 * i)
    # The gift name in yellow and the jinx name in red, each with a bar of the time
    # that is left: one byte (4 pixels) for each step of frames, rounded up.
    for kind, timer, column, colour, step in (
        (game.power, game.power_timer, NAME_GIFT, "Y", GIFT_STEP),
        (game.jinx, game.jinx_timer, NAME_JINX, "R", JINX_STEP),
    ):
        if kind:
            text(codes, NAME[kind], HUD_ROW, column, colour)
            bar = min(BAR_BYTES, -(-timer // step))
            codes[BAR_ROW : BAR_ROW + 2, 4 * column : 4 * (column + bar)] = CODES[colour]


def text(
    codes: np.ndarray, words: str, row: int, column: int, colour: str = "Y", big: bool = False
) -> None:
    """Characters from font.txt at a pixel row and a byte column (4 pixels). The
    glyphs are yellow on blue; another colour takes the place of yellow. A big
    character shows each pixel as 2x2 pixels."""
    scale = 2 if big else 1
    for i, char in enumerate(words):
        glyph = FONT.get(char, ["BBBB"] * 5)
        left = 4 * column + 4 * scale * i
        for y, line in enumerate(glyph):
            for x, c in enumerate(line):
                code = CODES[colour] if c == "Y" else CODES[c]
                codes[
                    row + scale * y : row + scale * (y + 1),
                    left + scale * x : left + scale * (x + 1),
                ] = code


def blank() -> np.ndarray:
    return np.full((HEIGHT, WIDTH), BLUE, dtype=np.uint8)


def still(game: Game) -> np.ndarray:
    """The picture that a new screen puts into both screens."""
    if game.phase == PLAY:
        return arena()
    codes = blank()
    if game.phase == TITLE:
        text(codes, "ARENA BLASTER", 10, 3, big=True)
        text(codes, "HIGH SCORES", 28, 10)
        for i, (score, name) in enumerate(game.table):
            text(
                codes,
                f"{i + 1:2d} {name} {score:06d}",
                40 + 9 * i,
                9,
                "G" if i == game.new_rank else "Y",
            )
        stamp(codes, "grunt", 20, 136)
        text(codes, "10", 138, 7)
        stamp(codes, "hunter", 52, 136)
        text(codes, "50", 138, 15)
        stamp(codes, "shooter", 84, 136)
        text(codes, "30", 138, 23)
        text(codes, "MOVE WASD  SHOOT OKL;", 172, 5, "G")
    else:
        text(codes, "NEW HIGH SCORE", 20, 2, big=True)
        text(codes, f"{game.score:06d}", 40, 13)
        text(codes, "ENTER YOUR INITIALS", 60, 6)
        text(codes, "W AND S CHANGE THE LETTER", 120, 3, "G")
        text(codes, "SHOOT FOR THE NEXT LETTER", 130, 3, "G")
    return codes


def changing(game: Game, base: np.ndarray, frame: int) -> np.ndarray:
    """The hidden screen after frame N draws its part. The frame counter is N - 1."""
    if game.phase == PLAY:
        return picture(game, frame)
    codes = base.copy()
    if game.phase == TITLE:
        text(codes, "SHOOT TO START" if (frame - 1) & 16 == 0 else " " * 14, 156, 9)
    else:
        text(codes, " ".join(game.initials), 80, 12, big=True)
        for k in range(3):
            codes[92:94, 48 + 16 * k : 56 + 16 * k] = YELLOW if k == game.pos else BLUE
    return codes


def pack(codes: np.ndarray) -> bytes:
    """Four pixels per byte, leftmost pixel in bits 7-6 (MC6847 PDF 19 Table 3)."""
    c = codes.astype(np.uint8)
    return (c[:, 0::4] << 6 | c[:, 1::4] << 4 | c[:, 2::4] << 2 | c[:, 3::4]).tobytes()


def verify_high_scores(ram: bytes, symbols: dict[str, int], frame: int, game: Game) -> None:
    got = (ram[symbols["phase"]], ram[symbols["new_rank"]])
    if got != (game.phase, game.new_rank):
        raise ValueError(
            f"Frame {frame}: phase, new_rank = {got}, expected {(game.phase, game.new_rank)}."
        )
    table = ram[symbols["table"] : symbols["table"] + 60]
    want = b"".join(bytes.fromhex(f"{s:06d}") + n.encode() for s, n in game.table)
    if table != want:
        raise ValueError(f"Frame {frame}: the high-score table differs.")
    if game.phase == ENTRY:
        got = (
            bytes(ram[symbols["initials"] : symbols["initials"] + 3]).decode("latin-1"),
            ram[symbols["pos"]],
            ram[symbols["rpt"]],
        )
        want = ("".join(game.initials), game.pos, game.rpt)
        if got != want:
            raise ValueError(f"Frame {frame}: initials, pos, rpt = {got}, expected {want}.")


def verify_shots(ram: bytes, symbols: dict[str, int], frame: int, game: Game) -> None:
    for i, shot in enumerate(game.slots):
        base = symbols["shots"] + i * SLOT_SIZE
        if bool(ram[base]) != bool(shot):
            raise ValueError(f"Frame {frame}: shot slot {i} on/off differs.")
        if shot:
            got = (ram[base + 1], ram[base + 2], ram[base + 3], ram[base + 4])
            want = (shot.x, shot.y, shot.vx & 0xFF, shot.vy & 0xFF)
            if got != want:
                raise ValueError(f"Frame {frame}: shot slot {i} is {got}, expected {want}.")


def verify_pickup(ram: bytes, symbols: dict[str, int], frame: int, game: Game) -> None:
    p = game.pickup
    got = (
        ram[symbols["pk_type"]],
        ram[symbols["power"]],
        int.from_bytes(ram[symbols["power_timer"] : symbols["power_timer"] + 2], "big"),
    )
    want = (p[0] if p else 0, game.power, game.power_timer)
    if game.phase == PLAY and (got[0], got[1]) != want[:2]:
        raise ValueError(f"Frame {frame}: pk_type, power = {got[:2]}, expected {want[:2]}.")
    if game.power and got[2] != want[2]:
        raise ValueError(f"Frame {frame}: power_timer {got[2]}, expected {want[2]}.")
    got = (ram[symbols["jinx"]], ram[symbols["jinx_timer"]])
    if game.phase == PLAY and got[0] != game.jinx:
        raise ValueError(f"Frame {frame}: jinx {got[0]}, expected {game.jinx}.")
    if game.jinx and got[1] != game.jinx_timer:
        raise ValueError(f"Frame {frame}: jinx_timer {got[1]}, expected {game.jinx_timer}.")
    if p and tuple(ram[symbols[n]] for n in ("pk_x", "pk_y", "pk_timer")) != tuple(p[1:]):
        raise ValueError(f"Frame {frame}: the pickup differs: expected {p}.")


def verify_arena_state(ram: bytes, symbols: dict[str, int], frame: int, game: Game) -> None:
    if ram[symbols["shooter_turn"]] != game.shooter_turn and game.phase == PLAY:
        raise ValueError(f"Frame {frame}: shooter_turn differs.")
    got = (ram[symbols["demo"]], ram[symbols["part"]])
    if got != (int(game.demo), game.part):
        raise ValueError(f"Frame {frame}: demo, part = {got}, expected {(game.demo, game.part)}.")
    if ram[symbols["level"]] != game.level:
        raise ValueError(f"Frame {frame}: level {ram[symbols['level']]}, expected {game.level}.")
    for i, enemy in enumerate(game.enemies):
        base = symbols["enemies"] + i * ENEMY_SIZE
        got = tuple(ram[base : base + 4]) if ram[base] else None
        want = (enemy.kind, enemy.x, enemy.y, enemy.tick) if enemy else None
        if got != want:
            raise ValueError(f"Frame {frame}: enemy slot {i} is {got}, expected {want}.")


def verify_ram(ram: bytes, symbols: dict[str, int], frame: int, variant: str) -> None:
    bufs = screens(frame, variant)
    for which in (0, 1):
        at = SCREENS[which]
        if ram[at : at + SCREEN_BYTES] != pack(bufs[which]):
            raise ValueError(f"Frame {frame}: the screen at ${at:04X} differs.")
    game = games(frame, variant)[frame]
    verify_high_scores(ram, symbols, frame, game)
    actual = tuple(ram[symbols[name]] for name in STATE_FIELDS)
    if actual != (game.x, game.y, game.delay):
        raise ValueError(
            f"Frame {frame}: px, py, delay = {actual}, expected {(game.x, game.y, game.delay)}."
        )
    if int.from_bytes(ram[symbols["frames"] : symbols["frames"] + 2], "big") != frame - 1:
        raise ValueError(f"Frame {frame}: the frame counter differs.")
    verify_shots(ram, symbols, frame, game)
    bcd = int(ram[symbols["score"] : symbols["score"] + 3].hex())
    got = (
        bcd,
        ram[symbols["lives"]],
        ram[symbols["dying"]],
        ram[symbols["over"]],
        ram[symbols["ready"]],
    )
    want = (game.score, game.lives, game.dying, game.over, game.ready)
    if got != want:
        raise ValueError(
            f"Frame {frame}: score, lives, dying, over, ready = {got}, expected {want}."
        )
    for i, b in enumerate(game.bullets):
        base = symbols["bullets"] + i * BULLET_SIZE
        got = tuple(ram[base + 1 : base + 5]) if ram[base] else None
        want = (b[0], b[1], b[2] & 0xFF, b[3] & 0xFF) if b else None
        if got != want:
            raise ValueError(f"Frame {frame}: bullet slot {i} is {got}, expected {want}.")
    verify_pickup(ram, symbols, frame, game)
    verify_arena_state(ram, symbols, frame, game)


def expected_frame(frame: int, variant: str) -> np.ndarray:
    """XRoar's picture of the shown screen: CG6, colour set 0, measured xroar palette."""
    return render(screens(frame, variant)[frame % 2], MODES["CG6"], 0, XROAR, 2)


# --- Sound. The sound plays only while the program waits for the end of the picture.
# The capture ends at the checkpoint, at the end of that wait, so the last part of the
# capture holds the record of the frame.
CPU_HZ = 14_318_180 / 16  # Tandy PDF 26
# Measured in this project's captures, not sourced: one DAC unit is about 352.5 in
# XRoar's 16-bit mixer output.
MIXER_PER_DAC = 352.5
# Each frame lasts two fields. The second field's record plays in the wait at the end
# of the second field. The check judges the last 4 ms of that wait in every build.
WINDOW_S = 0.004


def square_hz(period: int) -> float:
    """A half wave is 17 x period + 35 cycles (main.asm play_until_fs; Leventhal
    Appendix C, PDF 553-555)."""
    return CPU_HZ / (2 * (17 * period + 35))


def steps(samples: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    jumps = np.abs(np.diff(samples.astype(np.int32)))
    where = np.nonzero(jumps > MIXER_PER_DAC * 3)[0]
    return where, jumps[where]


def verify_sound(sound, frame: int, variant: str) -> dict[str, object]:
    game = games(frame, variant)[frame]
    record = game.sound
    window = sound.samples[-int(WINDOW_S * sound.rate) :]
    where, sizes = steps(window)
    if record is None or record[2] == 0:
        if len(where):
            raise ValueError(f"Frame {frame}: {len(where)} DAC steps, expected silence.")
        return {"frame": frame, "sound": "silent"}
    mode, period, volume, _ = record
    want = volume * MIXER_PER_DAC
    if len(where) < 3 or not np.all(np.abs(sizes - want) < 0.1 * want):
        raise ValueError(
            f"Frame {frame}: {len(where)} steps of {sizes.tolist()[:4]}, expected volume "
            f"{volume} ({want:.0f}) for {game.effect}."
        )
    gaps = np.diff(where)
    if mode == SQUARE:
        hz = (len(where) - 1) / (2 * (where[-1] - where[0]) / sound.rate)
        if abs(hz / square_hz(period) - 1) > 0.05:
            raise ValueError(
                f"Frame {frame}: {hz:.0f} Hz, expected {square_hz(period):.0f} Hz "
                f"for {game.effect}."
            )
        return {"frame": frame, "sound": game.effect, "hz": round(hz)}
    if gaps.min() == gaps.max():
        raise ValueError(f"Frame {frame}: regular steps, expected noise for {game.effect}.")
    return {"frame": frame, "sound": game.effect, "noise_steps": len(where)}
