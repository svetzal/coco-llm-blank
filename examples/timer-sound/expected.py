"""Independent model of the timer-sound redraw: phase arithmetic and a moving marker.

Functions take the build variant ("", "heavy", "timer" or "timer-heavy"); the
expected memory is the same for each, while timing differs.
"""

import numpy as np

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
    return variant.startswith("timer")


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
    if variant == "heavy":
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
    """The tone continues through every redraw, except in the cooperative heavy build.

    Only the program's own sound is analysed: at most the last 150 ms, and never
    more than the least time the program can have run.
    """
    seconds = min(0.15, 0.95 * least_program_seconds(frame, variant))
    tail = sound.samples[-int(seconds * sound.rate) :].astype(float) / 32768
    signal = tail - tail.mean()
    rms = float(np.sqrt(np.mean(signal**2)))
    if rms < MIN_AC_RMS:
        raise ValueError(f"Frame {frame}: no tone in the mixer output (AC RMS {rms:.5f}).")
    if variant == "heavy":
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
