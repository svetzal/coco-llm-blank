"""The VDG graphics converter packs, renders and converts as the MC6847 layout specifies."""

from pathlib import Path

import numpy as np
import pytest
from graphics import (
    MODES,
    XROAR,
    ConvertOptions,
    GraphicsError,
    Palette,
    VdgColour,
    assembly_block,
    assembly_include,
    border_colour,
    check_label,
    colour_set,
    convert_image,
    convert_images,
    crop_box,
    crop_to_aspect,
    half_clock_width,
    label_from_name,
    linear_to_lab,
    main,
    pack,
    palette_rgb,
    palette_spread,
    parse_mode,
    parse_palette,
    pixel_aspect,
    preview_scale,
    quantize,
    render,
    slice_cells,
    srgb_to_linear,
    unpack,
)
from PIL import Image

CG6, RG6, CG1 = MODES["CG6"], MODES["RG6"], MODES["CG1"]
RED, YELLOW, BLUE, GREEN = (131, 26, 55), (255, 255, 151), (44, 37, 129), (46, 188, 36)
BUFF, CYAN = (255, 255, 255), (46, 173, 115)


def picture(rows: list[list[tuple[int, ...]]]) -> np.ndarray:
    """An RGBA array from rows of RGB or RGBA tuples."""
    return np.array([[(*p, 255)[:4] for p in row] for row in rows], dtype=np.uint8)


def exact(mode, size, **extra) -> ConvertOptions:
    """Options that map one source pixel to one target pixel without filtering."""
    return ConvertOptions(mode=mode, size=size, fit="stretch", resample="nearest", **extra)


def save(path: Path, rows: list[list[tuple[int, ...]]]) -> Path:
    Image.fromarray(picture(rows), "RGBA").save(path)
    return path


class DescribeModeTable:
    def should_cover_the_same_display_window_in_every_mode(self) -> None:
        for mode in MODES.values():
            assert mode.width * mode.half_clocks == 256
            assert mode.height * mode.scan_lines == 192

    def should_need_the_memory_table_two_lists(self) -> None:
        sizes = {name: mode.bytes_total for name, mode in MODES.items()}

        assert sizes == {
            "CG1": 1024,
            "RG1": 1024,
            "CG2": 2048,
            "RG2": 1536,
            "CG3": 3072,
            "RG3": 3072,
            "CG6": 6144,
            "RG6": 6144,
        }

    def should_give_cg2_two_half_clocks_by_three_lines(self) -> None:
        cg2 = MODES["CG2"]

        assert (cg2.width, cg2.height, cg2.half_clocks, cg2.scan_lines) == (128, 64, 2, 3)
        assert (cg2.bits_per_pixel, cg2.bytes_per_row, cg2.colour_count) == (2, 32, 4)

    def should_find_modes_regardless_of_case(self) -> None:
        assert parse_mode(" cg6 ") is CG6

    @pytest.mark.parametrize("name", ["HSCREEN2", "CG4", ""])
    def should_reject_unknown_modes_and_name_the_coco3_limit(self, name: str) -> None:
        with pytest.raises(GraphicsError, match="GIME modes are not supported"):
            parse_mode(name)


class DescribeColourSets:
    def should_list_four_colour_codes_in_order(self) -> None:
        assert colour_set(CG6, 0) == ("green", "yellow", "blue", "red")
        assert colour_set(CG6, 1) == ("buff", "cyan", "magenta", "orange")

    def should_list_two_colour_codes_in_order(self) -> None:
        assert colour_set(RG6, 0) == ("black", "green")
        assert colour_set(RG6, 1) == ("black", "buff")

    def should_give_the_border_by_colour_set(self) -> None:
        assert (border_colour(0), border_colour(1)) == ("green", "buff")

    def should_reject_a_colour_set_other_than_zero_or_one(self) -> None:
        with pytest.raises(GraphicsError, match="0 or 1"):
            colour_set(CG6, 2)


class DescribePalettes:
    def should_give_black_by_colour_set(self) -> None:
        assert XROAR.rgb(VdgColour.BLACK, 0) == (0, 31, 0)
        assert XROAR.rgb(VdgColour.BLACK, 1) == (13, 13, 13)
        assert XROAR.rgb(VdgColour.RED, 1) == RED

    def should_index_mode_colours_by_pixel_code(self) -> None:
        assert palette_rgb(CG6, 0, XROAR).tolist() == [
            list(GREEN),
            list(YELLOW),
            list(BLUE),
            list(RED),
        ]
        assert palette_rgb(RG6, 1, XROAR).tolist() == [[13, 13, 13], list(BUFF)]

    def should_require_every_colour_but_black(self) -> None:
        colours = dict(XROAR.colours)
        del colours[VdgColour.CYAN]

        with pytest.raises(ValueError, match="every VDG colour"):
            Palette(name="x", description="x", colours=colours, black=XROAR.black)

    def should_reject_an_unknown_palette(self) -> None:
        with pytest.raises(GraphicsError, match="known: xroar"):
            parse_palette("tv")


class DescribePixelAspect:
    def should_make_an_ntsc_half_clock_six_sevenths_of_a_line(self) -> None:
        assert half_clock_width("ntsc") == pytest.approx(6 / 7, abs=1e-5)

    @pytest.mark.parametrize(
        ("name", "ntsc", "square"),
        [("RG6", 6 / 7, 1.0), ("CG6", 12 / 7, 2.0), ("CG1", 8 / 7, 4 / 3), ("RG1", 4 / 7, 2 / 3)],
    )
    def should_scale_half_clocks_by_scan_lines(self, name: str, ntsc: float, square: float) -> None:
        assert pixel_aspect(MODES[name], "ntsc") == pytest.approx(ntsc, abs=1e-5)
        assert pixel_aspect(MODES[name], "square") == square

    def should_preview_in_whole_samples_of_the_same_proportion(self) -> None:
        assert preview_scale("ntsc") == (6, 7)
        assert preview_scale("square") == (2, 2)

    def should_reject_an_unknown_display(self) -> None:
        with pytest.raises(GraphicsError, match="Unknown display"):
            half_clock_width("pal")  # type: ignore[arg-type]


class DescribePacking:
    def should_put_the_leftmost_one_bit_pixel_in_bit_seven(self) -> None:
        codes = np.zeros((2, 16), dtype=np.uint8)
        codes[0, 0] = 1
        codes[1, 15] = 1

        assert pack(codes, 1) == bytes([0x80, 0x00, 0x00, 0x01])

    def should_not_match_reversed_bit_order(self) -> None:
        codes = np.array([[1, 0, 0, 0, 0, 0, 0, 0]], dtype=np.uint8)

        assert pack(codes, 1) != bytes([0x01])

    def should_put_the_leftmost_two_bit_pixel_in_bits_seven_and_six(self) -> None:
        codes = np.array([[3, 2, 1, 0], [0, 1, 2, 3]], dtype=np.uint8)

        assert pack(codes, 2) == bytes([0xE4, 0x1B])

    def should_keep_the_high_bit_of_each_pair_as_the_high_bit_of_the_code(self) -> None:
        assert pack(np.array([[2, 0, 0, 0]], dtype=np.uint8), 2) == bytes([0x80])

    def should_round_trip_through_unpack(self) -> None:
        codes = np.arange(24, dtype=np.uint8).reshape(3, 8) % 4

        assert np.array_equal(unpack(pack(codes, 2), 8, 3, 2), codes)

    def should_reject_a_width_that_leaves_part_of_a_byte(self) -> None:
        with pytest.raises(GraphicsError, match="whole number"):
            pack(np.zeros((1, 6), dtype=np.uint8), 2)

    def should_reject_a_code_too_large_for_the_mode(self) -> None:
        with pytest.raises(GraphicsError, match="does not fit"):
            pack(np.full((1, 8), 2, dtype=np.uint8), 1)

    @pytest.mark.parametrize(("data", "width"), [(b"\0", 8), (b"\0\0", 6), (b"", 0)])
    def should_reject_bytes_that_do_not_fill_the_size(self, data: bytes, width: int) -> None:
        with pytest.raises(GraphicsError):
            unpack(data, width, 2, 1)


class DescribeRendering:
    def should_span_each_pixel_over_its_half_clocks_and_lines(self) -> None:
        codes = np.array([[0, 3]], dtype=np.uint8)

        frame = render(codes, CG6, 0, XROAR, samples_per_half_clock=2)

        assert frame.shape == (1, 8, 3)
        assert [tuple(v) for v in frame[0]] == [GREEN] * 4 + [RED] * 4

    def should_repeat_rows_for_taller_pixels(self) -> None:
        frame = render(np.array([[1, 0, 0, 0]], dtype=np.uint8), CG1, 1, XROAR)

        assert frame.shape == (3, 16, 3)
        assert tuple(frame[2, 3]) == CYAN and tuple(frame[2, 4]) == BUFF

    def should_change_every_colour_when_the_colour_set_swaps(self) -> None:
        codes = np.array([[0, 1, 2, 3]], dtype=np.uint8)

        assert np.all(render(codes, CG6, 0, XROAR) != render(codes, CG6, 1, XROAR))


class DescribeColourMatching:
    def should_map_sRGB_endpoints_to_linear_light(self) -> None:
        assert srgb_to_linear(np.array([0, 255])).tolist() == [0.0, 1.0]
        assert srgb_to_linear(np.array([128]))[0] == pytest.approx(0.2158605)

    def should_place_white_and_black_at_the_ends_of_lightness(self) -> None:
        assert linear_to_lab(np.array([1.0, 1.0, 1.0])) == pytest.approx([100, 0, 0], abs=0.01)
        assert linear_to_lab(np.array([0.0, 0.0, 0.0])) == pytest.approx([0, 0, 0], abs=0.01)

    @pytest.mark.parametrize(
        ("rgb", "css", "code"),
        [
            ((255, 0, 0), 0, 3),
            ((255, 255, 255), 0, 1),
            ((0, 0, 80), 0, 2),
            ((0, 255, 0), 0, 0),
            ((255, 255, 255), 1, 0),
            ((255, 0, 255), 1, 2),
            ((255, 128, 0), 1, 3),
        ],
    )
    def should_choose_the_perceptually_nearest_colour(self, rgb, css: int, code: int) -> None:
        linear = srgb_to_linear(np.array([[rgb]]))
        opaque = np.ones((1, 1), dtype=bool)

        codes = quantize(linear, opaque, srgb_to_linear(palette_rgb(CG6, css, XROAR)))

        assert codes[0, 0] == code


class DescribeDithering:
    @pytest.fixture
    def grey(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Pixels halfway, in linear light, between RG6's two colours."""
        palette = srgb_to_linear(palette_rgb(RG6, 0, XROAR))
        linear = np.broadcast_to(palette.mean(axis=0), (8, 8, 3)).copy()
        return linear, np.ones((8, 8), dtype=bool), palette

    def should_pick_one_colour_without_dithering(self, grey) -> None:
        assert len(np.unique(quantize(*grey))) == 1

    @pytest.mark.parametrize("dither", ["bayer", "floyd-steinberg"])
    def should_mix_both_colours_for_a_grey_between_them(self, grey, dither) -> None:
        assert set(np.unique(quantize(*grey, dither=dither)).tolist()) == {0, 1}

    @pytest.mark.parametrize("dither", ["none", "bayer", "floyd-steinberg"])
    def should_give_the_same_codes_every_time(self, grey, dither) -> None:
        assert np.array_equal(quantize(*grey, dither=dither), quantize(*grey, dither=dither))

    def should_leave_transparent_pixels_at_code_zero(self, grey) -> None:
        linear, opaque, palette = grey
        linear = np.ones_like(linear) * srgb_to_linear(np.array(GREEN))
        opaque[0, 0] = False

        codes = quantize(linear, opaque, palette, dither="floyd-steinberg")

        assert codes[0, 0] == 0 and codes[0, 1] == 1

    def should_not_let_unreachable_colours_pile_up_diffused_error(self) -> None:
        # Saturated blue lies outside the CSS=0 colours; beside it, exact palette green must
        # stay green past the edge columns rather than absorb accumulated error.
        rows = [[(0, 0, 255)] * 16 + [GREEN] * 16] * 16
        linear = srgb_to_linear(np.array(rows))
        palette = srgb_to_linear(palette_rgb(CG6, 0, XROAR))

        codes = quantize(linear, np.ones((16, 32), dtype=bool), palette, "floyd-steinberg")

        assert np.all(codes[:, 18:] == 0)

    def should_reject_an_unknown_dither(self, grey) -> None:
        with pytest.raises(GraphicsError, match="Unknown dither"):
            quantize(*grey, dither="atkinson")  # type: ignore[arg-type]

    def should_measure_palette_spread_between_distinct_colours(self) -> None:
        assert palette_spread(np.array([[0.0, 0, 0], [1.0, 0, 0]])) == 1.0


class DescribeConversion:
    def should_pack_an_asymmetric_cg6_sprite_exactly(self) -> None:
        image = picture([[RED, YELLOW, BLUE, GREEN], [GREEN, BLUE, YELLOW, RED]])

        result = convert_image(image, exact(CG6, (4, 2)))

        assert result.data == bytes([0b11011000, 0b00100111])
        assert result.mask == bytes([0, 0])
        assert (result.width, result.height, result.css) == (4, 2, 0)

    def should_pack_an_asymmetric_rg6_sprite_exactly(self) -> None:
        image = picture([[GREEN] + [(0, 0, 0)] * 7, [(0, 0, 0)] * 7 + [GREEN]])

        result = convert_image(image, exact(RG6, (8, 2)))

        assert result.data == bytes([0x80, 0x01])

    def should_choose_the_colour_set_with_less_error(self) -> None:
        cool = picture([[BUFF, CYAN, BUFF, CYAN]])
        warm = picture([[RED, GREEN, RED, GREEN]])

        assert convert_image(cool, exact(CG6, (4, 1), css="auto")).css == 1
        assert convert_image(warm, exact(CG6, (4, 1), css="auto")).css == 0

    def should_share_one_colour_set_across_cells(self) -> None:
        cells = [picture([[BUFF] * 4]), picture([[CYAN] * 4]), picture([[RED] * 4])]

        results = convert_images(cells, exact(CG6, (4, 1), css="auto"))

        assert {r.css for r in results} == {1}

    def should_mask_transparent_pixels_and_clear_their_bits(self) -> None:
        image = picture([[RED, (*RED, 0), RED, (*RED, 127)]])

        result = convert_image(image, exact(CG6, (4, 1)))

        assert result.data == bytes([0b11001100])
        assert result.mask == bytes([0b00110011])

    def should_pad_a_narrow_sprite_with_transparent_pixels(self) -> None:
        image = picture([[RED] * 5])

        result = convert_image(image, exact(CG6, (5, 1), pad=True))

        assert result.width == 8
        assert result.data == bytes([0xFF, 0xC0])
        assert result.mask == bytes([0x00, 0x3F])

    def should_fill_the_screen_when_no_size_is_given(self) -> None:
        image = picture([[GREEN] * 4] * 3)

        result = convert_image(image, ConvertOptions(mode=CG6))

        assert len(result.data) == 6144 and result.data == bytes(6144)
        assert result.codes().shape == (192, 128)

    def should_accept_rgb_without_alpha(self) -> None:
        image = picture([[RED] * 4])[..., :3]

        assert convert_image(image, exact(CG6, (4, 1))).data == b"\xff"

    @pytest.mark.parametrize(
        ("size", "message"),
        [((129, 8), "larger than the CG6 screen"), ((6, 1), "multiple of 4"), ((0, 1), "at least")],
    )
    def should_reject_sizes_the_mode_cannot_hold(self, size, message: str) -> None:
        with pytest.raises(GraphicsError, match=message):
            convert_image(picture([[RED] * 4]), exact(CG6, size))

    def should_reject_an_image_with_no_pixels(self) -> None:
        with pytest.raises(GraphicsError, match="non-empty"):
            convert_image(np.zeros((0, 4, 4), dtype=np.uint8), exact(CG6, (4, 1)))

    def should_convert_only_the_box(self) -> None:
        image = picture([[GREEN] * 4 + [RED] * 4])

        result = convert_image(image, exact(CG6, (4, 1), box=(4, 0, 4, 1)))

        assert result.data == b"\xff"

    @pytest.mark.parametrize("box", [(0, 0, 9, 1), (0, 0, 4, 2), (-1, 0, 1, 1)])
    def should_reject_a_box_outside_the_image(self, box) -> None:
        with pytest.raises(GraphicsError, match="not inside"):
            crop_box(picture([[RED] * 8]), box)

    def should_crop_a_wide_image_to_the_centre(self) -> None:
        image = picture([[GREEN, RED, RED, GREEN]])

        assert crop_to_aspect(image, 2.0)[..., :3].tolist() == [[list(RED), list(RED)]]

    def should_crop_a_tall_image_to_the_middle(self) -> None:
        image = picture([[GREEN], [RED], [GREEN]])

        assert crop_to_aspect(image, 1.0)[..., :3].tolist() == [[list(RED)]]

    def should_fit_the_displayed_shape_before_resizing(self) -> None:
        # Square samples make a CG6 pixel twice as wide as high, so 4x4 pixels show 2:1.
        # The 8x2 source (4:1) keeps its middle 4x2 columns; stretch keeps everything.
        image = picture([[GREEN, GREEN, RED, RED, BLUE, BLUE, GREEN, GREEN]] * 2)
        options = ConvertOptions(mode=CG6, size=(4, 4), display="square", resample="nearest")

        cropped = convert_image(image, options).codes()
        stretched = convert_image(image, options.model_copy(update={"fit": "stretch"})).codes()

        assert cropped.tolist() == [[3, 3, 2, 2]] * 4
        assert stretched.tolist() == [[0, 3, 2, 0]] * 4


class DescribeSheets:
    def should_slice_cells_row_by_row(self) -> None:
        sheet = picture([[RED, RED, GREEN, GREEN], [BLUE, BLUE, YELLOW, YELLOW]])

        cells = slice_cells(sheet, 2, 1)

        assert [[tuple(c[0, 0, :3]) for c in row] for row in cells] == [
            [RED, GREEN],
            [BLUE, YELLOW],
        ]

    @pytest.mark.parametrize("cell", [(3, 1), (2, 3), (0, 1)])
    def should_reject_a_sheet_that_is_not_a_whole_grid(self, cell) -> None:
        with pytest.raises(GraphicsError, match="whole grid"):
            slice_cells(picture([[RED] * 4] * 2), *cell)


class DescribeAssembly:
    @pytest.fixture
    def wide(self):
        return convert_image(picture([[RED] * 128, [GREEN] * 128]), exact(CG6, (128, 2)))

    def should_describe_the_block_and_split_rows_into_short_lines(self, wide) -> None:
        text = assembly_block("title", wide)

        assert (
            "* title: 128x2 CG6 pixels, colour set 0 (CSS=0), 32 bytes per row, 64 bytes." in text
        )
        assert "green, yellow, blue, red" in text
        assert "title_bpr equ 32\ntitle_rows equ 2\ntitle\n" in text
        assert text.count("        fcb $FF,") == 2 and text.count("        fcb $00,") == 2
        assert "_mask" not in text

    def should_add_the_mask_when_asked(self, wide) -> None:
        text = assembly_include([("title", wide)], "art.png", with_mask=True)

        assert text.startswith("* Generated by scripts/graphics.py from art.png.")
        assert "\ntitle_mask\n" in text

    @pytest.mark.parametrize("label", ["1st", "with-dash", "", "a b"])
    def should_reject_labels_lwasm_would_misread(self, label: str) -> None:
        with pytest.raises(GraphicsError, match="must start"):
            check_label(label)

    @pytest.mark.parametrize(
        ("name", "label"), [("hands-cg6", "hands_cg6"), ("1st", "_1st"), ("title", "title")]
    )
    def should_derive_a_valid_label_from_a_file_name(self, name: str, label: str) -> None:
        assert label_from_name(name) == label
        assert check_label(label_from_name(name)) == label


class DescribeCommandLine:
    def should_list_modes_and_palettes(self, capsys) -> None:
        assert main(["modes"]) == 0
        assert main(["palettes"]) == 0

        out = capsys.readouterr().out
        assert "CG2   128x64" in out and "2 x 3" in out
        assert "black (CSS=1): (13, 13, 13)" in out

    def should_write_bytes_include_and_a_preview_of_the_packed_bytes(
        self, tmp_path, capsys
    ) -> None:
        art = save(tmp_path / "art.png", [[RED, YELLOW, BLUE, GREEN], [GREEN, BLUE, YELLOW, RED]])
        out = tmp_path / "out" / "hero"

        code = main(
            ["convert", str(art), "--mode", "cg6", "--size", "4x2", "--fit", "stretch",
             "--resample", "nearest", "--display", "square", "--box", "0,0,4,2", "--out", str(out)]
        )  # fmt: skip

        assert code == 0
        assert (tmp_path / "out" / "hero.bin").read_bytes() == bytes([0xD8, 0x27])
        assert (
            "hero\n        fcb $D8\n        fcb $27\n"
            in (tmp_path / "out" / "hero.asm").read_text()
        )
        preview = np.asarray(Image.open(tmp_path / "out" / "hero.png"))
        assert preview.shape == (4, 16, 3)
        assert [tuple(preview[0, x]) for x in (0, 4, 8, 12)] == [RED, YELLOW, BLUE, GREEN]
        assert not (tmp_path / "out" / "hero-mask.bin").exists()
        assert "CG6 colour set 0" in capsys.readouterr().out

    def should_write_a_mask_and_choose_the_colour_set(self, tmp_path, capsys) -> None:
        art = save(tmp_path / "art.png", [[BUFF, (0, 0, 0, 0), CYAN, BUFF]])

        code = main(
            ["convert", str(art), "--mode", "CG6", "--size", "4x1", "--fit", "stretch",
             "--resample", "nearest", "--auto-css", "--mask", "--label", "ghost",
             "--out", str(tmp_path / "g")]
        )  # fmt: skip

        assert code == 0
        assert (tmp_path / "g-mask.bin").read_bytes() == bytes([0b00110000])
        assert (tmp_path / "g.bin").read_bytes() == bytes([0b00000100])
        assert "ghost_mask" in (tmp_path / "g.asm").read_text()
        assert "colour set 1" in capsys.readouterr().out

    def should_convert_a_sheet_into_labelled_cells(self, tmp_path) -> None:
        art = save(tmp_path / "sheet.png", [[RED, RED, GREEN, GREEN], [BLUE, BLUE, YELLOW, YELLOW]])

        code = main(
            ["sheet", str(art), "--mode", "RG6", "--cell", "2x1", "--size", "8x1",
             "--fit", "stretch", "--resample", "nearest", "--out", str(tmp_path / "s")]
        )  # fmt: skip

        assert code == 0
        text = (tmp_path / "s.asm").read_text()
        assert [f"s_r{r}c{c}" in text for r in (0, 1) for c in (0, 1)] == [True] * 4
        assert len((tmp_path / "s.bin").read_bytes()) == 4
        assert np.asarray(Image.open(tmp_path / "s.png")).shape == (14, 96, 3)

    def should_crop_the_sheet_before_slicing(self, tmp_path) -> None:
        art = save(tmp_path / "sheet.png", [[GREEN, RED, RED, BLUE, BLUE]])

        main(["sheet", str(art), "--mode", "CG6", "--box", "1,0,4,1", "--cell", "2x1",
              "--size", "4x1", "--fit", "stretch", "--resample", "nearest",
              "--out", str(tmp_path / "s")])  # fmt: skip

        assert (tmp_path / "s.bin").read_bytes() == bytes([0xFF, 0xAA])

    def should_render_bytes_in_the_capture_layout(self, tmp_path) -> None:
        data = tmp_path / "screen.bin"
        data.write_bytes(bytes([0x1B]) * 6144)

        code = main(["render", str(data), "--mode", "CG6", "--display", "xroar", "--out",
                     str(tmp_path / "screen.png")])  # fmt: skip

        frame = np.asarray(Image.open(tmp_path / "screen.png"))
        assert code == 0 and frame.shape == (192, 512, 3)
        assert [tuple(frame[191, x]) for x in (0, 4, 8, 12)] == [GREEN, YELLOW, BLUE, RED]

    def should_render_a_sprite_size_at_display_proportions(self, tmp_path) -> None:
        data = tmp_path / "sprite.bin"
        data.write_bytes(b"\x80")

        main(["render", str(data), "--mode", "RG6", "--size", "8x1", "--css", "1",
              "--out", str(tmp_path / "s.png")])  # fmt: skip

        assert np.asarray(Image.open(tmp_path / "s.png")).shape == (7, 48, 3)

    @pytest.mark.parametrize(
        ("argv", "message"),
        [
            (["render", "missing.bin", "--mode", "CG6", "--out", "x.png"], "missing.bin"),
            (["render", "{bin}", "--mode", "HR640", "--out", "x.png"], "GIME"),
            (["render", "{bin}", "--mode", "CG6", "--out", "x.png"], "needs 6144 bytes"),
            (["convert", "{bin}", "--mode", "CG6", "--out", "x"], "error:"),
            (["convert", "{png}", "--mode", "CG6", "--size", "200x8", "--out", "x"], "larger"),
            (["convert", "{png}", "--mode", "CG6", "--label", "9x", "--out", "x"], "must start"),
        ],
    )
    def should_explain_bad_input_and_exit_two(self, tmp_path, capsys, argv, message) -> None:
        (tmp_path / "data.bin").write_bytes(b"\0")
        png = save(tmp_path / "art.png", [[RED]])
        argv = [a.format(bin=tmp_path / "data.bin", png=png) for a in argv]
        argv = [str(tmp_path / a) if a in ("missing.bin", "x", "x.png") else a for a in argv]

        assert main(argv) == 2
        assert message in capsys.readouterr().err

    def should_refuse_to_overwrite_the_input_image(self, tmp_path, capsys) -> None:
        art = save(tmp_path / "art.png", [[RED] * 4])

        code = main(["convert", str(art), "--mode", "CG6", "--out", str(tmp_path / "art")])

        assert code == 2
        assert "would overwrite the input image" in capsys.readouterr().err
        assert not (tmp_path / "art.bin").exists()

    def should_append_suffixes_to_a_dotted_prefix(self, tmp_path) -> None:
        art = save(tmp_path / "art.png", [[RED] * 4])

        main(["convert", str(art), "--mode", "CG6", "--size", "4x1", "--label", "hero",
              "--out", str(tmp_path / "hero.v2")])  # fmt: skip

        assert (tmp_path / "hero.v2.bin").read_bytes() == b"\xff"

    @pytest.mark.parametrize("option", [["--size", "4by2"], ["--box", "1,2,3"]])
    def should_reject_malformed_geometry(self, tmp_path, option) -> None:
        with pytest.raises(SystemExit) as exit_info:
            main(["convert", "a.png", "--mode", "CG6", "--out", "x", *option])

        assert exit_info.value.code == 2

    def should_describe_every_command_in_help(self, capsys) -> None:
        with pytest.raises(SystemExit) as exit_info:
            main(["--help"])

        out = capsys.readouterr().out
        assert exit_info.value.code == 0
        assert all(word in out for word in ("convert", "sheet", "render", "modes", "GIME"))
