"""The GIME colour tables are what XRoar renders, and a wrong entry is caught."""

import instrumented_xroar
import numpy as np
import pytest
from gime import GIME_COMPOSITE, GIME_RGB
from gime_swatches import SwatchError, measure, palette_differences, swatch_colours
from native import ROOT, tool_path


def bands(colours: list[tuple[int, int, int]]) -> np.ndarray:
    """A 512x192 frame with 16 bands of 12 lines, as the swatch program shows them."""
    return np.repeat(np.array(colours, dtype=np.uint8), 12, axis=0)[:, None].repeat(512, axis=1)


COLOURS = [(r * 16, 255 - r * 16, r) for r in range(16)]


class DescribeSwatchColours:
    def should_read_each_band_from_register_zero_down(self) -> None:
        assert swatch_colours(bands(COLOURS)) == COLOURS

    def should_reject_a_band_of_more_than_one_colour(self) -> None:
        frame = bands(COLOURS)
        frame[12 * 5 + 6, 256] = (1, 2, 3)

        with pytest.raises(SwatchError, match="Band 5 holds 2 colours"):
            swatch_colours(frame)

    def should_ignore_the_edges_of_each_band(self) -> None:
        frame = bands(COLOURS)
        frame[12 * 3, :] = (9, 9, 9)
        frame[:, :16] = (9, 9, 9)

        assert swatch_colours(frame) == COLOURS

    def should_reject_a_frame_of_another_size(self) -> None:
        with pytest.raises(SwatchError, match="512x192"):
            swatch_colours(np.zeros((192, 640, 3), dtype=np.uint8))


class DescribeTableComparison:
    def should_find_no_difference_in_an_equal_table(self) -> None:
        assert palette_differences(list(GIME_RGB.colours), GIME_RGB.colours) == []

    def should_name_a_wrong_entry(self) -> None:
        measured = list(GIME_COMPOSITE.colours)
        measured[0x31] = (188, 255, 139)

        assert palette_differences(measured, GIME_COMPOSITE.colours) == [
            "$31: measured (188, 255, 139), table (188, 255, 138)"
        ]

    def should_report_a_missing_batch(self) -> None:
        assert palette_differences(list(GIME_RGB.colours[:48]), GIME_RGB.colours) == [
            "48 colours measured, 64 in the table"
        ]


def emulator_ready() -> bool:
    """LWTOOLS, the coco3 firmware, and an XRoar that is built or can be built."""
    host = instrumented_xroar.BuildHost()
    xroar = instrumented_xroar.status(ROOT, host)[0]
    xroar = xroar or not instrumented_xroar.missing_prerequisites(host)
    return bool(tool_path("lwasm") and xroar) and (ROOT / "local/roms/coco3").is_dir()


@pytest.fixture(scope="module")
def measured(tmp_path_factory: pytest.TempPathFactory) -> dict[str, list]:
    """All 64 codes on both inputs, measured once for the module."""
    if not emulator_ready():
        pytest.skip("LWTOOLS, XRoar or the coco3 firmware is not available")
    return measure(tmp_path_factory.mktemp("swatches") / "gime-swatches")


@pytest.mark.integration
class DescribeTheTablesInXRoar:
    """Measure all 64 codes again through scripts/coco.py; the tables must match exactly."""

    def should_match_the_composite_table(self, measured) -> None:
        assert palette_differences(measured["gime-composite"], GIME_COMPOSITE.colours) == []

    def should_match_the_rgb_table(self, measured) -> None:
        assert palette_differences(measured["gime-rgb"], GIME_RGB.colours) == []

    def should_show_the_two_inputs_differently(self, measured) -> None:
        assert measured["gime-composite"] != measured["gime-rgb"]
