"""Independent model of the tile room after each scripted move, in each redraw method.

Written from the room drawing, the movement rules, the move script and text
drawings of the pictures, not from the assembly, tiles.png or the converted
bytes. Both redraw methods must show the same picture at every frame.
"""

import numpy as np

# The room: floor ".", wall "#", collectible "*", exit "E". The actor starts
# at column 0, row 0. Walls and the room edge refuse a move.
ROOM = ("..#.....", ".*#..#..", "..#.....", "....##..", ".#......", "......E.")
# The script of requested moves: right, down, left, up.
MOVES = "LURRDDDRURUUUURRDRRRDDDDDDLRLLLLLULULUUDU"
STEPS = {"R": (1, 0), "D": (0, 1), "L": (-1, 0), "U": (0, -1)}
# The pictures as text drawings, "#" lit: floor, wall, collectible, exit, actor.
ART = {
    ".": ("........",) * 8,
    "#": (
        "########",
        "#......#",
        "#......#",
        "########",
        "...##...",
        "...##...",
        "...##...",
        "########",
    ),
    "*": (
        "........",
        "........",
        "...##...",
        "..####..",
        "..####..",
        "...##...",
        "........",
        "........",
    ),
    "E": (
        ".######.",
        ".#....#.",
        ".#.##.#.",
        ".#.#..#.",
        ".#.##.#.",
        ".#....#.",
        ".######.",
        "........",
    ),
    "@": (
        "...##...",
        "..####..",
        ".######.",
        "##.##.##",
        "########",
        "..#..#..",
        "..#..#..",
        ".##..##.",
    ),
}
WIDTH, HEIGHT, CELL = 256, 192, 8
# RG6 with colour set 0: black and green. RGB values are the pinned XRoar's
# renderer output, as in examples/first-screen, not a monitor.
COLOURS = np.array([(0, 31, 0), (46, 188, 36)], dtype=np.uint8)
# coco.py's capture: two samples per RG6 pixel, one row per scan line.
SAMPLES_PER_PIXEL = 2


def room_after(moves: int) -> tuple[list[list[str]], tuple[int, int]]:
    """The room and the actor's cell after the first moves of the script."""
    room = [list(row) for row in ROOM]
    x, y = 0, 0
    for move in MOVES[:moves]:
        dx, dy = STEPS[move]
        nx, ny = x + dx, y + dy
        if 0 <= nx < len(room[0]) and 0 <= ny < len(room) and room[ny][nx] != "#":
            x, y = nx, ny
            if room[y][x] == "*":
                room[y][x] = "."
    return room, (x, y)


def pixels(frame: int) -> list[list[int]]:
    """Frame N shows the room after N - 1 moves. The rest of the screen is black."""
    room, actor = room_after(frame - 1)
    rows = [[0] * WIDTH for _ in range(HEIGHT)]
    for row, cells in enumerate(room):
        for column, cell in enumerate(cells):
            art = ART["@" if (column, row) == actor else cell]
            for y, line in enumerate(art):
                for x, mark in enumerate(line):
                    rows[row * CELL + y][column * CELL + x] = int(mark == "#")
    return rows


def expected_screen(frame: int, variant: str) -> bytes:
    """Eight pixels per byte, leftmost in bit 7 (MC6847 PDF 19 Table 3)."""
    result = bytearray(WIDTH * HEIGHT // 8)
    for y, row in enumerate(pixels(frame)):
        for x, pixel in enumerate(row):
            if pixel:
                result[y * 32 + x // 8] |= 0x80 >> (x % 8)
    return bytes(result)


def expected_frame(frame: int, variant: str) -> np.ndarray:
    """The rendered 512x192 picture: each pixel spans two samples."""
    codes = np.array(pixels(frame), dtype=np.uint8)
    return COLOURS[np.repeat(codes, SAMPLES_PER_PIXEL, axis=1)]
