"""Independent model of the sound-slots loop: phase arithmetic and a moving marker.

Functions take the build variant: "" for live input, "scripted" for the fixture.
"""

import itertools
import re

SAMPLES_PER_FRAME = 256
LOW_PITCH, HIGH_PITCH = 0x0800, 0x1000


def expected_button(frame: int, variant: str) -> int:
    """The fixture holds released/pressed for alternating blocks of sixteen frames."""
    return 1 - ((frame - 1) // 16 % 2) if variant == "scripted" else 1


def expected_samples(variant: str, frames: int = 64) -> list[int]:
    """Upper six bits of a 16-bit phase; the pitch changes after each frame's input read."""
    phase, pitch, result = 0, LOW_PITCH, []
    for frame in range(1, frames + 1):
        for _ in range(SAMPLES_PER_FRAME):
            phase = (phase + pitch) % 65536
            result.append((phase >> 8) & 0xFC)
        pitch = LOW_PITCH if expected_button(frame, variant) else HIGH_PITCH
    return result


def expected_screen(frame: int, variant: str) -> bytes:
    """One full byte on row 96 at column frame mod 32; everything else clear."""
    screen = bytearray(6144)
    screen[96 * 32 + frame % 32] = 0xFF
    return bytes(screen)


def verify_ram(data: bytes, symbols: dict[str, int], frame: int, variant: str) -> None:
    def word(name: str) -> int:
        return int.from_bytes(data[symbols[name] : symbols[name] + 2], "big")

    if len(data) != 32768 or data[0x03FF] != 0xA5 or data[0x1C00] != 0xA5:
        raise ValueError("Missing initialized RAM or damaged framebuffer guards.")
    button = expected_button(frame, variant)
    state = (word("frames"), word("samples"), word("pitch"), word("phase"))
    expected = (frame, frame * SAMPLES_PER_FRAME, LOW_PITCH if button else HIGH_PITCH, 0)
    if state != expected or data[symbols["button"]] != button:
        raise ValueError("Sound/input state differs from the frame specification.")
    if data[0x400:0x1C00] != expected_screen(frame, variant):
        raise ValueError("Moving marker or background differs from the screen specification.")
    if data[symbols["position"]] != frame % 32:
        raise ValueError("Moving marker or background differs from the screen specification.")


def verify_trace(trace: str, symbols: dict[str, int], variant: str) -> dict[str, int]:
    """Every DAC write in the instruction trace matches the phase model, in order."""
    instructions = re.findall(r"^([0-9a-f]{4})\|.*$", trace, re.MULTILINE)
    records = re.findall(r"^([0-9a-f]{4})\|.*?\ba=([0-9a-f]{2})\b.*$", trace, re.MULTILINE)
    writes = [
        (i, int(a, 16) & 0xFC)
        for i, (pc, a) in enumerate(records)
        if int(pc, 16) == symbols["sample"]
    ]
    if len(records) != len(instructions) or [a for _, a in writes] != expected_samples(variant):
        raise ValueError("DAC instruction trace differs from the independent phase model.")
    gaps = [right[0] - left[0] for left, right in itertools.pairwise(writes)]
    if max(gaps) <= min(gaps):
        raise ValueError("Trace did not exercise the extra input/graphics work.")
    return {
        "dac_writes": len(writes),
        "minimum_instructions_between_writes": min(gaps),
        "maximum_instructions_between_writes": max(gaps),
    }
