"""Masked pixels preserve scenery, clear opaque black, and respect draw order."""

from pathlib import Path

import pytest
from coco import load_expected

model = load_expected(Path(__file__).parent)
SYMBOLS = {"scene": 0x3F00}


def snapshot(frame: int) -> bytearray:
    ram = bytearray(32768)
    ram[0x03FF] = ram[0x1C00] = 0xA5
    ram[0x400:0x1C00] = model.expected_screen(frame)
    ram[0x3F00] = frame - 1
    return ram


class DescribeMaskedObjects:
    @pytest.mark.parametrize(
        "x,y,a,b",
        [
            (0, 1, 1, 0),
            (15, 8, 0, 1),
            (0, 4, 1, 0),
            (15, 4, 0, 1),
            (7, 4, None, None),
            (0, 0, None, None),
            (15, 9, None, None),
            (-1, 2, None, None),
            (16, 2, None, None),
        ],
    )
    def should_distinguish_transparent_holes_from_both_opaque_inks(self, x, y, a, b):
        assert model.ring_pixel(x, y, "a") == a
        assert model.ring_pixel(x, y, "b") == b

    def should_specify_byte_order_overlap_and_restored_background(self) -> None:
        first = model.expected_screen(1)
        plain = model.expected_screen(8)
        inverted = model.expected_screen(11)

        # A's green left / black right edges in row 4 over alternating 00/FF.
        assert first[4 * 32 : 4 * 32 + 2] == bytes((0x80, 0xFE))
        # Transparent entire first row and centre retain the underlying pattern.
        assert first[:2] == bytes((0, 255))
        assert first[5 * 32 : 5 * 32 + 2] == bytes((0x80, 0xFE))
        # Complete overlap: the last ring wins at its opaque top edge.
        assert model.expected_screen(5)[89 * 32 + 14 : 89 * 32 + 16] == bytes((0, 0))
        assert model.expected_screen(6)[89 * 32 + 14 : 89 * 32 + 16] == bytes((255, 255))
        assert model.expected_screen(3) != model.expected_screen(4)
        assert all(a ^ b == 255 for a, b in zip(plain, inverted, strict=True))
        assert plain[:32] == bytes((0, 255)) * 16
        assert plain[8 * 32 : 9 * 32] == bytes((255, 0)) * 16

    def should_accept_the_specified_memory(self) -> None:
        model.verify_ram(snapshot(3), SYMBOLS, 3)

    @pytest.mark.parametrize("address", [0x3FF, 0x1C00, 0x400, 0x1BFF, 0x3F00])
    def should_reject_any_damaged_byte(self, address: int) -> None:
        damaged = snapshot(3)
        damaged[address] ^= 1

        with pytest.raises(ValueError):
            model.verify_ram(damaged, SYMBOLS, 3)

    @pytest.mark.parametrize("data", [b"", bytes(32767), bytes(32769)])
    def should_reject_wrong_snapshot_size(self, data: bytes) -> None:
        with pytest.raises(ValueError, match="32 KiB"):
            model.verify_ram(data, SYMBOLS, 1)

    def should_reject_uninitialized_guards(self) -> None:
        with pytest.raises(ValueError, match="guards"):
            model.verify_ram(bytes(32768), SYMBOLS, 1)
