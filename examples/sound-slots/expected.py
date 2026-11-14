"""Independent model of the sound-slots loop: phase arithmetic and a moving marker.

Functions take the build variant: "" for live input, "scripted" for the fixture.
"""

import itertools
import re

import numpy as np

SAMPLES_PER_FRAME = 256
LOW_PITCH, HIGH_PITCH = 0x0800, 0x1000
# Sound timing, from the 6809 cycle counts of the eleven instructions in the sample
# loop (tick..bne tick, 57 cycles) at the stock 894,886.25 Hz clock. The foreground
# work after every 256 samples adds a little; the tolerance covers it.
CPU_HZ = 894_886.25
CYCLES_PER_SAMPLE = 57
FRAME_SECONDS = SAMPLES_PER_FRAME * CYCLES_PER_SAMPLE / CPU_HZ
PITCH_TOLERANCE_HZ = 15
MIN_AC_RMS = 0.01


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


def pitch_for(frame: int, variant: str) -> int:
    """The phase step used for a frame's samples: set by the previous frame's input."""
    if frame == 1:
        return LOW_PITCH
    return LOW_PITCH if expected_button(frame - 1, variant) else HIGH_PITCH


def expected_hz(pitch: int) -> float:
    """A sawtooth repeats every 65536 / pitch samples."""
    return CPU_HZ / CYCLES_PER_SAMPLE / (65536 / pitch)


def steady_frames(frame: int, variant: str) -> int:
    """How many frames up to this one share its pitch."""
    count = 1
    while count < frame and pitch_for(frame - count, variant) == pitch_for(frame, variant):
        count += 1
    return count


def verify_sound(sound, frame: int, variant: str) -> dict[str, float]:
    """XRoar's mixer output ends with a tone at the pitch this frame's input selected.

    Only whole steady frames are analysed, at most the last 150 ms. With less than
    100 ms of steady pitch, only the presence of a varying signal is checked.
    """
    pitch = pitch_for(frame, variant)
    seconds = min(0.15, (steady_frames(frame, variant) - 1) * FRAME_SECONDS)
    count = int(max(seconds, FRAME_SECONDS / 2) * sound.rate)
    tail = sound.samples[-count:].astype(float) / 32768
    signal = tail - tail.mean()
    rms = float(np.sqrt(np.mean(signal**2)))
    if rms < MIN_AC_RMS:
        raise ValueError(f"Frame {frame}: no tone in the mixer output (AC RMS {rms:.5f}).")
    result = {"frame": frame, "ac_rms": round(rms, 4), "expected_hz": None, "peak_hz": None}
    if seconds < 0.1:
        return result
    spectrum = np.abs(np.fft.rfft(signal * np.hanning(len(signal))))
    peak = (int(np.argmax(spectrum[1:])) + 1) * sound.rate / len(signal)
    if abs(peak - expected_hz(pitch)) > PITCH_TOLERANCE_HZ:
        raise ValueError(
            f"Frame {frame}: mixer output peaks at {peak:.1f} Hz, "
            f"expected {expected_hz(pitch):.1f} Hz."
        )
    return result | {"expected_hz": round(expected_hz(pitch), 1), "peak_hz": round(peak, 1)}
