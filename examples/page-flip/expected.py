"""Independent model of the page-flip frames: both screens and the picture.

Written from the scene description in README.md and the two-screen rule, not
from the assembly. Frame N is drawn into one screen and then shown, so at the
checkpoint for frame N the shown screen holds frame N complete, and the other
screen still holds frame N - 1.

Variants: "" (RG6, SAM offset flip, every target) and "coco3" (GIME native
256x192 two-colour graphics, $FF9D flip, CoCo 3 targets only). Both builds
draw the same bytes into the same CPU addresses.
"""

import numpy as np
from graphics import MODES, XROAR, XROAR_COCO3, palette_rgb

WIDTH, HEIGHT = 256, 192
SCREEN_BYTES = WIDTH * HEIGHT // 8
# CPU addresses. Odd frames are drawn at $2400, even frames at $0400.
SCREENS = {0: 0x0400, 1: 0x2400}
# The snapshot holds physical RAM. On a CoCo 3, BASIC's map puts CPU $xxxx at
# physical $7xxxx (Tepolt PDF 56, step 6). A 128 KiB CoCo 3 holds the same
# RAM at $1xxxx (Tepolt PDF 29), and its snapshot has 128 KiB.
OFFSETS = {"coco1": 0, "coco2": 0, "coco2b": 0, "coco3": 0x10000, "coco3-512": 0x70000}
# coco.py's capture: two samples per pixel at 256 pixels across. Measured in
# XRoar: the CoCo 3 captures, native mode too, have the same size and position.
SAMPLES_PER_PIXEL = 2


def colours(variant: str, target: str) -> np.ndarray:
    """RGB for pixel bits 0 and 1. The RGB values are measured in XRoar.

    RG6 with colour set 0 shows black and green (MC6847 PDF 21). On a CoCo 3
    the two codes select palette registers 8 and 9 (Tepolt PDF 46). In the
    native two-colour mode a bit selects palette register 0 or 1 (Tepolt
    PDF 39), the registers of CG codes 0 and 1. BASIC loads them all (Tepolt
    PDF 57, step 44), and the program keeps them.
    """
    if variant == "coco3":
        return palette_rgb(MODES["CG6"], 0, XROAR_COCO3)[:2]
    return palette_rgb(MODES["RG6"], 0, XROAR_COCO3 if target.startswith("coco3") else XROAR)


def position(frame: int) -> tuple[int, int]:
    """Byte column of rectangle A (0..30) and pixel row of both (0..184).

    Both start at 0 and move one step each frame, back and forth.
    """
    tick = frame - 1
    return 30 - abs(tick % 60 - 30), 184 - abs(tick % 368 - 184)


def lit(frame: int) -> np.ndarray:
    """192 x 256 pixel bits: checker scenery, then A (1) and B (0) in order."""
    y, x = np.mgrid[0:HEIGHT, 0:WIDTH]
    pixels = ((x // 8 + y // 8) % 2).astype(bool) ^ bool(frame & 64)
    column, top = position(frame)
    lefts = {"a": column * 8, "b": (30 - column) * 8}
    for name in ("b", "a") if frame & 32 else ("a", "b"):
        inside = (lefts[name] <= x) & (x < lefts[name] + 16) & (top <= y) & (y < top + 8)
        pixels[inside] = name == "a"
    return pixels


def screen_bytes(frame: int) -> bytes:
    """Eight pixels per byte, leftmost in bit 7 (MC6847 PDF 19 Table 3,
    Tepolt PDF 38)."""
    return np.packbits(lit(frame), axis=1).tobytes()


def verify_ram(ram: bytes, symbols: dict[str, int], frame: int, variant: str, target: str) -> None:
    """The shown screen holds frame N; the other screen still holds frame N - 1."""
    shown = OFFSETS[target] + SCREENS[frame % 2]
    if ram[shown : shown + SCREEN_BYTES] != screen_bytes(frame):
        raise ValueError(f"The screen at ${shown:05X} does not hold frame {frame}.")
    if frame > 1:
        other = OFFSETS[target] + SCREENS[(frame - 1) % 2]
        if ram[other : other + SCREEN_BYTES] != screen_bytes(frame - 1):
            raise ValueError(f"The screen at ${other:05X} does not hold frame {frame - 1}.")


def expected_frame(frame: int, variant: str, target: str) -> np.ndarray:
    """The rendered 512x192 picture: frame N, complete."""
    wide = np.repeat(lit(frame), SAMPLES_PER_PIXEL, axis=1)
    return colours(variant, target)[wide.astype(np.uint8)]
