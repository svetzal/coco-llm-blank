"""Independent model of Collect room: hand-transcribed art, map rules and a scripted journey.

Nothing here is derived from the assembly, the asset converter or captured RAM.
"""

import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
MESSAGES = ("SPACE TO START", "COLLECT BOTH THEN EXIT", "YOU WIN SPACE RESTART")
ACTOR = bytes.fromhex("183c7edbff242466")
# Hand-transcribed original art rows, independent of converter/assembly output.
ART = tuple(
    bytes.fromhex(s)
    for s in ("0000200000000000", "ff80b8a0ae8280fd", "2070f87020000200", "e080a0a4be8480c1")
) + (ACTOR,)
ROOM = ("..#.....", ".*#..#..", "..#.....", "....##..", ".#...*..", "......E.")
FIELDS = ("phase", "xpos", "ypos", "remaining", "accepted", "starts", "effects", "last_effect")
# Title screen with nothing pressed: the state every idle frame must keep.
TITLE = (0, 0, 0, 2, 0, 0, 0, 0, 0)
# The pinned XRoar's RG6 colours for colour set 0 through coco.py's renderer settings,
# measured by examples/palette-swatches. Emulator RGB values, not a monitor.
BLACK, GREEN = (0, 31, 0), (46, 188, 36)
# Each effect is 32 alternating DAC writes. The game's requirement: the pickup
# tone is highest and the win tone lowest, each within its own band.
EFFECT_WRITES = 32
EFFECT_HZ = {1: (900, 1100), 2: (1550, 1950), 3: (600, 800)}
# A DAC step larger than this is an effect write; idle output changes much less.
STEP_THRESHOLD = 8192
# Writes in one effect are under 1 ms apart; effects are a whole update apart.
EFFECT_GAP_SECONDS = 0.005


def journey() -> list[tuple[str, tuple[int, ...]]]:
    """Read hand-authored expectations, never derive them from observed RAM."""
    return [
        (parts[0], tuple(map(int, parts[1:])))
        for line in (HERE / "journey.txt").read_text().splitlines()
        if (parts := line.split()) and not line.startswith("#")
    ]


def expected_room(collected: int) -> bytes:
    cells = bytearray(".#*E".index(c) for row in ROOM for c in row)
    if collected & 1:
        cells[9] = 0
    if collected & 2:
        cells[37] = 0
    return bytes(cells)


def expected_pixel(x: int, y: int, cells: bytes, actor: tuple[int, int]) -> int:
    if not (64 <= x < 192 and 48 <= y < 144):
        return 0
    cx, cy = (x - 64) // 16, (y - 48) // 16
    tile = 4 if (cx, cy) == actor else cells[cy * 8 + cx]
    return ART[tile][((y - 48) % 16) // 2] & (128 >> (((x - 64) % 16) // 2))


def screen_for_state(state: tuple[int, ...]) -> bytes:
    """Independent per-pixel oracle, without expanded assets or packed headers."""
    phase, actor_x, actor_y, *_ = state
    cells = expected_room(state[8])
    font = json.loads((HERE / "letters.json").read_text())
    screen = bytearray(6144)
    for y in range(192):
        for x in range(256):
            bit = expected_pixel(x, y, cells, (actor_x, actor_y))
            column, subpixel = divmod(x - 16, 6)
            if 16 <= y < 23 and 0 <= column < len(MESSAGES[phase]) and subpixel < 5:
                bit = font[MESSAGES[phase][column]][y - 16] & (16 >> subpixel)
            if bit:
                screen[y * 32 + x // 8] |= 128 >> (x % 8)
    return bytes(screen)


def verify_journey_frame(
    ram: bytes, labels: dict[str, int], keys: str, state: tuple[int, ...]
) -> None:
    """Guards, game state, keyboard history, room, sound burst and the whole screen."""
    if len(ram) not in (32768, 65536):
        raise ValueError("Missing/truncated RAM")
    guards = [0x3FF, 0x1C00] + [
        labels[n]
        for n in ("map_guard_before", "map_guard_after", "asset_guard_before", "asset_guard_after")
    ]
    if any(ram[a] != 0xA5 for a in guards):
        raise ValueError("Memory guard damaged")
    if tuple(ram[labels[n]] for n in FIELDS) != state[:8]:
        raise ValueError(f"Game state differs: {tuple(ram[labels[n]] for n in FIELDS)} != {state}")
    held = sum(bit for char, bit in zip("UDLRF", (1, 2, 4, 8, 16)) if char in keys)
    if ram[labels["held"]] != held or ram[labels["previous"]] != held:
        raise ValueError("Keyboard/history differs")
    if ram[labels["room"] : labels["room"] + 48] != expected_room(state[8]):
        raise ValueError("Room lifecycle differs")
    samples = int.from_bytes(ram[labels["sample_count"] : labels["sample_count"] + 2], "big")
    if samples != state[6] * 32 or ram[labels["sound_count"]] != 0:
        raise ValueError("Sound burst did not finish")
    if ram[0x400:0x1C00] != screen_for_state(state):
        raise ValueError("Complete framebuffer differs")


def step(frame: int, variant: str) -> tuple[str, tuple[int, ...]]:
    """Keys held and state expected at a checkpoint: the journey, or idle on the title."""
    return journey()[frame - 1] if variant == "journey" else ("-", TITLE)


def expected_screen(frame: int, variant: str = "") -> bytes:
    """Without injected keys, every frame stays on the title screen."""
    return screen_for_state(step(frame, variant)[1])


def expected_frame(frame: int, variant: str = "") -> np.ndarray:
    """The rendered picture: two samples per pixel, XRoar's RG6 green or black (CSS=0)."""
    lit = np.unpackbits(np.frombuffer(expected_screen(frame, variant), np.uint8)).reshape(192, 256)
    wide = np.repeat(lit.astype(bool), 2, axis=1)
    return np.where(wide[:, :, None], np.array(GREEN), np.array(BLACK)).astype(np.uint8)


def verify_ram(ram: bytes, symbols: dict[str, int], frame: int, variant: str = "") -> None:
    verify_journey_frame(ram, symbols, *step(frame, variant))


def expected_effects(frame: int, variant: str = "") -> list[int]:
    """Effect kinds (1 start, 2 pickup, 3 win) played up to a checkpoint, from journey.txt."""
    if variant != "journey":
        return []
    kinds, played = [], 0
    for _, state in journey()[:frame]:
        if state[6] != played:
            if state[6] != played + 1:
                raise ValueError("journey.txt adds more than one effect in one step")
            kinds.append(state[7])
            played = state[6]
    return kinds


def effect_bursts(samples: np.ndarray, rate: int) -> list[tuple[int, float]]:
    """(writes, Hz) of each group of large DAC steps in XRoar's mixer output."""
    steps = np.nonzero(np.abs(np.diff(samples.astype(np.int32))) > STEP_THRESHOLD)[0]
    if not len(steps):
        return []
    breaks = np.nonzero(np.diff(steps) > EFFECT_GAP_SECONDS * rate)[0] + 1
    bursts = []
    for group in np.split(steps, breaks):
        span = (group[-1] - group[0]) / rate
        bursts.append((len(group), (len(group) - 1) / (2 * span) if span else 0.0))
    return bursts


def verify_sound(sound, frame: int, variant: str = "") -> dict[str, object]:
    """Every effect so far is in the mixer output: 32 writes each, in its pitch band."""
    expected = expected_effects(frame, variant)
    bursts = effect_bursts(sound.samples, sound.rate)
    if len(bursts) != len(expected):
        raise ValueError(
            f"Frame {frame}: the mixer output has {len(bursts)} effects, expected {len(expected)}."
        )
    for number, (kind, (writes, hz)) in enumerate(zip(expected, bursts, strict=True), 1):
        low, high = EFFECT_HZ[kind]
        if writes != EFFECT_WRITES or not low <= hz <= high:
            raise ValueError(
                f"Frame {frame}: effect {number} has {writes} steps at {hz:.0f} Hz, "
                f"expected {EFFECT_WRITES} at {low}-{high} Hz."
            )
    return {"frame": frame, "effects": len(bursts), "hz": [round(hz, 1) for _, hz in bursts]}
