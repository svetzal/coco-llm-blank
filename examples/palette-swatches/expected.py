"""Independent model of the palette swatches in each colour set and mode.

Written from the picture rule and the MC6847 datasheet, not from the assembly.
Variants: "" (CG6, CSS=0), "css1" (CG6, CSS=1), "rg6" (RG6, CSS=0) and
"rg6-css1" (RG6, CSS=1). Every variant writes the same screen bytes.

The rendered frame uses scripts/graphics.py's unpack and render with its `xroar`
palette on coco1, coco2 and coco2b, and its `xroar-coco3` palette on coco3. So
`check --video` tests those palettes, the pixel order in a byte and the pixel sizes
against XRoar's renderer. This example is the evidence for both palettes.

coco2b has the MC6847T1. Its graphics modes and the colour of each code and colour
set are the same as the MC6847's (MC6847T1 datasheet, PDF 15 Table 1 and PDF 25
Figure 26(c)); the T1 differs only in text and semigraphics (PDF 15-16).

On the CoCo 3 the same bytes and mode bits give the same picture, but each colour code
selects a palette register (Tepolt, Assembly Language Programming for the CoCo3, PDF 46).
The program keeps the values that BASIC loads into them (Tepolt PDF 57, step 44). The RGB
values of both palettes are measured in XRoar, not sourced.
"""

import numpy as np
from graphics import MODES, XROAR, XROAR_COCO3, render, unpack

SCREEN_BYTES = 6144  # CG6 and RG6: 6K bytes (MC6847 PDF 20)
BYTES_PER_ROW = 32
BAR_ROWS = 160
# Rows 0-159: four bars of 8 bytes each. Every pixel in a byte has the same bits,
# so each CG6 bar is one colour code: 0, 1, 2, 3 from the left.
BAR_BYTES = (0x00, 0x55, 0xAA, 0xFF)
# Rows 160-191: 00 01 10 11 in every byte. The leftmost pixel is in the high bits
# (MC6847 PDF 19 Table 3), so CG6 shows codes 0, 1, 2, 3 from the left.
ORDER_BYTE = 0x1B
# Mode and CSS of each variant. The colour of each code for each CSS is
# MC6847 PDF 21 Figure 22(c).
VARIANTS = {"": ("CG6", 0), "css1": ("CG6", 1), "rg6": ("RG6", 0), "rg6-css1": ("RG6", 1)}
# scripts/coco.py's capture: two samples per VDG half-clock, one row per scan line.
# Measured in XRoar: the CoCo 3 capture has the same size and position.
SAMPLES_PER_HALF_CLOCK = 2
PALETTES = {"coco1": XROAR, "coco2": XROAR, "coco2b": XROAR, "coco3": XROAR_COCO3}


def expected_screen(frame: int, variant: str) -> bytes:
    bar_row = b"".join(bytes([value]) * 8 for value in BAR_BYTES)
    order_row = bytes([ORDER_BYTE]) * BYTES_PER_ROW
    return bar_row * BAR_ROWS + order_row * (SCREEN_BYTES // BYTES_PER_ROW - BAR_ROWS)


def expected_frame(frame: int, variant: str, target: str) -> np.ndarray:
    """XRoar's picture of the screen bytes in the variant's mode and colour set."""
    name, css = VARIANTS[variant]
    mode = MODES[name]
    codes = unpack(expected_screen(frame, variant), mode.width, mode.height, mode.bits_per_pixel)
    return render(codes, mode, css, PALETTES[target], SAMPLES_PER_HALF_CLOCK)
