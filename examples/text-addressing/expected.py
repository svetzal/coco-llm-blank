"""Independent model of the CoCo 3 text-screen test card at each width.

Written from the test-card rule and the sourced buffer layout, not from the
assembly.
"""

import numpy as np

ROWS = 24
# Variant: columns. Tepolt, Assembly Language Programming for the CoCo3,
# PDF 36 Table 4-8; Tandy CoCo 3 Service Manual PDF 18 lists 32, 40 and 80.
COLUMNS = {"": 40, "c32": 32, "c64": 64, "c80": 80}
# Each cell is two bytes: the character code, then the attribute (Tepolt PDF
# 34). Space is code 32 (Tepolt PDF 34: codes 32-127 are ASCII). Attribute
# bits 5..3 select foreground palette 8-15 and bits 2..0 background palette
# 0-7 (Tepolt PDF 34-35). The program sets palette 0 to $00 and 1 to $3F.
SPACE = 0x20
BLACK_CELL, WHITE_CELL = 0x00, 0x01
# Measured, not sourced: the pinned XRoar's rendered levels for GIME palette
# values $00 and $3F with coco.py's renderer settings (read from a capture, measured in XRoar).
BLACK, WHITE = (20, 20, 20), (255, 255, 255)
LINES_PER_ROW = 8  # $FF98 LPR = 011 (Tandy PDF 12)
# Measured, not sourced: coco.py's capture is 512 samples wide. A text line
# is 512 samples at 32 and 64 columns and 640 samples at 40 and 80 columns.
# A 640-sample line is captured from sample 62, so its edges are not seen.
LINE_SAMPLES = {32: 512, 64: 512, 40: 640, 80: 640}
CAPTURE_START = {512: 0, 640: 62}
CAPTURE_SAMPLES = 512


def white(column: int, row: int, columns: int) -> bool:
    """The border cells and the cells where column = row."""
    return row in (0, ROWS - 1) or column in (0, columns - 1) or column == row


def cells(variant: str) -> np.ndarray:
    columns = COLUMNS[variant]
    return np.array(
        [[white(column, row, columns) for column in range(columns)] for row in range(ROWS)]
    )


def expected_screen(frame: int, variant: str) -> bytes:
    """Rows of (character, attribute) pairs from the upper left (Tepolt PDF 31)."""
    return bytes(
        byte for lit in cells(variant).flat for byte in (SPACE, WHITE_CELL if lit else BLACK_CELL)
    )


def expected_frame(frame: int, variant: str) -> np.ndarray:
    columns = COLUMNS[variant]
    line = LINE_SAMPLES[columns]
    start = CAPTURE_START[line]
    per_cell = line // columns
    lit = np.repeat(np.repeat(cells(variant), LINES_PER_ROW, axis=0), per_cell, axis=1)
    lit = lit[:, start : start + CAPTURE_SAMPLES]
    return np.where(lit[:, :, None], np.array(WHITE), np.array(BLACK)).astype(np.uint8)
