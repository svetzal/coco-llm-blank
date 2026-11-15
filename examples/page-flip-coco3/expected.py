"""Independent model of the CoCo 3 page flip, written in pixel coordinates.

Scene N (N = 0-4, then 0 again) is drawn into one buffer and then shown, so the
rendered picture after the flip must be that scene complete.
"""

import numpy as np

SCENES = 5
SCREEN_BYTES = 6144
# CPU $4000-$7FFF maps to physical pages 2 and 3, which are snapshot offsets
# $4000-$7FFF at either RAM size. Scene 0 is drawn into A, scene 1 into B, ...
BUFFERS = (0x4100, 0x6100)
GUARDS = (0x40FF, 0x5900, 0x60FF, 0x7900, 0x7DFF, 0x7F00)
# The pinned XRoar's rendered levels for GIME palette values $00 and $3F with
# coco.py's renderer settings, read from this example's capture: emulator RGB,
# not a monitor and not derived from a source.
BLACK, WHITE = (20, 20, 20), (255, 255, 255)
SAMPLES_PER_PIXEL = 2


def scene(frame: int) -> int:
    return (frame - 1) % SCENES


def lit(frame: int) -> np.ndarray:
    """192 x 256 pixels: a one-pixel outline and an 8x8 square at y=80."""
    pixels = np.zeros((192, 256), dtype=bool)
    pixels[[0, -1], :] = pixels[:, [0, -1]] = True
    left = 32 + 16 * scene(frame)
    pixels[80:88, left : left + 8] = True
    return pixels


def expected_screen(frame: int) -> bytes:
    """Row-major, 32 bytes per row, bit 7 leftmost."""
    return np.packbits(lit(frame), axis=1).tobytes()


def expected_frame(frame: int) -> np.ndarray:
    wide = np.repeat(lit(frame), SAMPLES_PER_PIXEL, axis=1)
    return np.where(wide[:, :, None], np.array(WHITE), np.array(BLACK)).astype(np.uint8)


def verify_ram(ram: bytes, symbols: dict[str, int], frame: int) -> None:
    """Guards, scene number and the buffer that was just drawn and shown."""
    if len(ram) not in (128 * 1024, 512 * 1024) or any(ram[g] != 0xA5 for g in GUARDS):
        raise ValueError("Missing initialized RAM or damaged buffer guards.")
    # Executive pages $38-$3F hold the code and state in the top 64 KiB.
    state = ram[len(ram) - 0x10000 :]
    if state[symbols["scene"]] != scene(frame):
        raise ValueError(f"Expected scene {scene(frame)}, found {state[symbols['scene']]}.")
    drawn = int.from_bytes(state[symbols["back"] : symbols["back"] + 2], "big")
    if drawn != BUFFERS[(frame - 1) % 2]:
        raise ValueError(f"Scene {scene(frame)} was drawn at ${drawn:04X}.")
    if ram[drawn : drawn + SCREEN_BYTES] != expected_screen(frame):
        raise ValueError("The drawn buffer differs from the independent scene specification.")
