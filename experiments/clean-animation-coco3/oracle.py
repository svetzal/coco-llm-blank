"""Independent pixel-coordinate scene expectations, never assembly-generated assets."""

import numpy as np


def scene(number: int) -> bytes:
    """Black canvas, white outline and an eight-pixel square moving right."""
    if number not in range(5):
        raise ValueError("scene outside bounded sequence")
    pixels = np.zeros((192, 256), dtype=np.uint8)
    pixels[0, :] = pixels[-1, :] = 1
    pixels[:, 0] = pixels[:, -1] = 1
    pixels[80:88, 32 + number * 16 : 40 + number * 16] = 1
    return np.packbits(pixels, axis=1).tobytes()


def rgb(number: int) -> bytes:
    """Pinned RGB transfer: brightness/contrast 52, source levels 0 and .920.

    XRoar's NTSC law and integer quantization produce channels 2 and 253.
    These are software-renderer endpoints, not monitor measurements.
    """
    pixels = np.unpackbits(np.frombuffer(scene(number), np.uint8)).reshape(192, 256)
    channels = np.repeat(np.repeat(pixels, 2, axis=1)[:, :, None], 3, axis=2)
    return (2 + channels * 251).astype(np.uint8).tobytes()
