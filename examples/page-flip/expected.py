"""Independent model of the page-flip frames: both screens and the picture.

Written from the scene description in README.md and the two-screen rule, not
from the assembly. Frame N is drawn into one screen and then shown, so at the
checkpoint for frame N the shown screen holds frame N complete, and the other
screen still holds frame N - 1.
"""

import numpy as np

WIDTH, HEIGHT = 256, 192
SCREEN_BYTES = WIDTH * HEIGHT // 8
# Odd frames are drawn at $2400, even frames at $0400.
SCREENS = {0: 0x0400, 1: 0x2400}
# RG6 with colour set 0: black and green. RGB values are the pinned XRoar's
# renderer output, as in examples/first-screen, not a monitor.
BLACK, GREEN = (0, 31, 0), (46, 188, 36)
# coco.py's capture: two samples per RG6 pixel, one row per scan line.
SAMPLES_PER_PIXEL = 2


def position(frame: int) -> tuple[int, int]:
    """Byte column of rectangle A (0..30) and pixel row of both (0..184).

    Both start at 0 and move one step each frame, back and forth.
    """
    tick = frame - 1
    return 30 - abs(tick % 60 - 30), 184 - abs(tick % 368 - 184)


def lit(frame: int) -> np.ndarray:
    """192 x 256 pixels: checker scenery, then A (lit) and B (unlit) in order."""
    y, x = np.mgrid[0:HEIGHT, 0:WIDTH]
    pixels = ((x // 8 + y // 8) % 2).astype(bool) ^ bool(frame & 64)
    column, top = position(frame)
    lefts = {"a": column * 8, "b": (30 - column) * 8}
    for name in ("b", "a") if frame & 32 else ("a", "b"):
        inside = (lefts[name] <= x) & (x < lefts[name] + 16) & (top <= y) & (y < top + 8)
        pixels[inside] = name == "a"
    return pixels


def screen_bytes(frame: int) -> bytes:
    """Eight pixels per byte, leftmost in bit 7 (MC6847 PDF 19 Table 3)."""
    return np.packbits(lit(frame), axis=1).tobytes()


def verify_ram(ram: bytes, symbols: dict[str, int], frame: int) -> None:
    """The shown screen holds frame N; the other screen still holds frame N - 1."""
    shown = SCREENS[frame % 2]
    if ram[shown : shown + SCREEN_BYTES] != screen_bytes(frame):
        raise ValueError(f"The screen at ${shown:04X} does not hold frame {frame}.")
    if frame > 1:
        other = SCREENS[(frame - 1) % 2]
        if ram[other : other + SCREEN_BYTES] != screen_bytes(frame - 1):
            raise ValueError(f"The screen at ${other:04X} does not hold frame {frame - 1}.")


def expected_frame(frame: int) -> np.ndarray:
    """The rendered 512x192 picture: frame N, complete."""
    wide = np.repeat(lit(frame), SAMPLES_PER_PIXEL, axis=1)
    return np.where(wide[:, :, None], np.array(GREEN), np.array(BLACK)).astype(np.uint8)
