"""The first-screen model specifies exact pixels and rejects startup RAM."""

from pathlib import Path

import pytest
from coco import load_expected, load_project, verify_snapshot

HERE = Path(__file__).parent
model = load_expected(HERE)


@pytest.fixture
def good_ram() -> bytearray:
    ram = bytearray(32768)
    ram[0x2FFF] = 0xA5
    ram[0x400:0x1C00] = model.expected_screen(1)
    return ram


class DescribeFirstScreen:
    def should_specify_exact_pixel_positions(self) -> None:
        screen = model.expected_screen(1)

        assert len(screen) == 6144
        assert screen[:32] == b"\xff" * 32
        assert screen[-32:] == b"\xff" * 32
        assert screen[32:64] == b"\x80" + b"\0" * 30 + b"\x01"
        assert screen[64 * 32 + 12 : 64 * 32 + 20] == b"\xff" * 8
        assert screen[128 * 32 + 12 : 128 * 32 + 20] == b"\0" * 8

    def should_accept_the_specified_memory(self, good_ram: bytearray) -> None:
        assert verify_snapshot(load_project(HERE), model, good_ram, {}, 1) == 6144

    def should_reject_one_wrong_screen_byte(self, good_ram: bytearray) -> None:
        good_ram[0xC0C] = 0

        with pytest.raises(ValueError, match=r"1 of 6144 screen bytes differ; first at \$0C0C"):
            verify_snapshot(load_project(HERE), model, good_ram, {}, 1)

    def should_specify_the_rendered_picture_with_bit_seven_leftmost(self) -> None:
        frame = model.expected_frame(1)

        assert frame.shape == (192, 512, 3)
        assert {tuple(colour) for colour in frame.reshape(-1, 3)} == {model.BLACK, model.GREEN}
        assert [tuple(frame[1, x]) for x in (0, 1, 2, 509, 510, 511)] == [
            model.GREEN,
            model.GREEN,
            model.BLACK,
            model.BLACK,
            model.GREEN,
            model.GREEN,
        ]
        assert tuple(frame[64, 191]) == model.BLACK and tuple(frame[64, 192]) == model.GREEN
        assert tuple(frame[127, 319]) == model.GREEN and tuple(frame[128, 319]) == model.BLACK

    @pytest.mark.parametrize("data", [b"", bytes(32768)])
    def should_reject_startup_memory(self, data: bytes) -> None:
        with pytest.raises(ValueError, match="initialized"):
            model.verify_ram(data, {}, 1)
