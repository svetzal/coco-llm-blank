"""Independent model of the palette swatches: written from the layout, not the assembly.

Functions take the build variant: "" (CG6, CSS=0), "css1" (CG6, CSS=1), "rg6" (RG6, CSS=0)
or "rg6-css1" (RG6, CSS=1). Every variant writes the same screen bytes.

The rendered frame is drawn with scripts/graphics.py's unpack and render and its `xroar`
palette, so `check --video` tests that palette, the unpacking bit order and the pixel sizes
against XRoar's renderer.
"""

import numpy as np
from graphics import MODES, XROAR, render, unpack

SCREEN_BYTES = 6144
BYTES_PER_ROW = 32
BAR_ROWS = 160
READY_MARKER = 0x2FFF
# Rows 0-159: four bars, 8 bytes each. Every pixel pair in a byte holds one code, so the
# CG6 bars are codes 0, 1, 2, 3 from the left.
BAR_BYTES = (0x00, 0x55, 0xAA, 0xFF)
# Rows 160-191: 00 01 10 11 in every byte, codes 0, 1, 2, 3 from the left in CG6.
ORDER_BYTE = 0x1B
VARIANTS = {"": ("CG6", 0), "css1": ("CG6", 1), "rg6": ("RG6", 0), "rg6-css1": ("RG6", 1)}
# scripts/coco.py's capture: two samples per VDG half-clock, one row per scan line.
SAMPLES_PER_HALF_CLOCK = 2


def expected_screen(frame: int, variant: str) -> bytes:
    bar_row = b"".join(bytes([value]) * 8 for value in BAR_BYTES)
    order_row = bytes([ORDER_BYTE]) * BYTES_PER_ROW
    return bar_row * BAR_ROWS + order_row * (SCREEN_BYTES // BYTES_PER_ROW - BAR_ROWS)


def expected_frame(frame: int, variant: str) -> np.ndarray:
    """XRoar's picture of the screen bytes in the variant's mode and colour set."""
    name, css = VARIANTS[variant]
    mode = MODES[name]
    codes = unpack(expected_screen(frame, variant), mode.width, mode.height, mode.bits_per_pixel)
    return render(codes, mode, css, XROAR, SAMPLES_PER_HALF_CLOCK)


def verify_ram(ram: bytes, symbols: dict[str, int], frame: int, variant: str) -> None:
    if len(ram) != 32768 or ram[READY_MARKER] != 0xA5:
        raise ValueError("The emulator did not reach the initialized program state.")
