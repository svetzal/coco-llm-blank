"""The GIME converter packs register numbers and chooses colour codes as the CoCo 3 needs."""

import json

import numpy as np
import pytest
from gime import (
    GIME_COMPOSITE,
    GIME_MODES,
    GIME_RGB,
    GimeMode,
    GimeOptions,
    assignment_error,
    candidate_codes,
    check_assignment,
    colour_samples,
    convert_gime_images,
    gime_assembly_block,
    gime_pixel_aspect,
    merge_locks,
    palette_assembly,
    palette_grid,
    palette_json,
    parse_gime_mode,
    parse_gime_palette,
    parse_palette_file,
    preview_columns,
    register_range,
    render_gime,
    select_palette,
)
from raster import GraphicsError, Prepared, srgb_to_linear

G320, G640X4, G640X2 = GIME_MODES["gime-320x16"], GIME_MODES["gime-640x4"], GIME_MODES["gime-640x2"]
# Composite colours of four codes (GIME_COMPOSITE): black, white, red, blue.
CODE_RGB = {0x00: (20, 20, 20), 0x30: (255, 255, 255), 0x07: (155, 18, 60), 0x0B: (34, 28, 222)}


def picture(rows: list[list[tuple[int, ...]]]) -> np.ndarray:
    return np.array([[(*p, 255)[:4] for p in row] for row in rows], dtype=np.uint8)


def grid(rows: list[list[tuple[int, ...]]]) -> Prepared:
    rgba = picture(rows)
    return Prepared(linear=srgb_to_linear(rgba[..., :3]), opaque=rgba[..., 3] >= 128)


def exact(mode, size, **extra) -> GimeOptions:
    """Options that map one source pixel to one target pixel without filtering."""
    return GimeOptions(mode=mode, size=size, fit="stretch", resample="nearest", **extra)


# Tepolt PDF 41-42 Table 4-10, as examples/gime-graphics lists them.
MODE_TABLE = {
    "gime-320x16": (4, 0b111, 0b10, 160, True),
    "gime-256x16": (4, 0b110, 0b10, 128, False),
    "gime-160x16": (4, 0b101, 0b10, 80, True),
    "gime-128x16": (4, 0b100, 0b10, 64, False),
    "gime-640x4": (2, 0b111, 0b01, 160, True),
    "gime-512x4": (2, 0b110, 0b01, 128, False),
    "gime-320x4": (2, 0b101, 0b01, 80, True),
    "gime-256x4": (2, 0b100, 0b01, 64, False),
    "gime-160x4": (2, 0b011, 0b01, 40, True),
    "gime-128x4": (2, 0b010, 0b01, 32, False),
    "gime-640x2": (1, 0b101, 0b00, 80, True),
    "gime-512x2": (1, 0b100, 0b00, 64, False),
    "gime-320x2": (1, 0b011, 0b00, 40, True),
    "gime-256x2": (1, 0b010, 0b00, 32, False),
    "gime-160x2": (1, 0b001, 0b00, 20, True),
    "gime-128x2": (1, 0b000, 0b00, 16, False),
    "gime-80x16": (4, 0b011, 0b10, 40, True),
    "gime-64x16": (4, 0b010, 0b10, 32, False),
    "gime-80x4": (2, 0b001, 0b01, 20, True),
    "gime-64x4": (2, 0b000, 0b01, 16, False),
}


class DescribeModeTable:
    def should_hold_the_twenty_modes_of_table_4_10(self) -> None:
        table = {
            name: (m.bits_per_pixel, m.hres, m.cres, m.bytes_per_row, m.full)
            for name, m in GIME_MODES.items()
        }

        assert table == MODE_TABLE

    def should_set_hres_bit_zero_exactly_on_full_width_modes(self) -> None:
        assert all(mode.full == bool(mode.hres & 1) for mode in GIME_MODES.values())

    def should_size_the_screen_by_its_rows(self) -> None:
        assert parse_gime_mode("GIME-320x16 ").bytes_total == 30720
        assert parse_gime_mode("gime-320x16", rows=225).bytes_total == 36000
        assert parse_gime_mode("gime-320x16", rows=200).height == 200

    def should_reject_other_row_counts_and_unknown_modes(self) -> None:
        with pytest.raises(GraphicsError, match="192, 200 or 225"):
            parse_gime_mode("gime-320x16", rows=199)
        with pytest.raises(GraphicsError, match="Known: gime-320x16"):
            parse_gime_mode("gime-640x16")
        with pytest.raises(ValueError, match="192, 200 or 225"):
            GimeMode.model_validate({**G320.model_dump(), "rows": 240})


class DescribePixelAspect:
    @pytest.mark.parametrize(
        ("name", "samples", "ntsc", "square"),
        [
            ("gime-320x16", 2, 6 / 7, 1.0),
            ("gime-256x16", 2, 6 / 7, 1.0),
            ("gime-640x4", 1, 3 / 7, 0.5),
            ("gime-512x2", 1, 3 / 7, 0.5),
            ("gime-160x16", 4, 12 / 7, 2.0),
            ("gime-64x4", 8, 24 / 7, 4.0),
        ],
    )
    def should_take_the_shape_of_its_share_of_the_line(self, name, samples, ntsc, square) -> None:
        mode = GIME_MODES[name]

        assert mode.samples_per_pixel == samples
        assert gime_pixel_aspect(mode, "ntsc") == pytest.approx(ntsc, abs=1e-5)
        assert gime_pixel_aspect(mode, "square") == square

    def should_preview_each_sample_in_the_display_proportion(self) -> None:
        assert preview_columns(G320, "ntsc") == (6, 7)
        assert preview_columns(G640X4, "ntsc") == (3, 7)
        assert preview_columns(G320, "square") == (2, 2)
        assert preview_columns(G640X4, "xroar") == (1, 1)


class DescribePalettes:
    def should_hold_one_colour_for_each_of_the_64_codes(self) -> None:
        assert len(GIME_COMPOSITE.colours) == len(GIME_RGB.colours) == 64

    def should_show_the_rgb_monitor_bits_as_r1_g1_b1_r0_g0_b0(self) -> None:
        levels = (2, 71, 166, 253)
        for code, (red, green, blue) in enumerate(GIME_RGB.colours):
            assert red == levels[(code >> 4) & 2 | (code >> 2) & 1]
            assert green == levels[(code >> 3) & 2 | (code >> 1) & 1]
            assert blue == levels[(code >> 2) & 2 | code & 1]

    def should_agree_with_the_gime_example_composite_colours(self) -> None:
        assert {code: GIME_COMPOSITE.colours[code] for code in CODE_RGB} == CODE_RGB

    def should_find_the_palettes_by_name(self) -> None:
        assert parse_gime_palette("gime-rgb") is GIME_RGB
        with pytest.raises(GraphicsError, match="known: gime-composite, gime-rgb"):
            parse_gime_palette("xroar")

    def should_offer_a_colour_only_once(self) -> None:
        candidates = candidate_codes(GIME_COMPOSITE, [0x30])

        assert 0x30 not in candidates and 0x3F not in candidates
        assert len(candidates) == len(set(GIME_COMPOSITE.colours)) - 1


class DescribeRegisterAssignments:
    def should_merge_locks_and_refuse_two_codes_for_one_register(self) -> None:
        assert merge_locks({1: 0x30}, {0: 0x00}, {1: 0x30}) == {0: 0x00, 1: 0x30}
        with pytest.raises(GraphicsError, match=r"locked to both \$30 and \$31"):
            merge_locks({1: 0x30}, {1: 0x31})

    @pytest.mark.parametrize(
        ("codes", "message"),
        [({4: 0}, "not one of the 4 registers 0-3"), ({0: 64}, "six-bit code")],
    )
    def should_reject_registers_and_codes_out_of_range(self, codes, message) -> None:
        with pytest.raises(GraphicsError, match=message):
            check_assignment(codes, 4)

    def should_give_the_whole_mode_without_a_span(self) -> None:
        assert register_range(None, 4) == [0, 1, 2, 3]
        assert register_range((8, 15), 16) == list(range(8, 16))
        with pytest.raises(GraphicsError, match="not inside"):
            register_range((2, 4), 4)


class DescribePaletteSelection:
    @pytest.fixture
    def four(self) -> tuple[np.ndarray, np.ndarray]:
        """Two pixels of each of four codes' exact composite colours."""
        return colour_samples([grid([[*CODE_RGB.values()] * 2])])

    def should_find_the_exact_codes_of_an_image_drawn_in_them(self, four) -> None:
        assignment = select_palette(*four, GIME_COMPOSITE, 4)

        assert sorted(assignment.values()) == sorted(CODE_RGB)
        assert assignment_error(*four, list(assignment.values()), GIME_COMPOSITE) == 0

    def should_fill_the_registers_from_the_darkest(self, four) -> None:
        assert select_palette(*four, GIME_COMPOSITE, 4) == {0: 0x00, 1: 0x0B, 2: 0x07, 3: 0x30}

    def should_keep_locked_registers_and_not_repeat_their_colour(self, four) -> None:
        assignment = select_palette(*four, GIME_COMPOSITE, 4, locks={3: 0x3F})

        assert assignment[3] == 0x3F
        assert 0x30 not in assignment.values()
        assert sorted(assignment.values()) == [0x00, 0x07, 0x0B, 0x3F]

    def should_choose_only_inside_the_span_and_keep_locks_outside_it(self, four) -> None:
        assignment = select_palette(*four, GIME_COMPOSITE, 16, (8, 11), {0: 0x00})

        assert list(assignment) == [0, 8, 9, 10, 11]
        assert assignment[0] == 0x00 and 0x00 in [assignment[r] for r in range(8, 12)]

    def should_give_the_same_codes_every_time(self) -> None:
        rng = np.random.default_rng(7)
        rows = rng.integers(0, 256, (24, 24, 3)).tolist()
        samples = colour_samples([grid([[tuple(p) for p in row] for row in rows])])

        assert select_palette(*samples, GIME_COMPOSITE, 16) == select_palette(
            *samples, GIME_COMPOSITE, 16
        )

    @pytest.mark.parametrize("palette", [GIME_COMPOSITE, GIME_RGB])
    def should_do_better_than_a_naive_choice_of_codes(self, palette) -> None:
        rng = np.random.default_rng(3)
        rows = rng.integers(0, 256, (20, 20, 3)).tolist()
        samples = colour_samples([grid([[tuple(p) for p in row] for row in rows])])

        chosen = list(select_palette(*samples, palette, 4).values())

        naive = [0x00, 0x10, 0x20, 0x30]
        assert assignment_error(*samples, chosen, palette) < assignment_error(
            *samples, naive, palette
        )

    def should_count_each_image_the_same_when_asked(self) -> None:
        big = grid([[CODE_RGB[0x07]] * 9])
        small = grid([[CODE_RGB[0x0B]]])

        _, weights = colour_samples([big, small], equal_weight=True)

        assert weights.tolist() == [1.0, 1.0]

    def should_choose_for_an_image_with_no_opaque_pixels(self) -> None:
        empty = grid([[(1, 2, 3, 0)]])

        assignment = select_palette(*colour_samples([empty]), GIME_COMPOSITE, 2)

        assert list(assignment) == [0, 1]
        assert assignment_error(*colour_samples([empty]), [0], GIME_COMPOSITE) == 0

    def should_reduce_a_large_image_before_counting_its_colours(self) -> None:
        prepared = palette_grid(np.zeros((40, 40, 4), dtype=np.uint8), 100)

        assert prepared.linear.shape == (10, 10, 3) and not prepared.opaque.any()


class DescribeConversion:
    def should_pack_four_bit_registers_leftmost_in_the_high_nibble(self) -> None:
        red, blue, white, black = (CODE_RGB[c] for c in (0x07, 0x0B, 0x30, 0x00))
        image = picture([[red, blue, white, black], [black, white, blue, red]])
        locks = {1: 0x07, 2: 0x0B, 3: 0x30, 4: 0x00}

        result = convert_gime_images([image], exact(G320, (4, 2), locks=locks, registers=(1, 4)))

        assert result.conversions[0].data == bytes([0x12, 0x34, 0x43, 0x21])
        assert result.assignment == locks

    def should_pack_two_bit_registers_leftmost_in_bits_seven_and_six(self) -> None:
        red, blue, white, black = (CODE_RGB[c] for c in (0x07, 0x0B, 0x30, 0x00))
        image = picture([[white, blue, red, black]])
        locks = {0: 0x00, 1: 0x07, 2: 0x0B, 3: 0x30}

        result = convert_gime_images([image], exact(G640X4, (4, 1), locks=locks))

        assert result.conversions[0].data == bytes([0b11_10_01_00])

    def should_pack_one_bit_registers_leftmost_in_bit_seven(self) -> None:
        white, black = CODE_RGB[0x30], CODE_RGB[0x00]
        image = picture([[white] + [black] * 7, [black] * 7 + [white]])

        result = convert_gime_images([image], exact(G640X2, (8, 2), locks={0: 0x00, 1: 0x30}))

        assert result.conversions[0].data == bytes([0x80, 0x01])

    def should_share_one_palette_across_images(self) -> None:
        red, blue = CODE_RGB[0x07], CODE_RGB[0x0B]
        images = [picture([[red] * 4]), picture([[blue] * 4])]

        result = convert_gime_images(images, exact(G640X2, (8, 1), pad=True))

        assert sorted(result.assignment.values()) == [0x07, 0x0B]
        assert [c.codes()[0, 0] for c in result.conversions] == [1, 0]

    def should_mask_transparent_pixels_and_give_them_register_zero(self) -> None:
        red = CODE_RGB[0x07]
        image = picture([[red, (*red, 0)]])

        conversion = convert_gime_images(
            [image], exact(G320, (2, 1), registers=(5, 5))
        ).conversions[0]

        assert conversion.data == bytes([0x50]) and conversion.mask == bytes([0x0F])

    def should_give_each_mosaic_block_one_register(self) -> None:
        red, blue = CODE_RGB[0x07], CODE_RGB[0x0B]
        image = picture([[red, red, blue, blue], [red, blue, blue, blue]])
        locks = {0: 0x07, 1: 0x0B}

        codes = (
            convert_gime_images(
                [image], exact(G640X2, (8, 2), locks=locks, pad=True, mosaic=(2, 2))
            )
            .conversions[0]
            .codes()
        )

        assert codes[:, :2].tolist() == [[0, 0], [0, 0]]
        assert codes[:, 2:4].tolist() == [[1, 1], [1, 1]]

    def should_fill_a_screen_of_the_chosen_rows(self) -> None:
        result = convert_gime_images(
            [picture([[CODE_RGB[0x30]] * 8] * 8)],
            GimeOptions(mode=parse_gime_mode("gime-80x4", 225)),
        )

        assert len(result.conversions[0].data) == 20 * 225


class DescribeRendering:
    def should_render_registers_with_their_codes_colours(self) -> None:
        codes = np.array([[0, 1]], dtype=np.uint8)

        frame = render_gime(codes, G640X2, {0: 0x07, 1: 0x0B}, GIME_COMPOSITE, 2, 3)

        assert frame.shape == (3, 4, 3)
        assert [tuple(frame[2, x]) for x in (1, 2)] == [CODE_RGB[0x07], CODE_RGB[0x0B]]

    def should_round_trip_a_conversion_to_its_source_colours(self) -> None:
        source = [[CODE_RGB[c] for c in (0x30, 0x07, 0x0B, 0x00)]]

        result = convert_gime_images([picture(source)], exact(G320, (4, 1)))
        frame = render_gime(result.conversions[0].codes(), G320, result.assignment, GIME_COMPOSITE)

        assert frame.tolist() == [[list(p) for p in source[0]]]

    def should_name_registers_the_palette_does_not_set(self) -> None:
        with pytest.raises(GraphicsError, match=r"registers \[3\]"):
            render_gime(np.array([[0, 3]], dtype=np.uint8), G320, {0: 0}, GIME_COMPOSITE)


class DescribeOutputs:
    @pytest.fixture
    def assignment(self) -> dict[int, int]:
        return {0: 0x00, 1: 0x30, 3: 0x07}

    def should_write_every_register_of_the_mode_from_register_zero(self, assignment) -> None:
        text = palette_assembly("art_palette", assignment, GIME_COMPOSITE, G640X4)

        assert "registers 0-3 ($FFB0-$FFB3)" in text
        assert "gime-composite" in text and "register  3: $07 (155, 18, 60)" in text
        assert "Registers [2] are not set" in text
        assert text.endswith("art_palette_count equ 4\nart_palette\n        fcb $00,$30,$00,$07\n")

    def should_read_back_the_json_it_writes(self, assignment) -> None:
        text = palette_json(assignment, GIME_RGB, G640X4)

        document = json.loads(text)
        assert document["palette"] == "gime-rgb" and document["mode"] == "gime-640x4"
        assert document["registers"][2] == {
            "register": 3, "code": 7, "hex": "$07", "rgb": [71, 71, 71]
        }  # fmt: skip
        assert parse_palette_file(text) == (assignment, "gime-rgb")

    @pytest.mark.parametrize(
        "text",
        [
            "not json",
            '{"palette": "gime-rgb", "registers": [{"register": 16, "code": 0}]}',
            '{"palette": "gime-rgb", "registers": [{"register": 0, "code": 64}]}',
            '{"palette": "x", "registers": [{"register": 1, "code": 0}, {"register": 1, "code": 2}]}',
        ],
    )
    def should_reject_a_document_that_is_not_a_palette(self, text: str) -> None:
        with pytest.raises(GraphicsError, match="art.json is not a palette file"):
            parse_palette_file(text, "art.json")

    def should_describe_register_bytes_and_add_the_mask(self) -> None:
        image = picture([[CODE_RGB[0x07], (0, 0, 0, 0)]])
        conversion = convert_gime_images([image], exact(G320, (2, 1))).conversions[0]

        text = gime_assembly_block("hero", conversion, with_mask=True)

        assert "* hero: 2x1 gime-320x16 pixels, 4 bits each, 1 bytes per row, 1 bytes." in text
        assert "palette registers" in text and "\nhero_mask\n        fcb $0F\n" in text
