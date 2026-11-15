"""Independent pixel model of the moving-objects scene.

Written from the scene rules in README.md, not from the assembly. All three
methods must show the same picture: a correct restore leaves no trace of the
old object positions.
"""

import numpy as np

WIDTH, HEIGHT = 256, 192
OBJECT_WIDTH, OBJECT_HEIGHT = 16, 8
# RG6 with colour set 0: black and green. RGB values are the pinned XRoar's
# renderer output, as in examples/first-screen, not a monitor.
COLOURS = np.array([(0, 31, 0), (46, 188, 36)], dtype=np.uint8)
# coco.py's capture: two samples per RG6 pixel, one row per scan line.
SAMPLES_PER_PIXEL = 2


def position(frame: int) -> tuple[int, int]:
    """Byte column of A (0 to 30) and pixel row of both (0 to 184).

    Both start at 0 and move one step per frame. Each reverses at its last
    position that keeps the object on the screen.
    """
    tick = frame - 1
    return 30 - abs(tick % 60 - 30), 184 - abs(tick % 368 - 184)


def pixels(frame: int) -> np.ndarray:
    """192 x 256 colour codes: checker scenery, then A (green) and B (black)."""
    y, x = np.mgrid[0:HEIGHT, 0:WIDTH]
    lit = ((x // 8 + y // 8) % 2).astype(bool) ^ bool(frame & 64)
    column, top = position(frame)
    lefts = {"a": column * 8, "b": (30 - column) * 8}
    # The object drawn last is on top. The order swaps every 32 frames.
    for name in ("b", "a") if frame & 32 else ("a", "b"):
        left = lefts[name]
        inside = (left <= x) & (x < left + OBJECT_WIDTH) & (top <= y) & (y < top + OBJECT_HEIGHT)
        lit[inside] = name == "a"
    return lit.astype(np.uint8)


def expected_screen(frame: int, variant: str) -> bytes:
    """Eight pixels per byte, leftmost in bit 7 (MC6847 PDF 19 Table 3)."""
    return np.packbits(pixels(frame), axis=1).tobytes()


def expected_frame(frame: int, variant: str) -> np.ndarray:
    """The rendered 512x192 picture: each pixel spans two samples."""
    return COLOURS[np.repeat(pixels(frame), SAMPLES_PER_PIXEL, axis=1)]
