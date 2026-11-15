"""Independent model of the page-flip scene, written without reading the assembly.

The scene is the moving-objects scene. The program draws frame N into one of two
screens and then shows that screen, so the rendered picture after the flip must
be frame N complete: never a frame still being drawn.
"""

import numpy as np

SCREEN_BYTES = 6144
# Odd frames are drawn at $2400, even frames at $0400; each has a guard on each side.
SCREENS = (0x0400, 0x2400)
GUARDS = (0x03FF, 0x1C00, 0x23FF, 0x3C00)
# The pinned XRoar's two RG6 colours for colour set 0, as in examples/first-screen.
BLACK, GREEN = (0, 31, 0), (46, 188, 36)
SAMPLES_PER_PIXEL = 2


def position(frame: int) -> tuple[int, int]:
    """Closed-form reflected motion: byte column of A and pixel row of both."""
    tick = frame - 1
    return 30 - abs(tick % 60 - 30), 184 - abs(tick % 368 - 184)


def lit(frame: int) -> np.ndarray:
    """192 x 256 pixels: checker scenery, then A (set) and B (clear) in layer order."""
    y, x = np.mgrid[0:192, 0:256]
    pixels = ((x // 8 + y // 8) % 2).astype(bool) ^ bool(frame & 64)
    xbyte, top = position(frame)
    lefts = {"a": xbyte * 8, "b": (30 - xbyte) * 8}
    for name in ("b", "a") if frame & 32 else ("a", "b"):
        inside = (lefts[name] <= x) & (x < lefts[name] + 16) & (top <= y) & (y < top + 8)
        pixels[inside] = name == "a"
    return pixels


def expected_screen(frame: int) -> bytes:
    """Eight pixels per byte, high bit leftmost."""
    return np.packbits(lit(frame), axis=1).tobytes()


def expected_frame(frame: int) -> np.ndarray:
    """The rendered picture: two samples per pixel, green where set, black elsewhere."""
    wide = np.repeat(lit(frame), SAMPLES_PER_PIXEL, axis=1)
    return np.where(wide[:, :, None], np.array(GREEN), np.array(BLACK)).astype(np.uint8)


def verify_ram(ram: bytes, symbols: dict[str, int], frame: int) -> None:
    """Guards, frame counter, trajectory and the screen that was just drawn."""
    if len(ram) != 32768 or any(ram[guard] != 0xA5 for guard in GUARDS):
        raise ValueError("Missing initialized RAM or damaged screen guards.")
    count = int.from_bytes(ram[symbols["frames"] : symbols["frames"] + 2], "big")
    if count != frame or (ram[symbols["xpos"]], ram[symbols["ypos"]]) != position(frame):
        raise ValueError("Movement state differs from the independent trajectory.")
    drawn = int.from_bytes(ram[symbols["drawing"] : symbols["drawing"] + 2], "big")
    if drawn not in SCREENS:
        raise ValueError(f"The drawing pointer ${drawn:04X} is not a screen base.")
    if ram[drawn : drawn + SCREEN_BYTES] != expected_screen(frame):
        raise ValueError("The drawn screen differs from the independent scene specification.")
