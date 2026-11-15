"""Independent model of the timer-sound builds: the marker after each redraw and the tone.

Written from the requirements in README.md and the cited sources, not from the
assembly. Functions take the build variant: "" (timer), "heavy" (timer with a
costly redraw), "cooperative" or "cooperative-heavy". The expected memory is the
same for each; the sound differs.
"""

import numpy as np

# At reset, BASIC maps the executive pages $38-$3F (Tepolt, PDF 56). On this
# 128 KiB machine they occupy the upper 64 KiB of the RAM snapshot.
RAM_BASE = 0x10000
MARKER_ROW = 96
BYTES_PER_ROW = 32
STEP = 0x0800


def expected_screen(frame: int, variant: str) -> bytes:
    """The context: one full byte on row 96 at column (redraw mod 32); the rest clear."""
    screen = bytearray(6144)
    screen[MARKER_ROW * BYTES_PER_ROW + frame % BYTES_PER_ROW] = 0xFF
    return bytes(screen)


def verify_ram(data: bytes, symbols: dict[str, int], frame: int, variant: str) -> None:
    """The phase matches the sample count, and each redraw follows a new block of samples."""
    ram = data[RAM_BASE:]

    def word(name: str) -> int:
        return int.from_bytes(ram[symbols[name] : symbols[name] + 2], "big")

    samples = word("samples")
    if samples < frame * SAMPLES_PER_BLOCK or word("phase") != samples * STEP % 65536:
        raise ValueError(f"Redraw {frame}: the phase and the sample count disagree.")


# Sound timing. The emulated clocks come from XRoar's 14,318,180 Hz event clock:
# the slow 6809 cycle is 16 ticks, and the GIME timer counts reload + 2 (1986) or
# reload + 1 (1987) steps of 4 ticks each (Kowalski's GIME reference, $FF94-$FF95).
TICK_HZ = 14_318_180
CPU_HZ = TICK_HZ / 16
TIMER_RELOAD = 510
TIMER_HZ = TICK_HZ / ((TIMER_RELOAD + 2) * 4)  # the 1987 GIME is 0.4 Hz higher in pitch
# Cooperative sample cost, from 6809 cycle counts (Leventhal, Appendix C): JSR emit (8),
# the emit body (49) and the loop's LDA/CMPA/BEQ test (13).
COOPERATIVE_CYCLES_PER_SAMPLE = 8 + 49 + 13
# The heavy redraw: STA ,X+ (6), CMPX # (4) and BLO (3) for each of 6,144 bytes.
CLEAR_CYCLES = 6144 * (6 + 4 + 3)
SAMPLES_PER_BLOCK = 256
SAMPLES_PER_CYCLE = 65536 // 0x0800
PITCH_TOLERANCE_HZ = 15
MIN_AC_RMS = 0.01
# The longest pause the tone may have: about seven timer sample periods.
MAX_PAUSE_SECONDS = 0.001


def is_timer(variant: str) -> bool:
    return not variant.startswith("cooperative")


def sample_hz(variant: str) -> float:
    return TIMER_HZ if is_timer(variant) else CPU_HZ / COOPERATIVE_CYCLES_PER_SAMPLE


def expected_hz(variant: str) -> float:
    """The sawtooth repeats every 32 samples."""
    return sample_hz(variant) / SAMPLES_PER_CYCLE


def least_program_seconds(frame: int, variant: str) -> float:
    """A lower bound on the time from the first sample to completed redraw `frame`.

    Each redraw follows a new block of 256 samples. Only the cooperative heavy
    build stops sampling while it clears the screen, so only it adds that cost.
    """
    seconds = frame * SAMPLES_PER_BLOCK / sample_hz(variant)
    if variant == "cooperative-heavy":
        seconds += frame * CLEAR_CYCLES / CPU_HZ
    return seconds


def longest_pause(samples) -> int:
    """The longest run of identical mixer samples."""
    changes = np.flatnonzero(np.diff(samples) != 0)
    return int(np.diff(np.concatenate([[-1], changes, [len(samples) - 1]])).max())


def final_pause(samples) -> int:
    changes = np.flatnonzero(np.diff(samples) != 0)
    return len(samples) - 1 - int(changes[-1]) if len(changes) else len(samples)


def verify_sound(sound, frame: int, variant: str) -> dict[str, object]:
    """The tone continues through every redraw, except in the cooperative-heavy build.

    Only the program's own sound is analysed: at most the last 150 ms, and never
    more than the least time the program can have run.
    """
    seconds = min(0.15, 0.95 * least_program_seconds(frame, variant))
    tail = sound.samples[-int(seconds * sound.rate) :].astype(float) / 32768
    signal = tail - tail.mean()
    rms = float(np.sqrt(np.mean(signal**2)))
    if rms < MIN_AC_RMS:
        raise ValueError(f"Frame {frame}: no tone in the mixer output (AC RMS {rms:.5f}).")
    if variant == "cooperative-heavy":
        return verify_stopped_by_clear(tail, sound.rate, frame) | {"ac_rms": round(rms, 4)}
    pause = longest_pause(tail) / sound.rate
    if pause > MAX_PAUSE_SECONDS:
        raise ValueError(f"Frame {frame}: the tone paused for {pause * 1000:.1f} ms.")
    result = {"frame": frame, "ac_rms": round(rms, 4), "longest_pause_ms": round(pause * 1000, 2)}
    if seconds < 0.05:
        return result | {"expected_hz": None, "peak_hz": None}
    spectrum = np.abs(np.fft.rfft(signal * np.hanning(len(signal))))
    peak = (int(np.argmax(spectrum[1:])) + 1) * sound.rate / len(signal)
    if abs(peak - expected_hz(variant)) > PITCH_TOLERANCE_HZ:
        raise ValueError(
            f"Frame {frame}: mixer output peaks at {peak:.1f} Hz, "
            f"expected {expected_hz(variant):.1f} Hz."
        )
    return result | {"expected_hz": round(expected_hz(variant), 1), "peak_hz": round(peak, 1)}


def verify_stopped_by_clear(tail, rate: int, frame: int) -> dict[str, object]:
    """Cooperative sound stops while the foreground clears the screen."""
    pause = final_pause(tail) / rate
    if pause < 0.95 * CLEAR_CYCLES / CPU_HZ:
        raise ValueError(
            f"Frame {frame}: the tone paused for only {pause * 1000:.1f} ms during the clear, "
            f"expected at least {CLEAR_CYCLES / CPU_HZ * 1000:.1f} ms."
        )
    return {"frame": frame, "final_pause_ms": round(pause * 1000, 2)}
