"""Independent model of Arena Blaster: the rules for each frame, the arena and the sprites.

Written from the rules and the design in README.md and the art in sprites.txt. It does
not use main.asm, assets.py, the assembled bytes or a captured snapshot. It reads the
key script and simulates each frame. Then it draws each screen pixel by pixel and packs
the pixels itself.

Frame N is drawn into the hidden screen and then shown. Odd frames are at $2400 and even
frames at $0400. At the checkpoint for frame N the shown screen holds frame N and the
other screen still holds frame N - 1 (or only the arena, at frame 1).
"""

import copy
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
SHOT_SLOTS, SHOT_DELAY = 6, 5
# Movement keys and shoot keys: (dx, dy) for each key letter in the key script.
MOVE = {"E": (0, -1), "C": (0, 1), "S": (-1, 0), "F": (1, 0)}
SHOOT = {"I": (0, -1), ",": (0, 1), "J": (-1, 0), "L": (1, 0)}
# The scanner's labels in RAM that the check compares.
STATE_FIELDS = ("px", "py", "delay")
SLOT_SIZE = 11  # on, x, y, vx, vy, sprite (2), maxx, maxy, w, h
# Enemies (README.md "Levels and enemies").
ENEMY_SLOTS, ENEMY_SIZE = 24, 4  # type, x, y, tick
ENEMY_W, ENEMY_H = 6, 10
GRUNT, HUNTER = 1, 2
PERIOD = {GRUNT: 4, HUNTER: 2}
SPRITE = {GRUNT: "grunt", HUNTER: "hunter"}
SEED = 0xACE1
START_LEVEL = {"": 1, "journey": 1, "hunters": 10}
SCRIPTS = {"journey": "journey.txt", "hunters": "hunters.txt"}
SAFE_X, SAFE_Y = 28, 45


def sprites() -> dict[str, list[str]]:
    art: dict[str, list[str]] = {}
    name = ""
    for line in (HERE / "sprites.txt").read_text().splitlines():
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
    game.hunter_wait = game.hunter_timer = max(90, 660 - 60 * game.level)
    for slot in range(min(20, 4 + 2 * game.level)):
        while True:
            x = game.random_x()
            y = game.random_y()
            if not (abs(x - START[0]) <= SAFE_X and abs(y - START[1]) <= SAFE_Y):
                break
        game.enemies[slot] = Enemy(GRUNT, x, y, slot % 4 + 1)


def new_game(variant: str) -> Game:
    game = Game(level=START_LEVEL[variant])
    start_level(game)
    return game


def toward(value: int, target: int, most: int) -> int:
    return value + max(-most, min(most, target - value))


def move_enemies(game: Game) -> None:
    for enemy in game.enemies:
        if enemy:
            enemy.tick -= 1
            if enemy.tick == 0:
                enemy.tick = PERIOD[enemy.kind]
                enemy.x = toward(enemy.x, game.x, 1)
                enemy.y = toward(enemy.y, game.y, 2)


def spawn_hunter(game: Game) -> None:
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
                break


def touched(game: Game) -> bool:
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


def step(game: Game, keys: str) -> None:
    """One frame of the rules in README.md."""
    game.rand_step()
    dx, dy = direction(keys, MOVE)
    game.x = min(max(game.x + dx, MIN_X), END_X - PLAYER_W)
    game.y = min(max(game.y + 2 * dy, MIN_Y), END_Y - PLAYER_H)
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
        start_level(game)
    elif not any(game.enemies):
        game.level += 1
        start_level(game)


def fire(game: Game, keys: str) -> None:
    if game.delay > 0:
        game.delay -= 1
        return
    fx, fy = direction(keys, SHOOT)
    if (fx, fy) == (0, 0) or None not in game.slots:
        return
    name = shot_sprite(fx, fy)
    w, h = size(name)
    shot = Shot(game.x + (PLAYER_W - w) // 2, game.y + (PLAYER_H - h) // 2, 3 * fx, 6 * fy, name)
    game.slots[game.slots.index(None)] = shot
    game.delay = SHOT_DELAY


def journey(name: str = "journey.txt") -> list[tuple[str, tuple[int, int] | None]]:
    """Held keys for each frame, and the player position where the script gives one."""
    steps = []
    for line in (HERE / name).read_text().splitlines():
        parts = line.split("#")[0].split()
        if parts:
            keys = "" if parts[0] == "-" else parts[0]
            steps.append((keys, (int(parts[1]), int(parts[2])) if len(parts) >= 3 else None))
    return steps


def games(frames: int, variant: str) -> list[Game]:
    """The state after each frame 0..frames. Frame 0 is the start."""
    script = journey(SCRIPTS[variant]) if variant in SCRIPTS else []
    game = new_game(variant)
    result = [copy.deepcopy(game)]
    for n in range(frames):
        keys, position = script[n] if n < len(script) else ("", None)
        step(game, keys)
        if position is not None and position != (game.x, game.y):
            raise ValueError(
                f"journey.txt line for frame {n + 1} gives {position}, the rules give "
                f"{(game.x, game.y)}: correct the script or the rules."
            )
        result.append(copy.deepcopy(game))
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
    return codes


def pack(codes: np.ndarray) -> bytes:
    """Four pixels per byte, leftmost pixel in bits 7-6 (MC6847 PDF 19 Table 3)."""
    c = codes.astype(np.uint8)
    return (c[:, 0::4] << 6 | c[:, 1::4] << 4 | c[:, 2::4] << 2 | c[:, 3::4]).tobytes()


def verify_ram(ram: bytes, symbols: dict[str, int], frame: int, variant: str) -> None:
    states = games(frame, variant)
    shown = SCREENS[frame % 2]
    if ram[shown : shown + SCREEN_BYTES] != pack(picture(states[frame])):
        raise ValueError(f"The screen at ${shown:04X} does not hold frame {frame}.")
    other = SCREENS[(frame - 1) % 2]
    previous = states[frame - 1] if frame > 1 else None
    if ram[other : other + SCREEN_BYTES] != pack(picture(previous)):
        raise ValueError(f"The screen at ${other:04X} does not hold frame {frame - 1}.")
    game = states[frame]
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
    return render(picture(games(frame, variant)[frame]), MODES["CG6"], 0, XROAR, 2)
