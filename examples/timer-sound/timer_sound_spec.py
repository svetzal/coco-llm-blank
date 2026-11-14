"""The timer-sound model checks a completed redraw against phase and marker rules."""

from pathlib import Path

import pytest
from coco import load_expected

model = load_expected(Path(__file__).parent)
SYMBOLS = {"frames": 0x3F00, "samples": 0x3F02, "phase": 0x3F04, "position": 0x3F06}
BASE = model.RAM_BASE


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
