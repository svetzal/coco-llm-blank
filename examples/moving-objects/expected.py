"""Independent model of the moving-objects scene, written without reading the assembly."""


def position(frame: int) -> tuple[int, int]:
    """Closed-form reflected motion, independent of the assembly's direction state."""
    tick = frame - 1
    return 30 - abs(tick % 60 - 30), 184 - abs(tick % 368 - 184)


def expected_screen(frame: int) -> bytes:
    """Pixel-level scene specification; B is above A except every other 32 frames."""
    xbyte, top = position(frame)
    lefts = {"a": xbyte * 8, "b": (30 - xbyte) * 8}
    order = ("b", "a") if frame & 32 else ("a", "b")
    result = bytearray(6144)
    for y in range(192):
        for x in range(256):
            pixel = ((x // 8 + y // 8) % 2) ^ bool(frame & 64)
            for name in order:
                if lefts[name] <= x < lefts[name] + 16 and top <= y < top + 8:
                    pixel = name == "a"
            if pixel:
                result[y * 32 + x // 8] |= 0x80 >> (x % 8)
    return bytes(result)


def verify_ram(data: bytes, symbols: dict[str, int], frame: int) -> None:
    """Guards, frame counter, trajectory and the complete framebuffer."""
    if len(data) != 32768 or (data[0x03FF], data[0x1C00]) != (0xA5, 0xA5):
        raise ValueError("Missing initialized RAM or damaged framebuffer guards.")
    count = int.from_bytes(data[symbols["frames"] : symbols["frames"] + 2], "big")
    actual_position = (data[symbols["xpos"]], data[symbols["ypos"]])
    if count != frame or actual_position != position(frame):
        raise ValueError("Movement state differs from the independent trajectory.")
    if data[0x400:0x1C00] != expected_screen(frame):
        raise ValueError("Framebuffer differs from the independent scene specification.")
