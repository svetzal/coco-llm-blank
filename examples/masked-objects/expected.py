"""Independent pixel model of the masked-objects scenes, written in pixel coordinates."""

# Scene inputs: A origin, B origin, inverted background, draw order (last wins).
SCENES = (
    (0, 0, 240, 182, False, "ab"),
    (240, 0, 0, 182, False, "ab"),
    (112, 88, 120, 88, False, "ab"),
    (112, 88, 120, 88, False, "ba"),
    (112, 88, 112, 88, False, "ab"),
    (112, 88, 112, 88, False, "ba"),
    (16, 20, 216, 160, False, "ab"),
    (16, 20, 216, 160, False, ""),
    (112, 88, 120, 88, True, "ab"),
    (112, 88, 120, 88, True, "ba"),
    (112, 88, 120, 88, True, ""),
    (0, 182, 240, 0, True, "ab"),
)


def ring_pixel(x: int, y: int, name: str) -> int | None:
    """Geometric oracle: None is transparent, zero is opaque black."""
    if not (0 <= x < 16 and 1 <= y <= 8):
        return None
    if y == 1:
        return int(name == "a")
    if y == 8:
        return int(name == "b")
    if x in (0, 15):
        return int((x == 0) == (name == "a"))
    return None


def expected_screen(frame: int) -> bytes:
    """The screen after the Nth completed frame, which shows scene N - 1."""
    ax, ay, bx, by, invert, order = SCENES[frame - 1]
    origins = {"a": (ax, ay), "b": (bx, by)}
    result = bytearray(6144)
    for y in range(192):
        for x in range(256):
            pixel = ((x // 8 + y // 8) % 2) ^ invert
            for name in order:
                left, top = origins[name]
                ink = ring_pixel(x - left, y - top, name)
                if ink is not None:
                    pixel = ink
            if pixel:
                result[y * 32 + x // 8] |= 0x80 >> (x % 8)
    return bytes(result)


def verify_ram(data: bytes, symbols: dict[str, int], frame: int) -> None:
    """Snapshot size, guards, scene number and the complete framebuffer."""
    if len(data) != 32768:
        raise ValueError("Expected a 32 KiB RAM snapshot.")
    if (data[0x3FF], data[0x1C00]) != (0xA5, 0xA5):
        raise ValueError("Framebuffer guards damaged.")
    if data[symbols["scene"]] != frame - 1:
        raise ValueError("Wrong scene checkpoint.")
    if data[0x400:0x1C00] != expected_screen(frame):
        raise ValueError("Framebuffer differs from independent pixel oracle.")
