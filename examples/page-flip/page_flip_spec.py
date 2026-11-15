"""The page-flip model specifies both screens, the scene and the rendered picture."""

from pathlib import Path

import numpy as np
import pytest
from coco import ProjectError, load_expected, load_project, verify_picture
from recording import Picture

HERE = Path(__file__).parent
model = load_expected(HERE)
SYMBOLS = {"drawing": 0x4200, "frames": 0x4202, "xpos": 0x4204, "ypos": 0x4205}


def snapshot(frame: int) -> bytearray:
    ram = bytearray(32768)
    for guard in model.GUARDS:
        ram[guard] = 0xA5
    drawn = model.SCREENS[frame % 2]
    ram[drawn : drawn + 6144] = model.expected_screen(frame)
    ram[0x4200:0x4202] = drawn.to_bytes(2, "big")
    ram[0x4202:0x4204] = frame.to_bytes(2, "big")
    ram[0x4204], ram[0x4205] = model.position(frame)
    return ram


class DescribePageFlip:
    def should_specify_the_moving_objects_scene(self) -> None:
        # Frame 16: both occupy x=120..135, B (black) in front at y=15.
        assert model.expected_screen(16)[15 * 32 + 15 : 15 * 32 + 17] == b"\0\0"
        # Frame 46: same x position, A (set) in front at y=45.
        assert model.expected_screen(46)[45 * 32 + 15 : 45 * 32 + 17] == b"\xff\xff"
        # Scenery not covered by either object inverts at frame 64.
        assert model.expected_screen(63)[0] == 0
        assert model.expected_screen(64)[0] == 255

    def should_bound_every_motion_tick(self) -> None:
        assert {model.position(frame)[0] for frame in range(1, 61)} == set(range(31))
        assert {model.position(frame)[1] for frame in range(1, 369)} == set(range(185))

    @pytest.mark.parametrize("frame", [1, 2])
    def should_accept_the_drawn_screen_at_either_base(self, frame: int) -> None:
        model.verify_ram(snapshot(frame), SYMBOLS, frame)

    @pytest.mark.parametrize("address", [*model.GUARDS, 0x2400, 0x3BFF, 0x4201, 0x4203, 0x4205])
    def should_reject_any_damaged_byte(self, address: int) -> None:
        damaged = snapshot(1)
        damaged[address] ^= 1

        with pytest.raises(ValueError):
            model.verify_ram(damaged, SYMBOLS, 1)

    def should_reject_a_drawing_pointer_that_is_not_a_screen(self) -> None:
        damaged = snapshot(1)
        damaged[0x4200:0x4202] = b"\x30\x00"

        with pytest.raises(ValueError, match=r"\$3000"):
            model.verify_ram(damaged, SYMBOLS, 1)

    @pytest.mark.parametrize("data", [b"", bytes(32768)])
    def should_reject_startup_or_missing_ram(self, data: bytes) -> None:
        with pytest.raises(ValueError, match="RAM"):
            model.verify_ram(data, SYMBOLS, 1)

    def should_render_two_samples_per_pixel_with_bit_seven_leftmost(self) -> None:
        frame = model.expected_frame(1)

        assert frame.shape == (192, 512, 3)
        assert {tuple(colour) for colour in frame.reshape(-1, 3)} == {model.BLACK, model.GREEN}
        # Frame 1: A (set) at x=0..15, y=0..7 over a clear first checker cell.
        assert tuple(frame[0, 0]) == tuple(frame[7, 31]) == model.GREEN
        assert tuple(frame[8, 0]) == model.GREEN and tuple(frame[8, 16]) == model.BLACK
        assert tuple(frame[0, 32]) == model.BLACK and tuple(frame[0, 48]) == model.GREEN

    def should_reject_a_picture_with_the_previous_frame_partly_erased(self) -> None:
        picture = model.expected_frame(2).copy()
        picture[:4] = model.expected_frame(3)[:4]

        with pytest.raises(ProjectError, match="Frame 2: rendered display"):
            verify_picture(load_project(HERE), model, Picture(path=HERE, pixels=picture), 2)

    def should_accept_the_complete_rendered_frame(self) -> None:
        picture = Picture(path=HERE, pixels=np.array(model.expected_frame(370)))

        assert verify_picture(load_project(HERE), model, picture, 370) == 98304
