"""Independent model of the first screen: written from the pixel layout, not the assembly."""

SCREEN_BYTES = 6144
READY_MARKER = 0x2FFF


def expected_screen(frame: int) -> bytes:
    """Perimeter and a centred 64-pixel square; eight pixels per byte, high bit leftmost."""
    result = bytearray(SCREEN_BYTES)
    for y in range(192):
        for x in range(256):
            if x in (0, 255) or y in (0, 191) or (96 <= x < 160 and 64 <= y < 128):
                result[y * 32 + x // 8] |= 0x80 >> (x % 8)
    return bytes(result)


def verify_ram(ram: bytes, symbols: dict[str, int], frame: int) -> None:
    if len(ram) != 32768 or ram[READY_MARKER] != 0xA5:
        raise ValueError("The emulator did not reach the initialized program state.")
