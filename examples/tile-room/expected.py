"""Independent model of the tile room: a graph walk and hand-drawn pixel art."""

import numpy as np

ROOM = ("..#.....", ".*#..#..", "..#.....", "....##..", ".#......", "......E.")
# The pinned XRoar's two RG6 colours for colour set 0, as in examples/first-screen.
BLACK, GREEN = (0, 31, 0), (46, 188, 36)
# Specification of requested directions, not read from the assembly or RAM.
MOVES = "LURRDDDRURUUUURRDRRRDDDDDDLRLLLLLULULUUDU"
# Pixel drawings are independent of tiles.png and of the converted bytes.
ART = (
    ("........",) * 8,
    (
        "########",
        "#......#",
        "#......#",
        "########",
        "...##...",
        "...##...",
        "...##...",
        "########",
    ),
    (
        "........",
        "........",
        "...##...",
        "..####..",
        "..####..",
        "...##...",
        "........",
        "........",
    ),
    (
        ".######.",
        ".#....#.",
        ".#.##.#.",
        ".#.#..#.",
        ".#.##.#.",
        ".#....#.",
        ".######.",
        "........",
    ),
    (
        "...##...",
        "..####..",
        ".######.",
        "##.##.##",
        "########",
        "..#..#..",
        "..#..#..",
        ".##..##.",
    ),
)


def expected_state(step: int) -> tuple[tuple[int, int], bytes, int]:
    """Walk a graph of passable cells, independent of assembly address arithmetic."""
    if not 0 <= step <= len(MOVES):
        raise ValueError("Checkpoint outside the scripted movement.")
    cells = {(x, y): value for y, row in enumerate(ROOM) for x, value in enumerate(row)}
    edges = {}
    for x, y in cells:
        for direction, neighbor in zip("RDLU", ((x + 1, y), (x, y + 1), (x - 1, y), (x, y - 1))):
            if cells.get(neighbor, "#") != "#":
                edges[(x, y), direction] = neighbor
    position, accepted = (0, 0), 0
    for direction in MOVES[:step]:
        next_position = edges.get((position, direction), position)
        accepted = int(next_position != position)
        position = next_position
        if cells[position] == "*":
            cells[position] = "."
    return position, bytes(".#*E".index(value) for value in cells.values()), accepted


def expected_screen(frame: int) -> bytes:
    """Frame N shows the room after N - 1 moves, composed pixel by pixel, blank space included."""
    actor, room, _ = expected_state(frame - 1)
    screen = bytearray(6144)
    for y in range(48):
        for x in range(64):
            cell = (x // 8, y // 8)
            tile = 4 if cell == actor else room[cell[1] * 8 + cell[0]]
            if ART[tile][y % 8][x % 8] == "#":
                screen[y * 32 + x // 8] |= 128 >> (x % 8)
    return bytes(screen)


def expected_frame(frame: int) -> np.ndarray:
    """The rendered picture: two samples per pixel, XRoar's RG6 green or black (CSS=0)."""
    lit = np.unpackbits(np.frombuffer(expected_screen(frame), np.uint8)).reshape(192, 256)
    wide = np.repeat(lit.astype(bool), 2, axis=1)
    return np.where(wide[:, :, None], np.array(GREEN), np.array(BLACK)).astype(np.uint8)


def verify_ram(data: bytes, symbols: dict[str, int], frame: int) -> None:
    """Check state, complete map, guards, and every screen byte at a checkpoint."""
    step = frame - 1
    guards = (0x03FF, 0x1C00, symbols["map_guard_before"], symbols["map_guard_after"])
    if len(data) != 32768 or any(data[address] != 0xA5 for address in guards):
        raise ValueError("Missing RAM or damaged guards.")
    position, room, accepted = expected_state(step)
    observed = tuple(data[symbols[name]] for name in ("xpos", "ypos", "accepted", "step"))
    if observed != (*position, accepted, step):
        raise ValueError(f"Movement checkpoint {step} differs: {observed}.")
    if data[symbols["room"] : symbols["room"] + 48] != room:
        raise ValueError("Map state differs, including collected tile.")
    if data[0x0400:0x1C00] != expected_screen(frame):
        raise ValueError("Framebuffer differs from the independent pixel scene.")
