"""Independent model of the main-loop tone: DAC values, the mixer's pitch and the marker.

Written from the requirements in README.md and the cited sources, not from the
assembly. Functions take the build variant: "" (sawtooth) or "square".
"""

import itertools
import re

import numpy as np

SAMPLES_PER_BLOCK = 256
BLOCKS_PER_NOTE = 16
LOW_STEP, HIGH_STEP = 0x0800, 0x1000
# The DAC is $FF20 bits 7..2 (Tandy, Technical Reference Manual, PDF 14; CoCo 3
# Service Manual, PDF 10).
# Sawtooth: phase bits 15..10. Square: phase bit 15 only.
WAVE_MASK = {"": 0xFC, "square": 0x80}
# CoCo 1/2: the CPU clock is 14.31818 MHz / 16 (Tandy, Technical Reference
# Manual, PDF 26).
# CoCo 3: crystal X1 is 28.63636 MHz (CoCo 3 Service Manual, PDF 85) on the
# GIME (PDF 103), whose oscillator divider makes E and Q (PDF 96) at 0.89 or
# 1.78 MHz (PDF 31). BASIC leaves the slow rate (Tepolt, PDF 56 step 14 and
# PDF 62). Divide by 32 is our inference, shared by XRoar 1.13 (src/events.h,
# src/tcc1014/tcc1014.c), and gives the same 894,886.25 Hz on every target.
CPU_HZ = 14_318_180 / 16
# The sample loop takes 41 cycles (Leventhal, Appendix C, PDF 553-555):
# LDD 6, ADDD 7, STD 6, ANDA # 2, ORA 5, STA 5, DEC 7, BNE 3, all extended.
# The slot after each block adds a little; the tolerance covers it.
CYCLES_PER_SAMPLE = 41
BLOCK_SECONDS = SAMPLES_PER_BLOCK * CYCLES_PER_SAMPLE / CPU_HZ
PITCH_TOLERANCE_HZ = 15
MIN_AC_RMS = 0.01
# The slot budget: the frame work between two DAC writes. Longer work delays
# a sample even when every value is correct.
MAX_INSTRUCTIONS_BETWEEN_WRITES = 40
TRACED_BLOCKS = 64
MARKER_ROW = 96
BYTES_PER_ROW = 32


def step_for(block: int) -> int:
    """Each note lasts 16 blocks: blocks 1-16 low, 17-32 high, 33-48 low, and so on."""
    return HIGH_STEP if (block - 1) // BLOCKS_PER_NOTE % 2 else LOW_STEP


def expected_samples(variant: str, blocks: int = TRACED_BLOCKS) -> list[int]:
    """The DAC bits of each sample: the high byte of a 16-bit phase, masked to the waveform."""
    phase, result = 0, []
    for block in range(1, blocks + 1):
        for _ in range(SAMPLES_PER_BLOCK):
            phase = (phase + step_for(block)) % 65536
            result.append((phase >> 8) & WAVE_MASK[variant])
    return result


def expected_screen(frame: int, variant: str) -> bytes:
    """The context: one full byte on row 96 at column (block mod 32); the rest clear."""
    screen = bytearray(6144)
    screen[MARKER_ROW * BYTES_PER_ROW + frame % BYTES_PER_ROW] = 0xFF
    return bytes(screen)


def verify_trace(trace: str, symbols: dict[str, int], variant: str) -> dict[str, int]:
    """Every DAC write matches the model, in order, and the slot stays inside the budget."""
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
    if max(gaps) > MAX_INSTRUCTIONS_BETWEEN_WRITES:
        raise ValueError(
            f"Foreground work took {max(gaps)} instructions between DAC writes; "
            f"the budget is {MAX_INSTRUCTIONS_BETWEEN_WRITES}."
        )
    return {
        "dac_writes": len(writes),
        "minimum_instructions_between_writes": min(gaps),
        "maximum_instructions_between_writes": max(gaps),
    }


def expected_hz(step: int) -> float:
    """The waveform repeats every 65536 / step samples."""
    return CPU_HZ / CYCLES_PER_SAMPLE * step / 65536


def steady_blocks(frame: int) -> int:
    """How many blocks up to this one share its note."""
    count = 1
    while count < frame and step_for(frame - count) == step_for(frame):
        count += 1
    return count


def verify_sound(sound, frame: int, variant: str) -> dict[str, float]:
    """XRoar's mixer output ends with a tone at the pitch of this block's note.

    Only whole steady blocks are analysed, at most the last 150 ms. With less than
    100 ms of steady pitch, only the presence of a varying signal is checked.
    """
    step = step_for(frame)
    seconds = min(0.15, (steady_blocks(frame) - 1) * BLOCK_SECONDS)
    count = int(max(seconds, BLOCK_SECONDS / 2) * sound.rate)
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
    if abs(peak - expected_hz(step)) > PITCH_TOLERANCE_HZ:
        raise ValueError(
            f"Frame {frame}: mixer output peaks at {peak:.1f} Hz, "
            f"expected {expected_hz(step):.1f} Hz."
        )
    return result | {"expected_hz": round(expected_hz(step), 1), "peak_hz": round(peak, 1)}
