"""The sound-slots model fixes every DAC value, the input fixture and the marker."""

from pathlib import Path

import numpy as np
import pytest
from coco import load_expected
from recording import Sound

model = load_expected(Path(__file__).parent)
SYMBOLS = {
    "frames": 0x3F00,
    "samples": 0x3F02,
    "pitch": 0x3F04,
    "phase": 0x3F06,
    "button": 0x3F08,
    "position": 0x3F09,
    "sample": 0x3050,
}


def snapshot(frame: int, variant: str) -> bytearray:
    ram = bytearray(32768)
    ram[0x03FF] = ram[0x1C00] = 0xA5
    ram[0x400:0x1C00] = model.expected_screen(frame, variant)
    button = model.expected_button(frame, variant)
    pitch = 0x0800 if button else 0x1000
    for address, value in ((0x3F00, frame), (0x3F02, frame * 256), (0x3F04, pitch)):
        ram[address : address + 2] = value.to_bytes(2, "big")
    ram[0x3F08], ram[0x3F09] = button, frame % 32
    return ram


def sawtooth(hz: float, seconds: float = 1.0, rate: int = 44100) -> Sound:
    """A synthetic mixer recording: boot silence, then a tone up to the checkpoint."""
    time = np.arange(int(seconds * rate)) / rate
    tone = ((time * hz) % 1.0 - 0.5) * 20000
    samples = np.concatenate([np.zeros(rate // 2), tone]).astype(np.int16)
    return Sound(path=Path("x.wav"), rate=rate, samples=samples)


def trace(variant: str, extra_every: int = 256) -> str:
    lines = []
    for index, value in enumerate(model.expected_samples(variant), 1):
        lines.append(f"3050| STA $ff20 a={value | 2:02x} b=00")
        lines.append("3053| ADDD #$0800 a=00 b=00")
        if index % extra_every == 0:
            lines.append("3060| LDA $ff00 a=7f b=00")
    return "\n".join(lines) + "\n"


class DescribeSoundSlots:
    def should_alternate_the_fixture_every_sixteen_frames(self) -> None:
        held = [model.expected_button(frame, "scripted") for frame in (1, 16, 17, 32, 33)]

        assert held == [1, 1, 0, 0, 1]
        assert {model.expected_button(frame, "") for frame in range(1, 65)} == {1}

    def should_double_the_phase_step_after_a_pressed_frame(self) -> None:
        samples = model.expected_samples("scripted")

        assert len(samples) == 64 * 256
        assert samples[:4] == [8, 16, 24, 32]
        assert samples[17 * 256 : 17 * 256 + 2] != samples[16 * 256 : 16 * 256 + 2]

    @pytest.mark.parametrize("variant", ["", "scripted"])
    def should_accept_the_specified_memory(self, variant: str) -> None:
        model.verify_ram(snapshot(17, variant), SYMBOLS, 17, variant)

    @pytest.mark.parametrize("address", [0x03FF, 0x1C00, 0x1000, 0x3F01, 0x3F08, 0x3F09])
    def should_reject_any_damaged_byte(self, address: int) -> None:
        broken = snapshot(64, "scripted")
        broken[address] ^= 1

        with pytest.raises(ValueError):
            model.verify_ram(broken, SYMBOLS, 64, "scripted")

    def should_reject_missing_ram(self) -> None:
        with pytest.raises(ValueError, match="RAM"):
            model.verify_ram(b"", SYMBOLS, 1, "")

    def should_measure_instruction_gaps_in_a_matching_trace(self) -> None:
        result = model.verify_trace(trace(""), SYMBOLS, "")

        assert result == {
            "dac_writes": 16384,
            "minimum_instructions_between_writes": 2,
            "maximum_instructions_between_writes": 3,
        }

    def should_reject_foreground_work_over_the_budget(self) -> None:
        lines = trace("").splitlines()
        lines.insert(3, "\n".join(["3070| LEAX -1,X a=00 b=00"] * 41))

        with pytest.raises(ValueError, match="took 43 instructions .* budget is 40"):
            model.verify_trace("\n".join(lines) + "\n", SYMBOLS, "")

    def should_accept_the_coco2_targets_64_kib_snapshot(self) -> None:
        model.verify_ram(snapshot(17, "") + bytes(32768), SYMBOLS, 17, "")

    @pytest.mark.parametrize("damage", ["truncated", "other variant", "even gaps", "no registers"])
    def should_reject_a_trace_that_differs(self, damage: str) -> None:
        text = {
            "truncated": trace("")[: len(trace("")) // 2],
            "other variant": trace("scripted"),
            "even gaps": trace("", extra_every=10**6),
            "no registers": trace("") + "3070| NOP\n",
        }[damage]

        with pytest.raises(ValueError):
            model.verify_trace(text, SYMBOLS, "")


class DescribeSoundOutput:
    def should_take_each_frames_pitch_from_the_previous_input(self) -> None:
        pitches = [model.pitch_for(frame, "scripted") for frame in (1, 17, 18, 33, 34)]

        assert pitches == [0x0800, 0x0800, 0x1000, 0x1000, 0x0800]
        assert model.steady_frames(32, "scripted") == 15
        assert model.steady_frames(64, "") == 64

    def should_derive_the_tone_from_cycle_counts(self) -> None:
        assert model.expected_hz(0x0800) == pytest.approx(490.6, abs=0.1)
        assert model.expected_hz(0x1000) == pytest.approx(2 * model.expected_hz(0x0800))

    @pytest.mark.parametrize("frame,variant,hz", [(64, "", 488), (32, "scripted", 975)])
    def should_accept_a_tone_at_the_selected_pitch(self, frame, variant, hz) -> None:
        result = model.verify_sound(sawtooth(hz), frame, variant)

        assert result["expected_hz"] == pytest.approx(
            model.expected_hz(model.pitch_for(frame, variant)), abs=0.1
        )
        assert abs(result["peak_hz"] - hz) < 7

    def should_reject_a_tone_at_the_other_pitch(self) -> None:
        with pytest.raises(ValueError, match="peaks at .* expected 490.6 Hz"):
            model.verify_sound(sawtooth(975), 64, "")

    def should_reject_silence(self) -> None:
        silent = Sound(path=Path("x.wav"), rate=44100, samples=np.zeros(44100, dtype=np.int16))

        with pytest.raises(ValueError, match="no tone"):
            model.verify_sound(silent, 64, "")

    def should_only_require_a_signal_when_the_pitch_is_new(self) -> None:
        result = model.verify_sound(sawtooth(975), 1, "")

        assert result["peak_hz"] is None and result["ac_rms"] > 0.01
