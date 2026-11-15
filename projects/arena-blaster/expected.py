"""Independent model of Arena Blaster: the rules for each frame, the arena and the sprites.

Written from the rules and the design in README.md and the art in sprites.txt. It does
not use main.asm, assets.py, the assembled bytes or a captured snapshot. It reads the
key script and simulates each frame. Then it draws each screen pixel by pixel and packs
the pixels itself.

Frame N is drawn into the hidden screen and then shown. Odd frames are at $2400 and even
frames at $0400. The model keeps both screens. A new screen (the arena, the title or the
initials) goes into both screens. Then each frame draws its part into the hidden screen:
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
SHOT_SLOTS, SHOT_DELAY = 6, 2
# Movement keys and shoot keys: (dx, dy) for each key letter in the key script.
MOVE = {"W": (0, -1), "S": (0, 1), "A": (-1, 0), "D": (1, 0)}
SHOOT = {"O": (0, -1), "L": (0, 1), "K": (-1, 0), ";": (1, 0)}
# (row, column) of each script key in the matrix: Tandy PDF 75. C is the
# wrong-key control.
MATRIX = {"A": (0, 1), "D": (0, 4), "C": (0, 3), "K": (1, 3), "L": (1, 4), "O": (1, 7),
          "S": (2, 3), "W": (2, 7), ";": (5, 3)}
# The scanner's labels in RAM that the check compares.
STATE_FIELDS = ("px", "py", "delay")
SLOT_SIZE = 11  # on, x, y, vx, vy, sprite (2), maxx, maxy, w, h
# Enemies (README.md "Levels and enemies").
ENEMY_SLOTS, ENEMY_SIZE = 24, 4  # type, x, y, tick
ENEMY_W, ENEMY_H = 6, 10
GRUNT, HUNTER = 1, 2
PERIOD = {GRUNT: 2, HUNTER: 1}
SPRITE = {GRUNT: "grunt", HUNTER: "hunter"}
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
    "level10": {"SKIP_TITLE"},
    "over": {"SKIP_TITLE", "NO_READY"},
    "scores": {"NO_READY", "FIXED_ENEMIES"},
}
START_LEVEL = {"level3": 3, "level10": 10}
START_LIVES = {"over": 1, "scores": 1}
START_SCORE = {"hit": 990, "scores": 5000}
# Score and lives (README.md "Score and lives").
POINTS = {1: 10, 2: 50}  # grunt, hunter
EXTRA_EVERY = 1000
LIVES = 3
DYING_FRAMES, OVER_FRAMES = 45, 90
HUD_ROW, ICONS = 3, 6
SCRIPTS = {"moves": "moves.txt", "hit": "hit.txt", "scores": "scores.txt"}
# Title and high scores (README.md "Title and high scores").
TITLE, PLAY, ENTRY = 0, 1, 2
TABLE = [(10000, "ZAP"), (9000, "ACE"), (8000, "MAX"), (7000, "JET"), (6000, "SKY"),
         (5000, "REX"), (4000, "ION"), (3000, "VOX"), (2000, "KIT"), (1000, "DOT")]
REPEAT_FIRST, REPEAT_NEXT = 12, 4
NO_RANK = 0xFF
# The first levels (README.md "Levels and enemies"): grunts, frames until the first
# hunter, frames between hunters (0 = no hunters), the hint and its byte column.
TEACH = {
    1: (4, 0, 0, "SHOOT THE GRUNTS", 8),
    2: (8, 0, 0, "HOLD TWO KEYS FOR DIAGONALS", 2),
    3: (6, 60, 240, "HUNTERS ARE FAST", 8),
    4: (10, 210, 210, "MORE OF EVERYTHING", 7),
}
READY_FRAMES = 60
# Sound effects from README.md "Sound": (mode, period, volume, fields) records. Each
# field plays one record, so each frame plays two.
SQUARE, NOISE = 0, 0x80


def square(*notes: tuple[int, int, int]) -> list[tuple[int, int, int, int]]:
    return [(SQUARE, p, v, f) for p, v, f in notes]


EFFECTS = {
    "shot": (1, square((8, 24, 1), (10, 22, 1), (13, 18, 1), (17, 14, 1), (22, 10, 1))),
    "boom": (2, [(NOISE, p, v, 1) for p, v in
                 ((2, 44), (2, 40), (3, 34), (3, 28), (4, 22), (4, 16), (5, 10), (6, 6))]),
    "hunter": (3, square((10, 26, 2), (14, 26, 2), (10, 26, 2), (14, 26, 2))),
    "level": (4, square((30, 28, 3), (22, 28, 3), (16, 28, 3), (11, 28, 3), (11, 20, 1),
                        (11, 12, 1))),
    "extra": (4, square(*[(15, 30, 2), (10, 30, 2)] * 3, (10, 20, 2))),
    "death": (5, [(NOISE, p, v, 1) for p, v in
                  ((1, 60), (1, 56), (2, 52), (2, 48), (3, 44), (3, 40), (4, 36), (4, 32),
                   (5, 28), (6, 24), (7, 20), (8, 16), (9, 12), (10, 8))]),
    "start": (6, square((48, 28, 4), (38, 28, 4), (31, 28, 4), (23, 28, 6), (31, 28, 3),
                        (23, 28, 12), (23, 18, 4), (23, 10, 4))),
    "over": (6, square((32, 28, 20), (40, 28, 20), (43, 28, 20), (48, 28, 30), (48, 20, 15),
                       (48, 12, 15))),
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


def start_level(game: Game) -> None:
    game.x, game.y = START
    game.delay = 0
    game.slots = [None] * SHOT_SLOTS
    game.enemies = [None] * ENEMY_SLOTS
    if "NO_READY" not in game.controls:
        game.ready = READY_FRAMES
    if game.level in TEACH:
        grunts, game.hunter_timer, game.hunter_wait, _, _ = TEACH[game.level]
    else:
        grunts = min(20, 4 + 2 * game.level)
        game.hunter_wait = game.hunter_timer = max(45, 330 - 30 * game.level)
    if "HUNTER_SOON" in game.controls:
        game.hunter_wait = game.hunter_timer = 15
    if "FIXED_ENEMIES" in game.controls:
        game.hunter_wait = game.hunter_timer = 0
        game.enemies[0] = Enemy(GRUNT, 100, 90, 1)
        game.enemies[1] = Enemy(HUNTER, 100, 40, PERIOD[HUNTER])
        return
    if "NO_ENEMIES" in game.controls:
        return
    for slot in range(grunts):
        while True:
            x = game.random_x()
            y = game.random_y()
            if not (abs(x - START[0]) <= SAFE_X and abs(y - START[1]) <= SAFE_Y):
                break
        game.enemies[slot] = Enemy(GRUNT, x, y, slot % 2 + 1)


def power_on(variant: str) -> Game:
    """The program clears its state, then shows the title (or starts a game at once)."""
    if "SKIP_TITLE" in CONTROLS[variant]:
        return new_game(variant)
    return Game(x=0, y=0, level=0, lives=0, next_extra=0, phase=TITLE,
                controls=frozenset(CONTROLS[variant]))


def game_end(game: Game) -> None:
    """After the pause of game over: the initials if the score gets a place."""
    game.new_rank = NO_RANK
    game.rank = next((i for i, (s, _) in enumerate(game.table) if game.score > s), 10)
    game.setup = True
    if game.rank < 10:
        game.phase, game.pos, game.rpt, game.initials = ENTRY, 0, 0, ["A"] * 3
    else:
        game.phase = TITLE


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
            game.phase, game.setup = TITLE, True


def new_game(variant: str, game: Game | None = None) -> Game:
    """A new game: at power-on, or after the pause that follows game over."""
    if game is None:
        game = Game(controls=frozenset(CONTROLS[variant]))
    game.score = START_SCORE.get(variant, 0)
    game.next_extra = EXTRA_EVERY
    game.lives = START_LIVES.get(variant, LIVES)
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
    if game.hunter_timer > 0 or None not in game.enemies:
        return
    side = game.rand() & 3
    if side < 2:
        x, y = game.random_x(), (MIN_Y, END_Y - ENEMY_H)[side]
    else:
        y = game.random_y()
        x = (MIN_X, END_X - ENEMY_W)[side - 2]
    if abs(x - game.x) < 20 and abs(y - game.y) < 30:
        return
    game.enemies[game.enemies.index(None)] = Enemy(HUNTER, x, y, PERIOD[HUNTER])
    game.hunter_timer = game.hunter_wait
    game.start_sound("hunter")


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
                break


def touched(game: Game) -> bool:
    if "NO_DEATH" in game.controls:
        return False
    return any(
        e and overlap(e.x, e.y, ENEMY_W, ENEMY_H, game.x, game.y, PLAYER_W, PLAYER_H)
        for e in game.enemies
    )


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
        if game.fire_new:
            game.phase, game.setup = PLAY, True
            new_game(variant, game)
    elif game.phase == ENTRY:
        entry(game, keys)
    elif game.over:
        game.over -= 1
        if game.over == 0:
            game_end(game)
    elif game.dying:
        game.dying -= 1
        if game.dying == 0:
            game.lives -= 1
            if game.lives == 0:
                game.start_sound("over")
                game.over = OVER_FRAMES
            else:
                start_level(game)
    elif game.ready:
        game.ready -= 1
    else:
        play(game, keys)
    game.sound_frame()  # the first field of the frame
    game.sound_frame()  # the second field: this record plays at the checkpoint


def play(game: Game, keys: str) -> None:
    dx, dy = direction(keys, MOVE)
    game.x = min(max(game.x + 2 * dx, MIN_X), END_X - PLAYER_W)
    game.y = min(max(game.y + 4 * dy, MIN_Y), END_Y - PLAYER_H)
    for i, shot in enumerate(game.slots):
        if shot:
            shot.x += shot.vx
            shot.y += shot.vy
            if not inside(shot.x, shot.y, shot.name):
                game.slots[i] = None
    fire(game, keys)
    move_enemies(game)
    spawn_hunter(game)
    hit_enemies(game)
    if touched(game):
        game.start_sound("death")
        game.dying = DYING_FRAMES
    elif not any(game.enemies) and "NO_ENEMIES" not in game.controls:
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
        k for k, (r, c) in MATRIX.items()
        if r in rows and any((rr, c) in pressed for rr in reach[r])
    )


def fire(game: Game, keys: str) -> None:
    if game.delay > 0:
        game.delay -= 1
        return
    fx, fy = direction(keys, SHOOT)
    if (fx, fy) == (0, 0) or None not in game.slots:
        return
    name = shot_sprite(fx, fy)
    w, h = size(name)
    shot = Shot(game.x + (PLAYER_W - w) // 2, game.y + (PLAYER_H - h) // 2, 6 * fx, 12 * fy, name)
    game.slots[game.slots.index(None)] = shot
    game.delay = SHOT_DELAY
    game.start_sound("shot")


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
    for n in range(frames):
        keys, position = script[n] if n < len(script) else ("", None)
        game.setup = False
        step(game, keys, variant)
        if game.setup:
            bufs = {0: still(game), 1: still(game)}
        hidden = (n + 1) % 2
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


def picture(game: Game | None) -> np.ndarray:
    """Pixel codes: the arena, then the shots and the enemies in slot order, then the player."""
    codes = arena()
    if game is not None:
        for shot in game.slots:
            if shot:
                stamp(codes, shot.name, shot.x, shot.y)
        for enemy in game.enemies:
            if enemy:
                stamp(codes, SPRITE[enemy.kind], enemy.x, enemy.y)
        stamp(codes, "player", game.x, game.y)
        if game.ready:
            text(codes, f"LEVEL {game.level}", 60, 9, big=True)
            if game.level in TEACH:
                text(codes, TEACH[game.level][3], 76, TEACH[game.level][4], "G")
        hud(codes, game)
    return codes


def hud(codes: np.ndarray, game: Game) -> None:
    """The 6-digit score at pixels 4-27 and the reserve lives from pixel 120 to the
    left, on rows HUD_ROW to HUD_ROW + 4. Glyphs from font.txt cover every pixel."""
    def glyph(name: str, left: int) -> None:
        for y, row in enumerate(FONT[name]):
            for x, char in enumerate(row):
                codes[HUD_ROW + y, left + x] = CODES[char]
    for k, digit in enumerate(f"{game.score:06d}"):
        glyph(digit, 4 + 4 * k)
    for i in range(min(max(game.lives - 1, 0), ICONS)):
        glyph("life", 120 - 4 * i)


def text(codes: np.ndarray, words: str, row: int, column: int, colour: str = "Y",
         big: bool = False) -> None:
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
                codes[row + scale * y : row + scale * (y + 1),
                      left + scale * x : left + scale * (x + 1)] = code


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
            text(codes, f"{i + 1:2d} {name} {score:06d}", 40 + 9 * i, 9,
                 "G" if i == game.new_rank else "Y")
        stamp(codes, "grunt", 36, 136)
        text(codes, "10", 138, 11)
        stamp(codes, "hunter", 76, 136)
        text(codes, "50", 138, 21)
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
        return picture(game)
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


def verify_ram(ram: bytes, symbols: dict[str, int], frame: int, variant: str) -> None:
    bufs = screens(frame, variant)
    for which in (0, 1):
        at = SCREENS[which]
        if ram[at : at + SCREEN_BYTES] != pack(bufs[which]):
            raise ValueError(f"Frame {frame}: the screen at ${at:04X} differs.")
    game = games(frame, variant)[frame]
    got = (ram[symbols["phase"]], ram[symbols["new_rank"]])
    if got != (game.phase, game.new_rank):
        raise ValueError(f"Frame {frame}: phase, new_rank = {got}, expected "
                         f"{(game.phase, game.new_rank)}.")
    table = ram[symbols["table"] : symbols["table"] + 60]
    want = b"".join(bytes.fromhex(f"{s:06d}") + n.encode() for s, n in game.table)
    if table != want:
        raise ValueError(f"Frame {frame}: the high-score table differs.")
    if game.phase == ENTRY:
        got = (bytes(ram[symbols["initials"] : symbols["initials"] + 3]).decode("latin-1"),
               ram[symbols["pos"]], ram[symbols["rpt"]])
        want = ("".join(game.initials), game.pos, game.rpt)
        if got != want:
            raise ValueError(f"Frame {frame}: initials, pos, rpt = {got}, expected {want}.")
    actual = tuple(ram[symbols[name]] for name in STATE_FIELDS)
    if actual != (game.x, game.y, game.delay):
        raise ValueError(f"Frame {frame}: px, py, delay = {actual}, expected "
                         f"{(game.x, game.y, game.delay)}.")
    if int.from_bytes(ram[symbols["frames"] : symbols["frames"] + 2], "big") != frame - 1:
        raise ValueError(f"Frame {frame}: the frame counter differs.")
    for i, shot in enumerate(game.slots):
        base = symbols["shots"] + i * SLOT_SIZE
        if bool(ram[base]) != bool(shot):
            raise ValueError(f"Frame {frame}: shot slot {i} on/off differs.")
        if shot:
            got = (ram[base + 1], ram[base + 2], ram[base + 3], ram[base + 4])
            want = (shot.x, shot.y, shot.vx & 0xFF, shot.vy & 0xFF)
            if got != want:
                raise ValueError(f"Frame {frame}: shot slot {i} is {got}, expected {want}.")
    bcd = int(ram[symbols["score"] : symbols["score"] + 3].hex())
    got = (bcd, ram[symbols["lives"]], ram[symbols["dying"]], ram[symbols["over"]],
           ram[symbols["ready"]])
    want = (game.score, game.lives, game.dying, game.over, game.ready)
    if got != want:
        raise ValueError(f"Frame {frame}: score, lives, dying, over, ready = {got}, "
                         f"expected {want}.")
    if ram[symbols["level"]] != game.level:
        raise ValueError(f"Frame {frame}: level {ram[symbols['level']]}, expected {game.level}.")
    for i, enemy in enumerate(game.enemies):
        base = symbols["enemies"] + i * ENEMY_SIZE
        got = tuple(ram[base : base + 4]) if ram[base] else None
        want = (enemy.kind, enemy.x, enemy.y, enemy.tick) if enemy else None
        if got != want:
            raise ValueError(f"Frame {frame}: enemy slot {i} is {got}, expected {want}.")


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
    window = sound.samples[-int(WINDOW_S * sound.rate):]
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
            f"{volume} ({want:.0f}) for {game.effect}.")
    gaps = np.diff(where)
    if mode == SQUARE:
        hz = (len(where) - 1) / (2 * (where[-1] - where[0]) / sound.rate)
        if abs(hz / square_hz(period) - 1) > 0.05:
            raise ValueError(f"Frame {frame}: {hz:.0f} Hz, expected {square_hz(period):.0f} Hz "
                             f"for {game.effect}.")
        return {"frame": frame, "sound": game.effect, "hz": round(hz)}
    if gaps.min() == gaps.max():
        raise ValueError(f"Frame {frame}: regular steps, expected noise for {game.effect}.")
    return {"frame": frame, "sound": game.effect, "noise_steps": len(where)}
