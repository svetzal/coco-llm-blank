"""The timer-sound model checks a completed redraw against phase and marker rules."""

from pathlib import Path

import numpy as np
import pytest
from coco import load_expected
from recording import Sound

model = load_expected(Path(__file__).parent)
SYMBOLS = {"frames": 0x3F00, "samples": 0x3F02, "phase": 0x3F04, "position": 0x3F06}
BASE = model.RAM_BASE


def recording(hz: float, seconds: float = 0.5, pause_at_end: float = 0.0) -> Sound:
    """A synthetic mixer recording: boot silence, a stepped sawtooth, then any final pause."""
    rate = 44100
    time = np.arange(int(seconds * rate)) / rate
    tone = np.floor((time * hz) % 1.0 * 64) * 300 - 9600
    hold = np.full(int(pause_at_end * rate), tone[-1])
    samples = np.concatenate([np.zeros(rate // 2), tone, hold]).astype(np.int16)
    return Sound(path=Path("x.wav"), rate=rate, samples=samples)


def snapshot(frames: int, samples: int) -> bytearray:
    data = bytearray(131072)
    ram = memoryview(data)[BASE:]
    ram[0x3FF] = ram[0x1C00] = 0xA5
    ram[0x400:0x1C00] = model.expected_screen(frames, "")
    ram[0x3F00:0x3F02] = frames.to_bytes(2, "big")
    ram[0x3F02:0x3F04] = samples.to_bytes(2, "big")
    ram[0x3F04:0x3F06] = (samples * 0x0800 % 65536).to_bytes(2, "big")
    ram[0x3F06] = frames % 32
    return data


class DescribeTimerSound:
    def should_place_the_marker_by_redraw_count(self) -> None:
        screen = model.expected_screen(33, "timer")

        assert screen[96 * 32 + 1] == 0xFF
        assert sum(screen) == 0xFF

    def should_accept_a_consistent_redraw(self) -> None:
        model.verify_ram(snapshot(2, 517), SYMBOLS, 2, "timer-heavy")

    def should_reject_a_different_redraw_count(self) -> None:
        with pytest.raises(ValueError, match="redraw 3"):
            model.verify_ram(snapshot(2, 517), SYMBOLS, 3, "")

    @pytest.mark.parametrize("address", [0x3FF, 0x1C00, 0x1000, 0x3F03, 0x3F06])
    def should_reject_any_damaged_byte(self, address: int) -> None:
        broken = snapshot(2, 517)
        broken[BASE + address] ^= 1

        with pytest.raises(ValueError):
            model.verify_frame(broken, SYMBOLS)

    def should_reject_incomplete_memory(self) -> None:
        with pytest.raises(ValueError, match="128 KiB"):
            model.verify_frame(bytes(32768), SYMBOLS)

    def should_reject_a_frame_before_any_sample_block(self) -> None:
        with pytest.raises(ValueError, match="inconsistent"):
            model.verify_frame(snapshot(1, 255), SYMBOLS)


class DescribeTimerSoundOutput:
    def should_derive_the_timings_from_cycle_counts_and_the_timer(self) -> None:
        assert model.COOPERATIVE_CYCLES_PER_SAMPLE == 70
        assert model.CLEAR_CYCLES == 79_872
        assert model.expected_hz("timer") == pytest.approx(218.5, abs=0.1)
        assert model.expected_hz("") == pytest.approx(399.5, abs=0.1)

    @pytest.mark.parametrize("variant", ["", "timer", "timer-heavy"])
    def should_accept_a_continuous_tone_at_the_scheduled_pitch(self, variant: str) -> None:
        result = model.verify_sound(recording(model.expected_hz(variant)), 3, variant)

        assert abs(result["peak_hz"] - model.expected_hz(variant)) < 15
        assert result["longest_pause_ms"] < 1

    def should_reject_a_tone_at_another_pitch(self) -> None:
        with pytest.raises(ValueError, match="peaks at .* expected 218.5 Hz"):
            model.verify_sound(recording(400), 3, "timer-heavy")

    def should_reject_a_timer_tone_that_pauses(self) -> None:
        with pytest.raises(ValueError, match=r"paused for 20\.\d ms"):
            model.verify_sound(recording(218.5, pause_at_end=0.02), 3, "timer-heavy")

    def should_only_require_a_continuous_signal_before_the_window_is_long_enough(self) -> None:
        result = model.verify_sound(recording(300), 1, "timer")

        assert result["peak_hz"] is None and result["ac_rms"] > 0.01

    def should_accept_cooperative_sound_that_stops_for_the_whole_clear(self) -> None:
        result = model.verify_sound(recording(399.5, pause_at_end=0.09), 2, "heavy")

        assert result["final_pause_ms"] == pytest.approx(90, abs=0.1)

    def should_reject_a_cooperative_heavy_tone_without_the_clear_pause(self) -> None:
        with pytest.raises(ValueError, match="paused for only"):
            model.verify_sound(recording(399.5, pause_at_end=0.01), 2, "heavy")

    def should_reject_silence(self) -> None:
        silent = Sound(path=Path("x.wav"), rate=44100, samples=np.zeros(44100, dtype=np.int16))

        with pytest.raises(ValueError, match="no tone"):
            model.verify_sound(silent, 3, "timer")
