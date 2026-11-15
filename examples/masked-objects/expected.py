"""Independent pixel model of the masked-objects scenes in each draw method.

Written from the scene list, the ring shapes and the draw rules, not from the
assembly or its mask data.
"""

import numpy as np

# Scene inputs in pixels: A origin, B origin, inverted background, draw order
# (the last object wins).
SCENES = (
    (0, 0, 240, 182, False, "ab"),
    (240, 0, 0, 182, False, "ab"),
    (112, 88, 120, 88, False, "ab"),
    (112, 88, 120, 88, False, "ba"),
    (112, 88, 112, 88, False, "ab"),
    (112, 88, 112, 88, False, "ba"),
    (16, 20, 216, 160, False, "ab"),
    (16, 20, 216, 160, False, ""),
    (112, 88, 120, 88, True, "ab"),
    (112, 88, 120, 88, True, "ba"),
    (112, 88, 120, 88, True, ""),
    (0, 182, 240, 0, True, "ab"),
)
WIDTH, HEIGHT = 256, 192
OBJECT_WIDTH, OBJECT_HEIGHT = 16, 10
# RG6 with colour set 0: black and green. RGB values are the pinned XRoar's
# renderer output, as in examples/first-screen, not a monitor.
COLOURS = np.array([(0, 31, 0), (46, 188, 36)], dtype=np.uint8)
# coco.py's capture: two samples per RG6 pixel, one row per scan line.
SAMPLES_PER_PIXEL = 2


def ring_pixel(x: int, y: int, name: str) -> int | None:
    """Ink inside the 16x10 box: None is transparent, 0 is opaque black."""
    if not (0 <= x < 16 and 1 <= y <= 8):
        return None
    if y == 1:
        return int(name == "a")
    if y == 8:
        return int(name == "b")
    if x in (0, 15):
        return int((x == 0) == (name == "a"))
    return None


def draw(pixel: int, ink: int | None, method: str) -> int:
    """One pixel of the box drawn over one scenery pixel."""
    if method == "opaque":
        return ink or 0
    if method == "xor":
        return pixel ^ (ink or 0)
    return pixel if ink is None else ink


def pixels(frame: int, variant: str) -> list[list[int]]:
    """Colour codes of the screen after the Nth completed scene, scene N - 1."""
    ax, ay, bx, by, invert, order = SCENES[frame - 1]
    origins = {"a": (ax, ay), "b": (bx, by)}
    rows = [[(x // 8 + y // 8) % 2 ^ invert for x in range(WIDTH)] for y in range(HEIGHT)]
    for name in order:
        left, top = origins[name]
        for y in range(top, top + OBJECT_HEIGHT):
            for x in range(left, left + OBJECT_WIDTH):
                ink = ring_pixel(x - left, y - top, name)
                rows[y][x] = draw(rows[y][x], ink, variant or "mask")
    return rows


def expected_screen(frame: int, variant: str) -> bytes:
    """Eight pixels per byte, leftmost in bit 7 (MC6847 PDF 19 Table 3)."""
    result = bytearray(WIDTH * HEIGHT // 8)
    for y, row in enumerate(pixels(frame, variant)):
        for x, pixel in enumerate(row):
            if pixel:
                result[y * 32 + x // 8] |= 0x80 >> (x % 8)
    return bytes(result)


def expected_frame(frame: int, variant: str) -> np.ndarray:
    """The rendered 512x192 picture: each pixel spans two samples."""
    codes = np.array(pixels(frame, variant), dtype=np.uint8)
    return COLOURS[np.repeat(codes, SAMPLES_PER_PIXEL, axis=1)]
