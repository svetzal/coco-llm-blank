"""The palette-swatch model specifies every colour-set colour and rejects swapped colours."""

from pathlib import Path

import numpy as np
import pytest
from coco import ProjectError, load_expected, load_project, verify_picture, verify_snapshot
from recording import Picture

HERE = Path(__file__).parent
model = load_expected(HERE)
VARIANTS = ["", "css1", "rg6", "rg6-css1"]


def colours(frame: np.ndarray) -> list[tuple[int, ...]]:
    """The colour at the left of each 32-pixel bar, then the first four order-band pixels."""
    bars = [tuple(int(v) for v in frame[0, x]) for x in (0, 128, 256, 384)]
    return bars + [tuple(int(v) for v in frame[191, x]) for x in (0, 4, 8, 12)]


class DescribePaletteSwatches:
    def should_specify_four_bars_and_an_order_band(self) -> None:
        screen = model.expected_screen(1, "")

        assert len(screen) == 6144
        assert screen[:32] == b"\x00" * 8 + b"\x55" * 8 + b"\xaa" * 8 + b"\xff" * 8
        assert screen[159 * 32 : 160 * 32] == screen[:32]
        assert screen[160 * 32 :] == b"\x1b" * 1024

    def should_render_colour_set_zero_left_to_right(self) -> None:
        green, yellow, blue, red = (46, 188, 36), (255, 255, 151), (44, 37, 129), (131, 26, 55)

        assert colours(model.expected_frame(1, "")) == [green, yellow, blue, red] * 2

    def should_render_colour_set_one_left_to_right(self) -> None:
        buff, cyan, magenta, orange = (
            (255, 255, 255),
            (46, 173, 115),
            (255, 90, 255),
            (255, 112, 59),
        )

        assert colours(model.expected_frame(1, "css1")) == [buff, cyan, magenta, orange] * 2

    @pytest.mark.parametrize(("variant", "black", "lit"), [("rg6", (0, 31, 0), (46, 188, 36)),
                                                           ("rg6-css1", (13, 13, 13), (255,) * 3)])  # fmt: skip
    def should_render_two_colour_bars_bit_seven_leftmost(self, variant, black, lit) -> None:
        frame = model.expected_frame(1, variant)

        assert frame.shape == (192, 512, 3)
        assert [tuple(int(v) for v in frame[0, 128 + x]) for x in range(0, 8, 2)] == [
            black,
            lit,
        ] * 2
        # $1B is 00011011: three dark pixels, two lit, one dark, two lit.
        row = [tuple(int(v) for v in frame[191, x]) for x in range(0, 16, 2)]
        assert row == [black] * 3 + [lit] * 2 + [black] + [lit] * 2

    @pytest.mark.parametrize("variant", VARIANTS)
    def should_accept_its_own_picture(self, variant: str) -> None:
        project = load_project(HERE)
        frame = model.expected_frame(1, variant)

        assert verify_picture(project, model, Picture(path=HERE, pixels=frame), 1, variant) == 98304

    @pytest.mark.parametrize(("variant", "other"), [("", "css1"), ("rg6", "rg6-css1"), ("", "rg6")])
    def should_reject_the_other_colour_set_or_mode(self, variant: str, other: str) -> None:
        wrong = Picture(path=HERE, pixels=model.expected_frame(1, other))

        with pytest.raises(ProjectError, match="rendered samples differ"):
            verify_picture(load_project(HERE), model, wrong, 1, variant)

    def should_reject_swapped_yellow_and_blue(self) -> None:
        frame = model.expected_frame(1, "").copy()
        yellow, blue = frame[0, 128].copy(), frame[0, 256].copy()
        was_yellow, was_blue = np.all(frame == yellow, axis=2), np.all(frame == blue, axis=2)
        frame[was_yellow], frame[was_blue] = blue, yellow

        with pytest.raises(ProjectError, match="49152 of 98304"):
            verify_picture(load_project(HERE), model, Picture(path=HERE, pixels=frame), 1, "")

    def should_accept_the_specified_memory(self) -> None:
        ram = bytearray(32768)
        ram[0x2FFF] = 0xA5
        ram[0x400:0x1C00] = model.expected_screen(1, "")

        assert verify_snapshot(load_project(HERE), model, ram, {}, 1, "css1") == 6144

    @pytest.mark.parametrize("data", [b"", bytes(32768)])
    def should_reject_startup_memory(self, data: bytes) -> None:
        with pytest.raises(ValueError, match="initialized"):
            model.verify_ram(data, {}, 1, "")
