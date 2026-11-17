"""Independent model of the GIME graphics test card in each mode.

Written from the mode tables and the test-card rule, not from the assembly.

Sources: Tepolt, Assembly Language Programming for the CoCo3, PDF 38-39 (byte formats:
the leftmost pixel is in the high bits, a pixel value selects a palette register,
HRES0 set gives the full screen width) and PDF 41-42 Table 4-10 (HRES, CRES and
pixels of each mode); Tandy Color Computer 3 Service Manual PDF 12 (192, 200 or 225
lines per field) and PDF 18.
"""

import numpy as np

# Variant: (pixels across, bits per pixel, HRES). Tepolt PDF 41-42, Service Manual PDF 18.
MODES = {
    "": (320, 4, 0b111),
    "g256x16": (256, 4, 0b110),
    "g160x16": (160, 4, 0b101),
    "g128x16": (128, 4, 0b100),
    "g640x4": (640, 2, 0b111),
    "g512x4": (512, 2, 0b110),
    "g320x4": (320, 2, 0b101),
    "g256x4": (256, 2, 0b100),
    "g160x4": (160, 2, 0b011),
    "g128x4": (128, 2, 0b010),
    "g640x2": (640, 1, 0b101),
    "g512x2": (512, 1, 0b100),
    "g320x2": (320, 1, 0b011),
    "g256x2": (256, 1, 0b010),
    "g160x2": (160, 1, 0b001),
    "g128x2": (128, 1, 0b000),
    "g80x16": (80, 4, 0b011),
    "g64x16": (64, 4, 0b010),
    "g80x4": (80, 2, 0b001),
    "g64x4": (64, 2, 0b000),
    "l200": (320, 4, 0b111),
    "l225": (320, 4, 0b111),
}
ROWS = {"l200": 200, "l225": 225}

# The colour codes that main.asm puts in palette registers 0-15.
PALETTE = [
    0x00,
    0x30,
    0x12,
    0x24,
    0x0B,
    0x16,
    0x1C,
    0x34,
    0x07,
    0x21,
    0x2D,
    0x05,
    0x19,
    0x3C,
    0x0E,
    0x26,
]
# Measured, not sourced: XRoar 1.13.1's rendered colour of each code through coco.py's
# capture (-tv-input svideo -ccr none), a composite picture, not an RGB monitor. The
# rendered check is the evidence; its negative control is a wrong palette code.
RENDERED = {
    0x00: (20, 20, 20),
    0x30: (255, 255, 255),
    0x12: (71, 145, 5),
    0x24: (255, 200, 46),
    0x0B: (34, 28, 222),
    0x16: (255, 79, 75),
    0x1C: (34, 127, 241),
    0x34: (255, 255, 136),
    0x07: (155, 18, 60),
    0x21: (99, 255, 48),
    0x2D: (67, 248, 255),
    0x05: (117, 29, 2),
    0x19: (215, 71, 255),
    0x3C: (179, 255, 255),
    0x0E: (0, 67, 21),
    0x26: (255, 157, 151),
}
# Measured, not sourced, as in examples/text-addressing: the capture is 512 samples
# wide and 192 lines high. A short-width line is 512 samples. A full-width line is
# 640 samples, captured from sample 62.
CAPTURE_SAMPLES = 512
CAPTURE_LINES = 192
FULL_WIDTH_START = 62
# Measured, not sourced: the screen row on the first captured line, for each number
# of rows. The capture shows 192 lines, so it does not show all of a taller screen.
# XRoar's source agrees: tcc1014.c gives 36, 34 and 19 lines of top border at 60 Hz.
FIRST_ROW = {192: 0, 200: 2, 225: 17}
# Measured, not sourced: on the 1987 GIME, a short-width line with HRES bit 2 set
# starts 2 samples later, and the border colour fills the first 2 samples. XRoar's
# tcc1014.c gives that left border as 106 samples on the 1987 GIME and 104 on the
# 1986 GIME. This is XRoar's model, not a measurement of a real GIME.
LATE_SHORT_LINE = {"coco3-1987": 2}
BORDER = RENDERED[0x00]  # main.asm sets $FF9A, the border colour code, to 0


def shape(variant: str) -> tuple[int, int, int]:
    width, bits, _ = MODES[variant]
    return width, bits, ROWS.get(variant, 192)


def pixel(x: int, y: int, variant: str) -> int:
    """Palette register: the last colour on the edge, else one bar for each colour.

    Every 16 rows, each bar takes the next colour.
    """
    width, bits, rows = shape(variant)
    colours = 1 << bits
    if x in (0, width - 1) or y in (0, rows - 1):
        return colours - 1
    return (x // (width // colours) + y // 16) % colours


def expected_screen(frame: int, variant: str) -> bytes:
    """Rows of bytes from the upper left; the leftmost pixel in the high bits."""
    width, bits, rows = shape(variant)
    per_byte = 8 // bits
    result = bytearray(width * rows // per_byte)
    for y in range(rows):
        for x in range(width):
            shift = 8 - bits * (x % per_byte + 1)
            result[(y * width + x) // per_byte] |= pixel(x, y, variant) << shift
    return bytes(result)


def full_width(width: int, bits: int) -> bool:
    """HRES0 set: 20, 40, 80 or 160 bytes for each row (Tepolt PDF 39, 41-42)."""
    return width * bits // 8 in (20, 40, 80, 160)


def expected_frame(frame: int, variant: str, target: str) -> np.ndarray:
    """The captured picture: each pixel spans its share of the line's samples."""
    width, bits, rows = shape(variant)
    first = FIRST_ROW[rows]
    line = 640 if full_width(width, bits) else 512
    start = FULL_WIDTH_START if line == 640 else 0
    if line == 512 and MODES[variant][2] & 0b100:
        start = -LATE_SHORT_LINE.get(target, 0)
    colours = np.array([RENDERED[code] for code in PALETTE] + [BORDER], dtype=np.uint8)
    picture = []
    for y in range(CAPTURE_LINES):
        samples = [
            pixel((start + s) * width // line, first + y, variant)
            if start + s >= 0
            else len(PALETTE)
            for s in range(CAPTURE_SAMPLES)
        ]
        picture.append(colours[samples])
    return np.array(picture, dtype=np.uint8)
