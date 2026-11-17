"""The shared pixel core reduces colours in blocks and packs masks as both converters need."""

import numpy as np
import pytest
from pydantic import ValidationError
from raster import (
    ArtOptions,
    GraphicsError,
    as_rgba,
    fcb_rows,
    mosaic_codes,
    pack_with_mask,
    quantize,
    srgb_to_linear,
)

BLACK, WHITE, GREY, LIGHT = (0, 0, 0), (255, 255, 255), (128, 128, 128), (188, 188, 188)
PALETTE = srgb_to_linear(np.array([BLACK, WHITE, GREY]))


def linear(rows: list[list[tuple[int, int, int]]]) -> np.ndarray:
    return srgb_to_linear(np.array(rows, dtype=np.uint8))


class DescribeMosaic:
    def should_give_every_pixel_of_a_block_one_code(self) -> None:
        rows = [[BLACK, WHITE, BLACK, BLACK], [WHITE, BLACK, BLACK, BLACK]] * 2
        opaque = np.ones((4, 4), dtype=bool)

        codes = mosaic_codes(linear(rows), opaque, PALETTE, (2, 2))

        for top in (0, 2):
            for left in (0, 2):
                assert len(np.unique(codes[top : top + 2, left : left + 2])) == 1

    def should_choose_the_colour_nearest_the_block_mean_in_linear_light(self) -> None:
        # Half black and half white is linear 0.5, sRGB 188: the light grey. Averaging the
        # sRGB values instead would give 128, the darker grey.
        palette = srgb_to_linear(np.array([BLACK, WHITE, GREY, LIGHT]))
        pixels = linear([[BLACK, WHITE], [WHITE, BLACK]])

        codes = mosaic_codes(pixels, np.ones((2, 2), dtype=bool), palette, (2, 2))

        assert codes.tolist() == [[3, 3], [3, 3]]

    def should_average_only_the_opaque_pixels(self) -> None:
        pixels = linear([[WHITE, BLACK, BLACK, BLACK]])
        opaque = np.array([[True, False, False, False]])

        codes = quantize(pixels, opaque, PALETTE, mosaic=(4, 1))

        assert codes.tolist() == [[1, 0, 0, 0]]

    def should_cut_smaller_blocks_at_the_right_and_bottom_edges(self) -> None:
        pixels = linear([[BLACK, BLACK, WHITE], [BLACK, BLACK, WHITE], [WHITE, WHITE, WHITE]])

        codes = mosaic_codes(pixels, np.ones((3, 3), dtype=bool), PALETTE, (2, 2))

        assert codes.tolist() == [[0, 0, 1], [0, 0, 1], [1, 1, 1]]

    def should_match_nearest_colour_reduction_with_one_pixel_blocks(self) -> None:
        pixels = linear([[BLACK, GREY, WHITE, (90, 90, 90)]])
        opaque = np.ones((1, 4), dtype=bool)

        assert np.array_equal(
            quantize(pixels, opaque, PALETTE, mosaic=(1, 1)), quantize(pixels, opaque, PALETTE)
        )

    def should_refuse_to_dither_a_mosaic(self) -> None:
        with pytest.raises(GraphicsError, match="cannot also dither"):
            quantize(linear([[GREY]]), np.ones((1, 1), dtype=bool), PALETTE, "bayer", 1.0, (2, 2))

    def should_reject_an_empty_block(self) -> None:
        with pytest.raises(GraphicsError, match="at least 1x1"):
            mosaic_codes(linear([[GREY]]), np.ones((1, 1), dtype=bool), PALETTE, (0, 2))

    def should_refuse_options_that_ask_for_a_mosaic_and_a_dither(self) -> None:
        with pytest.raises(ValidationError, match="cannot also dither"):
            ArtOptions(mosaic=(2, 2), dither="floyd-steinberg")


class DescribePackingWithAMask:
    @pytest.mark.parametrize(
        ("bits", "codes", "data", "mask"),
        [
            (1, [1, 0, 1], [0b10100000], [0b00011111]),
            (2, [3, 1, 2], [0b11011000], [0b00000011]),
            (4, [15, 2, 9], [0xF2, 0x90], [0x00, 0x0F]),
        ],
    )
    def should_pad_to_whole_bytes_with_transparent_code_zero(self, bits, codes, data, mask) -> None:
        packed = pack_with_mask(np.array([codes], dtype=np.uint8), np.ones((1, 3), bool), bits)

        assert (packed.data, packed.mask) == (bytes(data), bytes(mask))
        assert packed.width == 8 // bits * len(data)

    def should_set_every_bit_of_a_transparent_pixel_in_the_mask(self) -> None:
        packed = pack_with_mask(np.array([[5, 0]], dtype=np.uint8), np.array([[True, False]]), 4)

        assert (packed.data, packed.mask) == (bytes([0x50]), bytes([0x0F]))


class DescribeHelpers:
    def should_break_rows_into_lines_of_sixteen_bytes(self) -> None:
        lines = fcb_rows("data", bytes(range(20)), 20)

        assert lines[0] == "data"
        assert lines[1].count("$") == 16 and lines[2] == "        fcb $10,$11,$12,$13"

    def should_add_an_opaque_alpha_to_rgb(self) -> None:
        assert as_rgba(np.zeros((1, 1, 3), dtype=np.uint8))[0, 0].tolist() == [0, 0, 0, 255]
