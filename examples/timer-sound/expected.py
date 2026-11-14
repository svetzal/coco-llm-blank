"""Independent model of the timer-sound redraw: phase arithmetic and a moving marker.

Functions take the build variant ("", "heavy", "timer" or "timer-heavy"); the
expected memory is the same for each, while timing differs.
"""

# Executive pages $38-$3F occupy the upper 64 KiB of this 128 KiB machine.
RAM_BASE = 0x10000


def expected_screen(frame: int, variant: str) -> bytes:
    """One full byte on row 96 at column frame mod 32; everything else clear."""
    screen = bytearray(6144)
    screen[96 * 32 + frame % 32] = 0xFF
    return bytes(screen)


def verify_frame(data: bytes, symbols: dict[str, int]) -> int:
    if len(data) != 131072:
        raise ValueError("Expected a complete 128 KiB RAM snapshot.")
    ram = data[RAM_BASE:]

    def word(name: str) -> int:
        return int.from_bytes(ram[symbols[name] : symbols[name] + 2], "big")

    frames, samples = word("frames"), word("samples")
    if not frames or samples < 256 or word("phase") != (samples * 0x0800) % 65536:
        raise ValueError("Frame/audio state is inconsistent.")
    if ram[0x3FF] != 0xA5 or ram[0x1C00] != 0xA5:
        raise ValueError("Framebuffer guards were damaged.")
    if ram[0x400:0x1C00] != expected_screen(frames, "") or ram[symbols["position"]] != frames % 32:
        raise ValueError("Completed redraw differs from the marker specification.")
    return frames


def verify_ram(data: bytes, symbols: dict[str, int], frame: int, variant: str) -> None:
    if verify_frame(data, symbols) != frame:
        raise ValueError(f"Expected completed redraw {frame}.")
