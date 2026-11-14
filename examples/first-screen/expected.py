"""Independent model of the first screen: written from the pixel layout, not the assembly."""

import numpy as np

SCREEN_BYTES = 6144
READY_MARKER = 0x2FFF
# XRoar 1.12.1 palette for this mode's two colours (colour set 0: black and green)
# through coco.py's renderer settings. These are the emulator's RGB values, measured
# in experiments/display-validation, not a measurement of a real monitor.
BLACK, GREEN = (0, 31, 0), (46, 188, 36)
# The renderer draws each of the 256 pixels as two horizontal samples, 192 rows.
SAMPLES_PER_PIXEL = 2


def lit(x: int, y: int) -> bool:
    """The picture: a one-pixel perimeter and a centred 64-pixel square."""
    return x in (0, 255) or y in (0, 191) or (96 <= x < 160 and 64 <= y < 128)


def expected_screen(frame: int) -> bytes:
    """Eight pixels per byte, high bit leftmost."""
    result = bytearray(SCREEN_BYTES)
    for y in range(192):
        for x in range(256):
            if lit(x, y):
                result[y * 32 + x // 8] |= 0x80 >> (x % 8)
    return bytes(result)


def expected_frame(frame: int) -> np.ndarray:
    """The rendered picture, row by row, from the left: green where lit, black elsewhere."""
    rows = [
        [GREEN if lit(x // SAMPLES_PER_PIXEL, y) else BLACK for x in range(256 * SAMPLES_PER_PIXEL)]
        for y in range(192)
    ]
    return np.array(rows, dtype=np.uint8)


def verify_ram(ram: bytes, symbols: dict[str, int], frame: int) -> None:
    if len(ram) != 32768 or ram[READY_MARKER] != 0xA5:
        raise ValueError("The emulator did not reach the initialized program state.")
