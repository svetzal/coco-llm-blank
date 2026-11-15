"""The CoCo 3 page-flip model specifies five scenes, both buffers and the picture."""

from pathlib import Path

import pytest
from coco import ProjectError, load_expected, load_project, verify_picture
from recording import Picture

HERE = Path(__file__).parent
model = load_expected(HERE)
SYMBOLS = {"scene": 0x3100, "back": 0x3101}


def snapshot(frame: int, kib: int = 128) -> bytearray:
    ram = bytearray(kib * 1024)
    for guard in model.GUARDS:
        ram[guard] = 0xA5
    drawn = model.BUFFERS[(frame - 1) % 2]
    ram[drawn : drawn + 6144] = model.expected_screen(frame)
    state = len(ram) - 0x10000
    ram[state + 0x3100] = model.scene(frame)
    ram[state + 0x3101 : state + 0x3103] = drawn.to_bytes(2, "big")
    return ram


class DescribePageFlipCoco3:
    def should_move_the_square_right_and_wrap_after_five_scenes(self) -> None:
        assert [model.scene(frame) for frame in range(1, 8)] == [0, 1, 2, 3, 4, 0, 1]
        # Row 80: byte 4 holds the square in scene 0, byte 6 in scene 1.
        assert model.expected_screen(1)[80 * 32 + 4] == 0xFF
        assert model.expected_screen(2)[80 * 32 + 4 : 80 * 32 + 7] == b"\0\0\xff"

    def should_specify_the_outline(self) -> None:
        screen = model.expected_screen(1)

        assert screen[:32] == screen[-32:] == b"\xff" * 32
        assert screen[32:64] == b"\x80" + b"\0" * 30 + b"\x01"

    @pytest.mark.parametrize("kib", [128, 512])
    @pytest.mark.parametrize("frame", [1, 2, 6])
    def should_accept_the_drawn_buffer_at_either_size(self, frame: int, kib: int) -> None:
        model.verify_ram(snapshot(frame, kib), SYMBOLS, frame)

    @pytest.mark.parametrize("address", [*model.GUARDS, 0x4100, 0x58FF, 0x13100, 0x13102])
    def should_reject_any_damaged_byte(self, address: int) -> None:
        damaged = snapshot(1)
        damaged[address] ^= 1

        with pytest.raises(ValueError):
            model.verify_ram(damaged, SYMBOLS, 1)

    def should_reject_a_scene_drawn_into_the_shown_buffer(self) -> None:
        ram = snapshot(2)
        ram[0x4100:0x5900] = model.expected_screen(2)
        ram[0x13101:0x13103] = b"\x41\x00"

        with pytest.raises(ValueError, match=r"drawn at \$4100"):
            model.verify_ram(ram, SYMBOLS, 2)

    @pytest.mark.parametrize("data", [b"", bytes(131072)])
    def should_reject_startup_or_missing_ram(self, data: bytes) -> None:
        with pytest.raises(ValueError, match="RAM"):
            model.verify_ram(data, SYMBOLS, 1)

    def should_render_white_where_set_with_two_samples_per_pixel(self) -> None:
        frame = model.expected_frame(1)

        assert frame.shape == (192, 512, 3)
        assert {tuple(colour) for colour in frame.reshape(-1, 3)} == {model.BLACK, model.WHITE}
        assert [tuple(frame[80, x]) for x in (63, 64, 79, 80)] == [
            model.BLACK,
            model.WHITE,
            model.WHITE,
            model.BLACK,
        ]

    def should_reject_the_previous_scene(self) -> None:
        picture = Picture(path=HERE, pixels=model.expected_frame(1))

        with pytest.raises(ProjectError, match="Frame 2: rendered display"):
            verify_picture(load_project(HERE), model, picture, 2)
