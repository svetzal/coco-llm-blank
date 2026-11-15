"""Independent model of the CoCo 3 page flip: both buffers and the picture.

Written from the scene description in README.md and the two-buffer rule, not
from the assembly. Frame N shows scene (N - 1) mod 5. It is drawn into one
buffer and then shown, so at the checkpoint for frame N the shown buffer holds
that scene complete, and the other buffer still holds the scene before it.
"""

import numpy as np

SCENES = 5
WIDTH, HEIGHT = 256, 192
BUFFER_BYTES = WIDTH * HEIGHT // 8
# Physical addresses. A 128 KiB snapshot holds the same RAM as physical
# pages $00-$0F (Tepolt PDF 29), so these offsets work at both RAM sizes.
# Frame 1 is drawn into B, frame 2 into A, and so on.
BUFFERS = {0: 0x04000, 1: 0x06000}
# The pinned XRoar's rendered levels for GIME palette values $00 and $3F with
# coco.py's renderer settings, read from a capture: emulator RGB, not a
# monitor and not from a source.
BLACK, WHITE = (20, 20, 20), (255, 255, 255)
# coco.py's capture: two samples per pixel at 256 pixels across.
SAMPLES_PER_PIXEL = 2


def scene(frame: int) -> int:
    return (frame - 1) % SCENES


def lit(frame: int) -> np.ndarray:
    """192 x 256 pixels: a one-pixel outline and an 8x8 square at row 80."""
    pixels = np.zeros((HEIGHT, WIDTH), dtype=bool)
    pixels[[0, -1], :] = pixels[:, [0, -1]] = True
    left = 32 + 16 * scene(frame)
    pixels[80:88, left : left + 8] = True
    return pixels


def buffer_bytes(frame: int) -> bytes:
    """Row-major, 32 bytes per row, bit 7 leftmost."""
    return np.packbits(lit(frame), axis=1).tobytes()


def verify_ram(ram: bytes, symbols: dict[str, int], frame: int) -> None:
    """The shown buffer holds this scene; the other still holds the scene before."""
    shown = BUFFERS[frame % 2]
    if ram[shown : shown + BUFFER_BYTES] != buffer_bytes(frame):
        raise ValueError(f"The buffer at ${shown:05X} does not hold scene {scene(frame)}.")
    if frame > 1:
        other = BUFFERS[(frame - 1) % 2]
        if ram[other : other + BUFFER_BYTES] != buffer_bytes(frame - 1):
            raise ValueError(f"The buffer at ${other:05X} does not hold scene {scene(frame - 1)}.")


def expected_frame(frame: int) -> np.ndarray:
    """The rendered 512x192 picture: the scene, complete."""
    wide = np.repeat(lit(frame), SAMPLES_PER_PIXEL, axis=1)
    return np.where(wide[:, :, None], np.array(WHITE), np.array(BLACK)).astype(np.uint8)
