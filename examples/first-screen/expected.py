"""Independent model of the display-setup picture in each VDG full-graphics mode.

Written from the mode table and the picture rule, not from the assembly.
"""

import numpy as np

# Variant: (width, height, bits per pixel, half-clocks per pixel, scan lines per pixel).
# MC6847 datasheet PDF 18 Table 2 and PDF 20; Tandy Technical Reference PDF 30.
MODES = {
    "": (128, 192, 2, 2, 1),  # CG6, PMODE 3
    "rg6": (256, 192, 1, 1, 1),  # PMODE 4
    "rg3": (128, 192, 1, 2, 1),  # PMODE 2
    "cg3": (128, 96, 2, 2, 2),  # PMODE 1
    "rg2": (128, 96, 1, 2, 2),  # PMODE 0
    "cg2": (128, 64, 2, 2, 3),
    "rg1": (128, 64, 1, 2, 3),
    "cg1": (64, 64, 2, 4, 3),
}
# Colour set 0. Codes 0-3 in four-colour modes; codes 0-1 in two-colour modes.
# RGB values are the pinned XRoar's renderer output (the `xroar` palette in
# scripts/graphics.py, measured by examples/palette-swatches), not a monitor.
FOUR_COLOURS = [(46, 188, 36), (255, 255, 151), (44, 37, 129), (131, 26, 55)]
TWO_COLOURS = [(0, 31, 0), (46, 188, 36)]
# coco.py's capture: two samples per VDG half-clock, one row per scan line.
SAMPLES_PER_HALF_CLOCK = 2


def pixel(x: int, y: int, variant: str) -> int:
    """Colour code: a one-pixel border in the last code, inside four bars."""
    width, height, bits, _, _ = MODES[variant]
    last = (1 << bits) - 1
    if x in (0, width - 1) or y in (0, height - 1):
        return last
    bar = 4 * x // width
    if bits == 2:
        return (1, 2, 3, 0)[bar]  # yellow, blue, red, green
    return (x % 2, 1 - x % 2, 1, 0)[bar]  # stripes, stripes, solid, unlit


def expected_screen(frame: int, variant: str) -> bytes:
    """Leftmost pixel in the high bits of each byte (MC6847 PDF 19 Table 3)."""
    width, height, bits, _, _ = MODES[variant]
    per_byte = 8 // bits
    result = bytearray(width * height // per_byte)
    for y in range(height):
        for x in range(width):
            shift = 8 - bits * (x % per_byte + 1)
            result[(y * width + x) // per_byte] |= pixel(x, y, variant) << shift
    return bytes(result)


def expected_frame(frame: int, variant: str) -> np.ndarray:
    """The rendered 512x192 picture: each pixel spans its half-clocks and lines."""
    width, height, bits, half_clocks, lines = MODES[variant]
    colours = FOUR_COLOURS if bits == 2 else TWO_COLOURS
    across = half_clocks * SAMPLES_PER_HALF_CLOCK
    rows = [
        [colours[pixel(s // across, line // lines, variant)] for s in range(width * across)]
        for line in range(height * lines)
    ]
    return np.array(rows, dtype=np.uint8)
