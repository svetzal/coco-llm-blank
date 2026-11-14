"""The moving-objects model specifies overlap order, bounds and the scenery change."""

from pathlib import Path

import pytest
from coco import load_expected

model = load_expected(Path(__file__).parent)
SYMBOLS = {"frames": 0x3F00, "xpos": 0x3F02, "ypos": 0x3F03}


def snapshot(frame: int) -> bytearray:
    ram = bytearray(32768)
    ram[0x03FF] = ram[0x1C00] = 0xA5
    ram[0x400:0x1C00] = model.expected_screen(frame)
    ram[0x3F00:0x3F02] = frame.to_bytes(2, "big")
    ram[0x3F02], ram[0x3F03] = model.position(frame)
    return ram


class DescribeMovingObjects:
    def should_specify_both_overlap_orders_and_background_change(self) -> None:
        black_overlap = model.expected_screen(16)
        white_overlap = model.expected_screen(46)

        # Frame 16: both occupy x=120..135, B (black) in front at y=15.
        assert black_overlap[15 * 32 + 15 : 15 * 32 + 17] == b"\0\0"
        # Frame 46: same x position, A (white) in front at y=45.
        assert white_overlap[45 * 32 + 15 : 45 * 32 + 17] == b"\xff\xff"
        # Scenery not covered by either object flips at frame 64.
        assert model.expected_screen(63)[0] == 0
        assert model.expected_screen(64)[0] == 255

    def should_bound_every_motion_tick(self) -> None:
        assert {model.position(frame)[0] for frame in range(1, 61)} == set(range(31))
        assert {model.position(frame)[1] for frame in range(1, 369)} == set(range(185))

    def should_accept_the_specified_memory(self) -> None:
        model.verify_ram(snapshot(16), SYMBOLS, 16)

    @pytest.mark.parametrize("address", [0x03FF, 0x1C00, 0x0400, 0x1BFF, 0x3F01, 0x3F02, 0x3F03])
    def should_reject_any_damaged_byte(self, address: int) -> None:
        damaged = snapshot(16)
        damaged[address] ^= 1

        with pytest.raises(ValueError):
            model.verify_ram(damaged, SYMBOLS, 16)

    @pytest.mark.parametrize("data", [b"", bytes(32768)])
    def should_reject_startup_or_missing_ram(self, data: bytes) -> None:
        with pytest.raises(ValueError, match="RAM"):
            model.verify_ram(data, SYMBOLS, 1)
