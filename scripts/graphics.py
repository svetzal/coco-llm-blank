"""Convert artwork to CoCo graphics bytes, and render those bytes back to pictures.

Run `uv run python scripts/graphics.py --help`. Two families of modes:

- The eight MC6847 VDG full-graphics modes of the CoCo 1/2, which the CoCo 3 also shows (with
  the `xroar-coco3` palette). This module holds them.
- The twenty CoCo 3 GIME graphics modes, whose pixels are palette registers. `gime.py` holds
  them, the 64 colour codes and the palette selection; `raster.py` holds the colour matching,
  reduction and packing that both families share.

Sourced VDG facts (Motorola MC6847/MC6847Y datasheet, 1984, DS9823-R1; resource `mc6847`):

- PDF 18 Table 2: memory size and colour count of each full-graphics mode.
- PDF 20 (page image read; the OCR omits the CG2 paragraph): matrix size and pixel size of
  each mode in half-clocks by scan lines. PDF 21 Figure 22(b) agrees, including CG2.
- PDF 19 Table 3 and PDF 21 Figure 22(a) (page images read): resolution modes use one bit
  per pixel, L7 leftmost; colour modes use one pair of bits per pixel, elements E3..E0 from
  the left over pairs C1 C0, so the leftmost pixel is in bits 7-6. That E3 is bits 7-6
  follows the same left-to-right drawing as L7..L0; XRoar's rendered frame agrees
  (examples/palette-swatches).
- PDF 21 Figure 22(c): colour codes for each colour set (CSS) and the border colours.
- PDF 13: the VDG clock is 3.579545 MHz. PDF 8 Figure 8: a line period is 227.5 clocks.

Palette RGB values are not datasheet facts: see `XROAR`. The `ntsc` pixel aspect is a
deduction with an external assumption: see `raster.half_clock_width`. The GIME sources are in
`gime.py`.
"""

import argparse
import re
import sys
from collections.abc import Sequence
from enum import StrEnum
from pathlib import Path
from typing import Literal

import numpy as np
from gime import (
    GIME_MODES,
    GIME_PALETTES,
    GIME_SOURCE,
    Assignment,
    GimeConversion,
    GimeMode,
    GimeOptions,
    GimePalette,
    assignment_error,
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
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, model_validator
from raster import (
    DISPLAYS,
    DITHERS,
    RESAMPLES,
    RGB,
    ArtOptions,
    Display,
    GraphicsError,
    Prepared,
    as_rgba,
    check_label,
    crop_box,
    fcb_rows,
    half_clock_width,
    label_from_name,
    pack_with_mask,
    prepare,
    preview_scale,
    quantize,
    slice_cells,
    srgb_to_linear,
    total_error,
    unpack,
)


class VdgColour(StrEnum):
    BLACK = "black"
    GREEN = "green"
    YELLOW = "yellow"
    BLUE = "blue"
    RED = "red"
    BUFF = "buff"
    CYAN = "cyan"
    MAGENTA = "magenta"
    ORANGE = "orange"


class Mode(BaseModel):
    """One VDG full-graphics mode. Pixel size is in VDG half-clocks by scan lines."""

    model_config = ConfigDict(frozen=True)

    name: str
    width: int
    height: int
    bits_per_pixel: Literal[1, 2]
    half_clocks: int
    scan_lines: int
    source: str

    @property
    def pixels_per_byte(self) -> int:
        return 8 // self.bits_per_pixel

    @property
    def bytes_per_row(self) -> int:
        return self.width // self.pixels_per_byte

    @property
    def bytes_total(self) -> int:
        return self.bytes_per_row * self.height

    @property
    def colour_count(self) -> int:
        return 2**self.bits_per_pixel


_SOURCE = "MC6847 PDF 18 Table 2, PDF 20, PDF 21 Figure 22"
MODES: dict[str, Mode] = {
    mode.name: mode
    for mode in (
        Mode(name="CG1", width=64, height=64, bits_per_pixel=2, half_clocks=4, scan_lines=3,
             source=_SOURCE),
        Mode(name="RG1", width=128, height=64, bits_per_pixel=1, half_clocks=2, scan_lines=3,
             source=_SOURCE),
        Mode(name="CG2", width=128, height=64, bits_per_pixel=2, half_clocks=2, scan_lines=3,
             source=_SOURCE + " (CG2 read from the PDF 20 page image; not in the OCR)"),
        Mode(name="RG2", width=128, height=96, bits_per_pixel=1, half_clocks=2, scan_lines=2,
             source=_SOURCE),
        Mode(name="CG3", width=128, height=96, bits_per_pixel=2, half_clocks=2, scan_lines=2,
             source=_SOURCE),
        Mode(name="RG3", width=128, height=192, bits_per_pixel=1, half_clocks=2, scan_lines=1,
             source=_SOURCE),
        Mode(name="CG6", width=128, height=192, bits_per_pixel=2, half_clocks=2, scan_lines=1,
             source=_SOURCE),
        Mode(name="RG6", width=256, height=192, bits_per_pixel=1, half_clocks=1, scan_lines=1,
             source=_SOURCE),
    )
}  # fmt: skip

_C = VdgColour
FOUR_COLOUR_SETS = (
    (_C.GREEN, _C.YELLOW, _C.BLUE, _C.RED),
    (_C.BUFF, _C.CYAN, _C.MAGENTA, _C.ORANGE),
)
TWO_COLOUR_SETS = ((_C.BLACK, _C.GREEN), (_C.BLACK, _C.BUFF))
BORDER_COLOURS = (_C.GREEN, _C.BUFF)


def parse_mode(name: str, rows: int = 192) -> Mode | GimeMode:
    """A VDG mode such as CG6, or a GIME mode such as gime-320x16 with its rows."""
    key = name.strip()
    if key.lower() in GIME_MODES:
        return parse_gime_mode(key, rows)
    try:
        return MODES[key.upper()]
    except KeyError:
        raise GraphicsError(
            f"Unknown mode {name!r}. Known MC6847 full-graphics modes: {', '.join(MODES)}. "
            f"Known CoCo 3 GIME modes: {', '.join(GIME_MODES)}."
        ) from None


def colour_set(mode: Mode, css: int) -> tuple[VdgColour, ...]:
    """The colours a mode shows with a colour set, in pixel-code order (code 0 first)."""
    sets = FOUR_COLOUR_SETS if mode.bits_per_pixel == 2 else TWO_COLOUR_SETS
    return sets[_checked_css(css)]


def border_colour(css: int) -> VdgColour:
    return BORDER_COLOURS[_checked_css(css)]


def _checked_css(css: int) -> int:
    if css not in (0, 1):
        raise GraphicsError(f"The colour set select (CSS) is 0 or 1, not {css!r}.")
    return css


# --- Palettes -------------------------------------------------------------------------------


class Palette(BaseModel):
    """RGB approximations of the VDG colours. Black can differ by colour set."""

    model_config = ConfigDict(frozen=True)

    name: str
    description: str
    colours: dict[VdgColour, RGB]
    black: tuple[RGB, RGB]

    @model_validator(mode="after")
    def _names_every_colour(self) -> "Palette":
        missing = set(VdgColour) - {VdgColour.BLACK} - set(self.colours)
        if missing or VdgColour.BLACK in self.colours:
            raise ValueError("colours names every VDG colour except black, which is per CSS")
        return self

    def rgb(self, colour: VdgColour, css: int) -> RGB:
        return self.black[_checked_css(css)] if colour is VdgColour.BLACK else self.colours[colour]


XROAR = Palette(
    name="xroar",
    description=(
        "Measured from XRoar 1.12.1 (with this starter's instrumented patch series; the "
        "palette-swatches rendered check also passes on 1.13) through "
        "scripts/coco.py's rendered-frame capture: S-video input, cross-colour off, active "
        "area only (-tv-input svideo -ccr none), machine cocous, NTSC, VDG 6847. "
        "examples/palette-swatches shows every colour in CG6 and RG6 with both colour sets. "
        "These are one emulator path's values, not measurements of a television or monitor."
    ),
    colours={
        VdgColour.GREEN: (46, 188, 36),
        VdgColour.YELLOW: (255, 255, 151),
        VdgColour.BLUE: (44, 37, 129),
        VdgColour.RED: (131, 26, 55),
        VdgColour.BUFF: (255, 255, 255),
        VdgColour.CYAN: (46, 173, 115),
        VdgColour.MAGENTA: (255, 90, 255),
        VdgColour.ORANGE: (255, 112, 59),
    },
    black=((0, 31, 0), (13, 13, 13)),
)
"""XRoar's rendered colours, measured from captures of examples/palette-swatches.

XRoar 1.12.1, instrumented build (the palette-swatches rendered check also passes on 1.13),
`scripts/coco.py` renderer path: S-video palette without
cross-colour artifacts (`-tv-input svideo -ccr none`), active area only, NTSC `cocous` with a
6847 VDG. Black in the two-colour modes is shown as (0, 31, 0) with CSS=0 and (13, 13, 13)
with CSS=1. They approximate one emulator path, not a real television.
"""

XROAR_COCO3 = Palette(
    name="xroar-coco3",
    description=(
        "Measured from instrumented XRoar 1.13 through scripts/coco.py's rendered-frame "
        "capture (-tv-input svideo -ccr none, active area only), machine coco3, NTSC, "
        "GIME 1986, after Super Extended Color BASIC's reset initialization. On a CoCo 3 each "
        "VDG colour is a palette register (Tepolt PDF 46), and BASIC loads them with "
        "12,24,0B,07,3F,1F,09,26,00,12,00,3F,... (Tepolt PDF 57 step 44). "
        "examples/palette-swatches shows every colour in CG6 and RG6 with both colour sets. "
        "Valid only while those registers hold BASIC's values. These are one emulator path's "
        "values, not measurements of a monitor."
    ),
    colours={
        VdgColour.GREEN: (71, 145, 5),
        VdgColour.YELLOW: (255, 200, 46),
        VdgColour.BLUE: (34, 28, 222),
        VdgColour.RED: (155, 18, 60),
        VdgColour.BUFF: (255, 255, 255),
        VdgColour.CYAN: (25, 161, 33),
        VdgColour.MAGENTA: (106, 17, 181),
        VdgColour.ORANGE: (255, 157, 151),
    },
    black=((20, 20, 20), (20, 20, 20)),
)
"""XRoar's rendered CoCo 3 colours for the VDG-compatible modes, measured from captures of
examples/palette-swatches.

On the CoCo 3 a pixel code selects a palette register, not a fixed VDG colour (Tepolt,
*Assembly Language Programming for the CoCo3*, PDF 46): CG with CSS=0 uses registers 0-3,
CSS=1 registers 4-7, RG with CSS=0 registers 8-9, CSS=1 registers 10-11. Super Extended
Color BASIC's reset loads them with 12,24,0B,07,3F,1F,09,26,00,12,00,3F,00,12,00,26 hex
(Tepolt PDF 57, step 44); XRoar reads back the same values. The CoCo 3 service manual
(PDF 17) lists other, RGB-coded values "for CoCo compatibility"; BASIC does not load those.
So RG green and buff are the same registers' codes as CG green and buff, and RG black is
code 00 for both colour sets. The rendered RGB is XRoar's (S-video input, cross-colour off)
conversion of those codes; a program that writes $FFB0-$FFBB changes it.
"""

PALETTES: dict[str, Palette] = {XROAR.name: XROAR, XROAR_COCO3.name: XROAR_COCO3}


def parse_palette(name: str) -> Palette:
    try:
        return PALETTES[name]
    except KeyError:
        raise GraphicsError(f"Unknown palette {name!r}; known: {', '.join(PALETTES)}.") from None


def palette_rgb(mode: Mode, css: int, palette: Palette) -> np.ndarray:
    """The mode's colours as an (n, 3) uint8 array indexed by pixel code."""
    return np.array([palette.rgb(c, css) for c in colour_set(mode, css)], dtype=np.uint8)


# --- Pixel aspect and rendering ------------------------------------------------------------


def pixel_aspect(mode: Mode, display: Display = "ntsc") -> float:
    """A mode's pixel width divided by its height on the named display."""
    return mode.half_clocks * half_clock_width(display) / mode.scan_lines


def render(
    codes: np.ndarray,
    mode: Mode,
    css: int,
    palette: Palette,
    samples_per_half_clock: int = 1,
    rows_per_scan_line: int = 1,
) -> np.ndarray:
    """An RGB picture of pixel codes: each pixel spans its half-clocks and scan lines.

    With 2 samples per half-clock and 1 row per line, a full screen matches the layout of
    `scripts/coco.py`'s rendered capture (512x192).
    """
    picture = palette_rgb(mode, css, palette)[codes]
    picture = np.repeat(picture, mode.scan_lines * rows_per_scan_line, axis=0)
    return np.repeat(picture, mode.half_clocks * samples_per_half_clock, axis=1)


# --- Conversion -----------------------------------------------------------------------------


class ConvertOptions(ArtOptions):
    """How to turn square-pixel RGBA artwork into one VDG mode's pixel codes."""

    mode: Mode
    css: Literal[0, 1, "auto"] = 0
    palette: Palette = XROAR


class Conversion(BaseModel):
    """Packed picture bytes, the preserve mask (1 keeps what is underneath), and their size."""

    model_config = ConfigDict(frozen=True)

    mode: Mode
    css: int
    width: int
    height: int
    data: bytes
    mask: bytes
    error: float

    @property
    def bytes_per_row(self) -> int:
        return self.width // self.mode.pixels_per_byte

    def codes(self) -> np.ndarray:
        return unpack(self.data, self.width, self.height, self.mode.bits_per_pixel)


def _prepare(rgba: np.ndarray, options: ConvertOptions) -> Prepared:
    aspect = pixel_aspect(options.mode, options.display)
    return prepare(rgba, options, options.mode, aspect)


def _quantized(prepared: Prepared, options: ConvertOptions, css: int) -> tuple[np.ndarray, float]:
    palette_linear = srgb_to_linear(palette_rgb(options.mode, css, options.palette))
    codes = quantize(
        prepared.linear,
        prepared.opaque,
        palette_linear,
        options.dither,
        options.dither_strength,
        options.mosaic,
    )
    return codes, total_error(prepared.linear, prepared.opaque, codes, palette_linear)


def _finish(
    codes: np.ndarray, opaque: np.ndarray, mode: Mode, css: int, error: float
) -> Conversion:
    packed = pack_with_mask(codes, opaque, mode.bits_per_pixel)
    return Conversion(mode=mode, css=css, error=error, **packed.model_dump())


def convert_images(images: Sequence[np.ndarray], options: ConvertOptions) -> list[Conversion]:
    """Convert RGBA arrays with one colour set for all; `auto` picks the lower total error."""
    prepared = [_prepare(as_rgba(image), options) for image in images]
    candidates = (0, 1) if options.css == "auto" else (options.css,)
    attempts = {css: [_quantized(p, options, css) for p in prepared] for css in candidates}
    css = min(candidates, key=lambda c: sum(error for _, error in attempts[c]))
    return [
        _finish(codes, p.opaque, options.mode, css, error)
        for p, (codes, error) in zip(prepared, attempts[css], strict=True)
    ]


def convert_image(rgba: np.ndarray, options: ConvertOptions) -> Conversion:
    return convert_images([rgba], options)[0]


# --- Assembly include -----------------------------------------------------------------------


def assembly_block(label: str, conversion: Conversion, with_mask: bool = False) -> str:
    """An lwasm `fcb` block, one screen row per group of lines, with a descriptive header."""
    mode, css = conversion.mode, conversion.css
    colours = ", ".join(colour_set(mode, css))
    bpr = conversion.bytes_per_row
    size = f"{conversion.width}x{conversion.height} {mode.name} pixels"
    layout = f"{bpr} bytes per row, {bpr * conversion.height} bytes"
    lines = [
        f"* {label}: {size}, colour set {css} (CSS={css}), {layout}.",
        f"* Pixel codes from 0: {colours}. Leftmost pixel in the high bits.",
        f"{label}_bpr equ {bpr}",
        f"{label}_rows equ {conversion.height}",
        *fcb_rows(label, conversion.data, bpr),
    ]
    if with_mask:
        lines += [
            f"* {label}_mask: preserve mask, (screen AND mask) OR {label}; 1 bits keep the screen.",
            *fcb_rows(f"{label}_mask", conversion.mask, bpr),
        ]
    return "\n".join(lines) + "\n"


def assembly_include(
    blocks: Sequence[tuple[str, Conversion | GimeConversion]], source: str, with_mask: bool = False
) -> str:
    header = f"* Generated by scripts/graphics.py from {source}. Regenerate rather than edit.\n"
    return header + "".join(_block(label, c, with_mask) for label, c in blocks)


def _block(label: str, conversion: Conversion | GimeConversion, with_mask: bool) -> str:
    if isinstance(conversion, GimeConversion):
        return gime_assembly_block(label, conversion, with_mask)
    return assembly_block(label, conversion, with_mask)


def sheet_preview(
    conversions: Sequence[Sequence[Conversion]], palette: Palette, display: Display
) -> np.ndarray:
    """One picture of every cell in its grid position, rendered from the packed bytes."""
    samples, rows = preview_scale(display)
    return np.concatenate(
        [
            np.concatenate(
                [render(c.codes(), c.mode, c.css, palette, samples, rows) for c in row], axis=1
            )
            for row in conversions
        ],
        axis=0,
    )


def gime_sheet_preview(
    conversions: Sequence[Sequence[GimeConversion]],
    assignment: Assignment,
    palette: GimePalette,
    display: Display,
) -> np.ndarray:
    """Every GIME cell in its grid position, rendered from the packed register numbers."""
    columns, rows = preview_columns(conversions[0][0].mode, display)
    return np.concatenate(
        [
            np.concatenate(
                [render_gime(c.codes(), c.mode, assignment, palette, columns, rows) for c in row],
                axis=1,
            )
            for row in conversions
        ],
        axis=0,
    )


# --- Command line ---------------------------------------------------------------------------

DESCRIPTION = """\
Convert artwork to CoCo graphics bytes, and render bytes back to pictures.
VDG modes (MC6847: the CoCo 1/2, and the CoCo 3's VDG-compatible modes): CG1 RG1 CG2 RG2 CG3
RG3 CG6 RG6. CoCo 3 GIME modes: gime-<pixels across>x<colours>, such as gime-320x16; run
'modes' for all twenty.

Conversion assumes square-pixel input (for example a PNG of concept art). It crops (optional
--box), fits the region to the shape the target pixels have on the display, resizes, picks
the nearest colour of the mode's colours by CIELAB distance (Delta E 1976, D65), optionally
dithers in linear light or gives each --mosaic block one colour, and packs pixels with the
leftmost pixel in the high bits (bit 7 in two-colour modes, bits 7-6 in four-colour modes,
bits 7-4 in sixteen-colour modes).

Colour sets (CSS): four-colour modes show green, yellow, blue, red (CSS=0) or buff, cyan,
magenta, orange (CSS=1) for codes 0-3. Two-colour modes show black and green (CSS=0) or black
and buff (CSS=1). The border is green or buff. Mode sizes, packing and colour codes are from
the Motorola MC6847 datasheet (PDF pages 18-21). Palette RGB values are XRoar's rendered
colours, measured in examples/palette-swatches; they are not a real TV's colours.

GIME pixels are palette registers 0 to colours-1. Registers $FFB0-$FFBF hold six-bit colour
codes (Tandy CoCo 3 Service Manual PDF 17). The tool chooses codes for an image, or for
several images that share one palette, by CIELAB error against a measured colour model:
gime-composite (default: XRoar's NTSC composite picture, which the starter's checks capture)
or gime-rgb (XRoar's RGB monitor input). Modes are from Tepolt, Assembly Language Programming
for the CoCo3, PDF 41-42 Table 4-10, and the Service Manual PDF 18; the byte layout from
Tepolt PDF 38-39. The colour models are XRoar 1.13.1 measurements, not a monitor's colours.

Commands:
  modes     list the modes: size, bits per pixel, bytes, pixel size and pixel aspect
  palettes  list the palettes and their RGB values
  convert   one image to one screen or sprite
  sheet     a sprite sheet to one labelled block per cell
  palette   one GIME palette that several images share
  render    packed bytes to a PNG

Run '%(prog)s <command> --help' for each command's options and outputs.
"""

CONVERT_EPILOG = """\
Outputs, from --out PREFIX:
  PREFIX.bin       packed bytes, row by row, top row first
  PREFIX.asm       lwasm include: a header, <label>_bpr and <label>_rows equates, then the
                   label and one 'fcb' group per screen row
  PREFIX.png       preview rendered from the packed bytes (not from the resized image), so
                   it shows the packing round trip, at the --display proportions
  PREFIX-mask.bin  with --mask: preserve-mask bytes in the same layout; draw with
                   (screen AND mask) OR picture. Every bit of a transparent pixel is 1.
Transparent pixels (alpha below --alpha-threshold) always get code 0 in the picture bytes.
The chosen colour set and total colour error are printed.

Pixel aspect: 'ntsc' (default) is a deduction, not a sourced fact. It assumes a 4:3 NTSC
picture with about 240 visible lines per field, so a VDG half-clock (1/7.159 MHz) is about
6/7 as wide as a scan line is high. An RG6 pixel is then 0.857 as wide as it is high, a CG6
pixel 1.714. 'square' makes a half-clock as wide as a line is high (a full screen is 256x192
units). Neither is XRoar's capture layout of 2 samples per half-clock: see 'render --help'.

CoCo 3 GIME modes also write:
  PREFIX-palette.asm   lwasm include: <label>_palette_count, then <label>_palette with one
                       'fcb' of colour codes for registers 0 to colours-1, register 0
                       first; a program writes them to $FFB0 and up
  PREFIX-palette.json  the registers the palette sets and their codes; --palette-file
                       reads it back
The tool chooses a code for each register in --registers (default: every register of the
mode) that --lock, --codes and --palette-file do not fix. It makes the sum of CIELAB
distances smallest against the --palette colour model. A locked register outside
--registers stays in the palette, but no pixel uses it. All cells of a sheet share one
palette. A GIME pixel's aspect is a deduction: XRoar draws a GIME line as 640 (full width)
or 512 (short width) samples and a VDG line as 512, so a gime-320x16 or gime-256x16 pixel
has the shape of an RG6 pixel.
"""

DEFAULT_GIME_PALETTE = "gime-composite"
GIME_DEDUCTION = (
    "Samples per pixel and aspect are deductions from XRoar 1.13.1 src/tcc1014/tcc1014.c "
    "(640 or 512 samples for each line)."
)
GIME_ONLY = ("rows", "registers", "lock", "codes", "palette_file")


def _size(text: str) -> tuple[int, int]:
    match = re.fullmatch(r"(\d+)[xX](\d+)", text.strip())
    if not match:
        raise argparse.ArgumentTypeError(f"expected WIDTHxHEIGHT, such as 16x12, not {text!r}")
    return int(match[1]), int(match[2])


def _box(text: str) -> tuple[int, int, int, int]:
    parts = text.split(",")
    if len(parts) != 4 or not all(p.strip().isdigit() for p in parts):
        raise argparse.ArgumentTypeError(f"expected X,Y,WIDTH,HEIGHT in pixels, not {text!r}")
    x, y, width, height = (int(p) for p in parts)
    return x, y, width, height


def _code(text: str) -> int:
    """A colour code in hexadecimal: 3F, $3F or 0x3F."""
    match = re.fullmatch(r"(?:\$|0[xX])?([0-9A-Fa-f]{1,2})", text.strip())
    if not match or int(match[1], 16) > 0x3F:
        raise argparse.ArgumentTypeError(f"expected a colour code $00-$3F in hex, not {text!r}")
    return int(match[1], 16)


def _codes(text: str) -> tuple[int, ...]:
    return tuple(_code(part) for part in text.split(","))


def _lock(text: str) -> tuple[int, int]:
    register, _, code = text.partition("=")
    if not register.strip().isdigit() or not code:
        raise argparse.ArgumentTypeError(f"expected REGISTER=CODE, such as 0=00, not {text!r}")
    return int(register), _code(code)


def _span(text: str) -> tuple[int, int]:
    match = re.fullmatch(r"(\d+)-(\d+)", text.strip())
    if not match:
        raise argparse.ArgumentTypeError(
            f"expected FIRST-LAST registers, such as 8-15, not {text!r}"
        )
    return int(match[1]), int(match[2])


MODE_HELP = "a VDG mode (CG1 RG1 CG2 RG2 CG3 RG3 CG6 RG6) or a GIME mode (gime-320x16 ...)"
PALETTE_HELP = (
    "VDG: the preview palette, xroar (default) or xroar-coco3; GIME: the colour model that "
    "codes are chosen and previewed with, gime-composite (default) or gime-rgb"
)


def _gime_options(parser: argparse.ArgumentParser, rows: bool = True, span: bool = True) -> None:
    group = parser.add_argument_group("CoCo 3 GIME modes")
    if rows:
        group.add_argument(
            "--rows", type=int, choices=(192, 200, 225), help="rows of a full screen (default 192)"
        )
    if span:
        group.add_argument(
            "--registers",
            type=_span,
            metavar="FIRST-LAST",
            help="the registers the pixels may use (default: all of the mode's)",
        )
    group.add_argument(
        "--lock",
        type=_lock,
        action="append",
        metavar="REGISTER=CODE",
        help="fix one register's colour code (hex), such as 0=00; repeat for more",
    )
    group.add_argument(
        "--codes",
        type=_codes,
        metavar="CODE,CODE,...",
        help="fix the codes (hex) of registers 0, 1, 2 ... in order, such as 00,30,12,24",
    )
    group.add_argument(
        "--palette-file",
        type=Path,
        metavar="PREFIX-palette.json",
        help="fix every register a palette file sets; its colour model is the default --palette",
    )


def _conversion_options() -> argparse.ArgumentParser:
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("image", type=Path, help="PNG or other image Pillow can read")
    shared.add_argument("--mode", required=True, help=MODE_HELP)
    shared.add_argument("--out", required=True, type=Path, help="output path without suffix")
    shared.add_argument(
        "--label",
        help="assembly label (default: the --out file name, with other characters turned into _)",
    )
    css = shared.add_mutually_exclusive_group()
    css.add_argument("--css", type=int, choices=(0, 1), help="VDG colour set (default 0)")
    css.add_argument(
        "--auto-css", action="store_true", help="VDG: choose the colour set with less colour error"
    )
    shared.add_argument("--box", type=_box, help="crop the source first: X,Y,WIDTH,HEIGHT")
    shared.add_argument(
        "--fit",
        choices=("crop", "stretch"),
        default="crop",
        help="crop: centre-crop to the target's displayed shape (default); "
        "stretch: use the whole region and distort it",
    )
    shared.add_argument(
        "--resample",
        choices=tuple(RESAMPLES),
        default="box",
        help="nearest for pixel art; box (default, area average), bilinear or lanczos "
        "for illustrations and photos",
    )
    reduce = shared.add_mutually_exclusive_group()
    reduce.add_argument(
        "--dither",
        choices=DITHERS,
        default="none",
        help="none (default); bayer: 4x4 ordered pattern; floyd-steinberg: error diffusion, "
        "left to right on every row. Both are deterministic",
    )
    reduce.add_argument(
        "--mosaic",
        type=_size,
        metavar="WxH",
        help="give each block of WxH target pixels, from the top left, one colour: the "
        "nearest (CIELAB) to the block's mean in linear light. Not with --dither",
    )
    shared.add_argument(
        "--dither-strength",
        type=float,
        default=1.0,
        help="scale of the Bayer threshold or diffused error (default 1.0; untuned)",
    )
    shared.add_argument(
        "--alpha-threshold",
        type=int,
        default=128,
        help="alpha below this is transparent (0-256, default 128; 0 makes every pixel opaque, but fully transparent pixels usually resample to black)",
    )
    shared.add_argument("--mask", action="store_true", help="also write PREFIX-mask.bin")
    shared.add_argument(
        "--pad",
        action="store_true",
        help="allow a width that does not fill whole bytes: pad the right edge with "
        "transparent code-0 pixels",
    )
    shared.add_argument("--display", choices=DISPLAYS, default="ntsc", help="default: ntsc")
    shared.add_argument("--palette", help=PALETTE_HELP)
    _gime_options(shared)
    return shared


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="graphics.py",
        description=DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    commands = parser.add_subparsers(dest="command", required=True, metavar="command")
    commands.add_parser("modes", help="list the VDG and GIME graphics modes")
    commands.add_parser("palettes", help="list the palettes and their RGB values")
    shared = _conversion_options()
    convert = commands.add_parser(
        "convert",
        parents=[shared],
        help="one image to one screen or sprite",
        description="Convert one image to a full screen (default) or a --size sprite.",
        epilog=CONVERT_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    convert.add_argument("--size", type=_size, help="WIDTHxHEIGHT in mode pixels (default: screen)")
    sheet = commands.add_parser(
        "sheet",
        parents=[shared],
        help="a sprite sheet to one labelled block per cell",
        description=(
            "Crop the sheet to --box if given, then slice it into equal --cell rectangles\n"
            "(no margins or gaps). Convert each cell to --size mode pixels, all with one colour\n"
            "set (VDG) or one palette (GIME), and label them <label>_r<row>c<col>, row 0 column\n"
            "0 at the top left. PREFIX.bin and PREFIX-mask.bin hold the cells row by row; the\n"
            "preview shows the grid."
        ),
        epilog=CONVERT_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sheet.add_argument("--cell", type=_size, required=True, help="source cell size, WxH pixels")
    sheet.add_argument("--size", type=_size, required=True, help="each cell in mode pixels, WxH")
    _palette_parser(commands)
    _render_parser(commands)
    return parser


def _palette_parser(commands: argparse._SubParsersAction) -> None:
    palette = commands.add_parser(
        "palette",
        help="one GIME palette that several images share",
        description=(
            "Choose the colour codes of one GIME palette for several images, such as a\n"
            "background and a sprite sheet, and write PREFIX-palette.asm and\n"
            "PREFIX-palette.json. Each image counts the same, whatever its size; an image\n"
            "with more pixels than the mode's screen is first reduced to that many. Then\n"
            "convert each image with --palette-file PREFIX-palette.json."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    palette.add_argument("images", type=Path, nargs="+", help="PNG or other images")
    palette.add_argument("--mode", required=True, help="a GIME mode, such as gime-320x16")
    palette.add_argument("--out", required=True, type=Path, help="output path without suffix")
    palette.add_argument("--label", help="assembly label (default: from the --out file name)")
    palette.add_argument("--palette", help="gime-composite (default) or gime-rgb")
    palette.add_argument(
        "--alpha-threshold", type=int, default=128, help="alpha below this is ignored (default 128)"
    )
    _gime_options(palette, rows=False)


def _render_parser(commands: argparse._SubParsersAction) -> None:
    render_cmd = commands.add_parser(
        "render",
        help="packed bytes to a PNG",
        description=(
            "Render packed bytes (leftmost pixel in the high bits) as a PNG picture. A GIME\n"
            "mode needs the palette: --palette-file, --codes or --lock."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    render_cmd.add_argument("data", type=Path, help="packed bytes, top row first")
    render_cmd.add_argument("--mode", required=True, help=MODE_HELP)
    render_cmd.add_argument("--css", type=int, choices=(0, 1), help="VDG colour set (default 0)")
    render_cmd.add_argument("--size", type=_size, help="WIDTHxHEIGHT pixels (default: screen)")
    render_cmd.add_argument("--out", required=True, type=Path, help="PNG to write")
    render_cmd.add_argument(
        "--display",
        choices=(*DISPLAYS, "xroar"),
        default="ntsc",
        help="ntsc (default) or square proportions; xroar matches scripts/coco.py's capture "
        "layout, 2 samples per half-clock (a GIME line is 640 or 512 samples)",
    )
    render_cmd.add_argument("--palette", help=PALETTE_HELP)
    _gime_options(render_cmd, span=False)


def _refuse_gime_options(args: argparse.Namespace) -> None:
    for name in GIME_ONLY:
        if getattr(args, name, None):
            flag = "--" + name.replace("_", "-")
            raise GraphicsError(f"{flag} applies only to CoCo 3 GIME modes, not {args.mode}.")


def _refuse_vdg_options(args: argparse.Namespace) -> None:
    if args.css is not None or getattr(args, "auto_css", False):
        raise GraphicsError(
            "GIME pixels are palette registers, with no colour set; leave out --css and --auto-css."
        )


def _art_fields(args: argparse.Namespace) -> dict[str, object]:
    return {
        "size": args.size,
        "box": args.box,
        "fit": args.fit,
        "resample": args.resample,
        "dither": args.dither,
        "dither_strength": args.dither_strength,
        "mosaic": args.mosaic,
        "alpha_threshold": args.alpha_threshold,
        "pad": args.pad,
        "display": args.display,
    }


def options_from(args: argparse.Namespace) -> ConvertOptions:
    return ConvertOptions(
        mode=parse_mode(args.mode),
        css="auto" if args.auto_css else (args.css or 0),
        palette=parse_palette(args.palette or XROAR.name),
        **_art_fields(args),
    )


def gime_locks(args: argparse.Namespace) -> tuple[Assignment, str | None]:
    """Registers fixed by --palette-file, --codes and --lock, and the file's colour model."""
    parts: list[Assignment] = []
    named = None
    if args.palette_file:
        assignment, named = parse_palette_file(
            args.palette_file.read_bytes(), str(args.palette_file)
        )
        parts.append(assignment)
    if args.codes:
        parts.append(dict(enumerate(args.codes)))
    parts += [{register: code} for register, code in args.lock or ()]
    return merge_locks(*parts), named


def gime_options_from(args: argparse.Namespace, mode: GimeMode) -> GimeOptions:
    _refuse_vdg_options(args)
    locks, named = gime_locks(args)
    return GimeOptions(
        mode=mode,
        palette=parse_gime_palette(args.palette or named or DEFAULT_GIME_PALETTE),
        registers=args.registers,
        locks=locks,
        **_art_fields(args),
    )


def _screen_mode(args: argparse.Namespace) -> Mode | GimeMode:
    mode = parse_mode(args.mode, args.rows or 192)
    if not isinstance(mode, GimeMode):
        _refuse_gime_options(args)
    return mode


def load_rgba(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        return np.asarray(image.convert("RGBA"))


def save_png(path: Path, picture: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(picture, "RGB").save(path)


PALETTE_SUFFIXES = ("-palette.asm", "-palette.json")


def output_paths(
    prefix: Path, image: Path, with_mask: bool, with_palette: bool = False
) -> list[Path]:
    """PREFIX.bin, .asm, .png, PREFIX-mask.bin with a mask, and the GIME palette files.

    Never the input image.
    """
    names = [
        ".bin",
        ".asm",
        ".png",
        *(["-mask.bin"] if with_mask else []),
        *(PALETTE_SUFFIXES if with_palette else ()),
    ]
    paths = [prefix.with_name(prefix.name + name) for name in names]
    if any(path.resolve() == image.resolve() for path in paths):
        raise GraphicsError(f"--out {prefix} would overwrite the input image {image}.")
    return paths


def _write_outputs(
    args: argparse.Namespace,
    grid: Sequence[Sequence[Conversion | GimeConversion]],
    labels: list[list[str]],
    preview: np.ndarray,
    palette_files: tuple[str, str] | None = None,
) -> list[Path]:
    paths = output_paths(args.out, args.image, args.mask, palette_files is not None)
    paths[0].parent.mkdir(parents=True, exist_ok=True)
    cells = [(label, c) for row_labels, row in zip(labels, grid, strict=True)
             for label, c in zip(row_labels, row, strict=True)]  # fmt: skip
    paths[0].write_bytes(b"".join(c.data for _, c in cells))
    paths[1].write_text(assembly_include(cells, args.image.name, args.mask))
    save_png(paths[2], preview)
    if args.mask:
        paths[3].write_bytes(b"".join(c.mask for _, c in cells))
    if palette_files:
        paths[-2].write_text(palette_files[0])
        paths[-1].write_text(palette_files[1])
    return paths


def _palette_files(label: str, assignment: Assignment, options: GimeOptions) -> tuple[str, str]:
    return (
        palette_assembly(f"{label}_palette", assignment, options.palette, options.mode),
        palette_json(assignment, options.palette, options.mode),
    )


def run_convert(args: argparse.Namespace) -> list[str]:
    mode = _screen_mode(args)
    label = check_label(args.label or label_from_name(args.out.name))
    output_paths(args.out, args.image, args.mask, isinstance(mode, GimeMode))
    if isinstance(mode, GimeMode):
        return _gime_cells(args, mode, label, [[load_rgba(args.image)]])
    options = options_from(args)
    conversion = convert_image(load_rgba(args.image), options)
    preview = sheet_preview([[conversion]], options.palette, options.display)
    paths = _write_outputs(args, [[conversion]], [[label]], preview)
    return _report(conversion, conversion.error, paths)


def run_sheet(args: argparse.Namespace) -> list[str]:
    mode = _screen_mode(args)
    label = check_label(args.label or label_from_name(args.out.name))
    output_paths(args.out, args.image, args.mask, isinstance(mode, GimeMode))
    rows = slice_cells(crop_box(load_rgba(args.image), args.box), *args.cell)
    args.box = None
    labels = [[f"{label}_r{r}c{c}" for c in range(len(rows[0]))] for r in range(len(rows))]
    if isinstance(mode, GimeMode):
        lines = _gime_cells(args, mode, label, rows, labels)
        return [f"{sum(map(len, rows))} cells in {len(rows)} rows of {len(rows[0])}", *lines]
    options = options_from(args)
    flat = convert_images([cell for row in rows for cell in row], options)
    width = len(rows[0])
    grid = [flat[r * width : (r + 1) * width] for r in range(len(rows))]
    preview = sheet_preview(grid, options.palette, options.display)
    paths = _write_outputs(args, grid, labels, preview)
    error = sum(c.error for c in flat)
    return [f"{len(flat)} cells in {len(rows)} rows of {width}", *_report(flat[0], error, paths)]


def _gime_cells(
    args: argparse.Namespace,
    mode: GimeMode,
    label: str,
    rows: list[list[np.ndarray]],
    labels: list[list[str]] | None = None,
) -> list[str]:
    """Convert a grid of images with one shared palette; write every output."""
    options = gime_options_from(args, mode)
    result = convert_gime_images([cell for row in rows for cell in row], options)
    width = len(rows[0])
    flat = result.conversions
    grid = [flat[r * width : (r + 1) * width] for r in range(len(rows))]
    preview = gime_sheet_preview(grid, result.assignment, options.palette, options.display)
    files = _palette_files(label, result.assignment, options)
    paths = _write_outputs(args, grid, labels or [[label]], preview, files)
    return [
        _assignment_line(mode, options.palette, result.assignment),
        f"colour error (sum of CIELAB distances): {sum(c.error for c in flat):.1f}",
        *(str(path) for path in paths),
    ]


def _assignment_line(mode: GimeMode, palette: GimePalette, assignment: Assignment) -> str:
    codes = " ".join(f"{register}=${code:02X}" for register, code in assignment.items())
    return f"{mode.name}, {mode.rows} rows, {palette.name} colours; registers {codes}"


def _report(conversion: Conversion, error: float, paths: list[Path]) -> list[str]:
    mode = conversion.mode
    return [
        f"{mode.name} colour set {conversion.css}: {', '.join(colour_set(mode, conversion.css))}",
        f"colour error (sum of CIELAB distances): {error:.1f}",
        *(str(path) for path in paths),
    ]


def run_palette(args: argparse.Namespace) -> list[str]:
    mode = parse_mode(args.mode)
    if not isinstance(mode, GimeMode):
        raise GraphicsError(
            f"palette chooses CoCo 3 GIME colour codes; {mode.name} is a VDG mode, whose colour "
            "sets are fixed."
        )
    label = check_label(args.label or label_from_name(args.out.name))
    locks, named = gime_locks(args)
    palette = parse_gime_palette(args.palette or named or DEFAULT_GIME_PALETTE)
    screen = mode.width * mode.rows
    grids = [palette_grid(load_rgba(path), screen, args.alpha_threshold) for path in args.images]
    colours, weights = colour_samples(grids, equal_weight=True)
    assignment = select_palette(colours, weights, palette, mode.colour_count, args.registers, locks)
    usable = [assignment[r] for r in register_range(args.registers, mode.colour_count)]
    error = assignment_error(colours, weights, usable, palette) / len(grids)
    paths = [args.out.with_name(args.out.name + suffix) for suffix in PALETTE_SUFFIXES]
    paths[0].parent.mkdir(parents=True, exist_ok=True)
    paths[0].write_text(palette_assembly(f"{label}_palette", assignment, palette, mode))
    paths[1].write_text(palette_json(assignment, palette, mode))
    return [
        _assignment_line(mode, palette, assignment),
        f"mean colour error per pixel, averaged over the images (CIELAB distance): {error:.2f}",
        *(str(path) for path in paths),
    ]


def run_render(args: argparse.Namespace) -> list[str]:
    mode = _screen_mode(args)
    if isinstance(mode, GimeMode):
        return _render_gime(args, mode)
    width, height = args.size or (mode.width, mode.height)
    codes = unpack(args.data.read_bytes(), width, height, mode.bits_per_pixel)
    scale = (2, 1) if args.display == "xroar" else preview_scale(args.display)
    palette = parse_palette(args.palette or XROAR.name)
    save_png(args.out, render(codes, mode, args.css or 0, palette, *scale))
    return [str(args.out)]


def _render_gime(args: argparse.Namespace, mode: GimeMode) -> list[str]:
    _refuse_vdg_options(args)
    locks, named = gime_locks(args)
    if not locks:
        raise GraphicsError(
            "A GIME render needs the palette's codes: give --palette-file, --codes or --lock."
        )
    assignment = check_assignment(locks, mode.colour_count)
    palette = parse_gime_palette(args.palette or named or DEFAULT_GIME_PALETTE)
    width, height = args.size or (mode.width, mode.rows)
    codes = unpack(args.data.read_bytes(), width, height, mode.bits_per_pixel)
    columns, rows = preview_columns(mode, args.display)
    save_png(args.out, render_gime(codes, mode, assignment, palette, columns, rows))
    return [str(args.out)]


def run_modes(_: argparse.Namespace) -> list[str]:
    lines = [
        "mode  pixels   bits  bytes/row  bytes  pixel(half-clocks x lines)  aspect ntsc/square"
    ]
    for mode in MODES.values():
        lines.append(
            f"{mode.name:<5} {mode.width:>3}x{mode.height:<4} {mode.bits_per_pixel:>4}  "
            f"{mode.bytes_per_row:>9}  {mode.bytes_total:>5}  {mode.half_clocks:>13} x {mode.scan_lines}"
            f"{'':12}{pixel_aspect(mode, 'ntsc'):.3f}/{pixel_aspect(mode, 'square'):.3f}"
        )
    lines += [f"Source: {_SOURCE}; CG2 from the PDF 20 page image.", ""]
    lines.append(
        "GIME mode    pixels   bits  colours  HRES  CRES  bytes/row  bytes  width  "
        "samples/pixel  aspect ntsc/square"
    )
    for mode in GIME_MODES.values():
        width = "full" if mode.full else "short"
        lines.append(
            f"{mode.name:<12} {mode.width:>3}x{mode.rows:<4} {mode.bits_per_pixel:>4}  "
            f"{mode.colour_count:>7}   {mode.hres:03b}    {mode.cres:02b}  {mode.bytes_per_row:>9}  "
            f"{mode.bytes_total:>5}  {width:<5}  {mode.samples_per_pixel:>13}  "
            f"{gime_pixel_aspect(mode, 'ntsc'):.3f}/{gime_pixel_aspect(mode, 'square'):.3f}"
        )
    return [
        *lines,
        "Rows: 192 (shown), 200 or 225 with --rows. One scan line for each row of pixels.",
        f"Source: {GIME_SOURCE}. {GIME_DEDUCTION}",
    ]


def run_palettes(_: argparse.Namespace) -> list[str]:
    lines = []
    for palette in PALETTES.values():
        lines += [f"{palette.name}: {palette.description}"]
        lines += [f"  black (CSS={css}): {rgb}" for css, rgb in enumerate(palette.black)]
        lines += [f"  {colour.value}: {rgb}" for colour, rgb in palette.colours.items()]
    for gime_palette in GIME_PALETTES.values():
        lines += [f"{gime_palette.name}: {gime_palette.description}"]
        lines += [f"  ${code:02X}: {rgb}" for code, rgb in enumerate(gime_palette.colours)]
    return lines


COMMANDS = {
    "modes": run_modes,
    "palettes": run_palettes,
    "convert": run_convert,
    "sheet": run_sheet,
    "palette": run_palette,
    "render": run_render,
}


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        lines = COMMANDS[args.command](args)
    except (GraphicsError, OSError, UnidentifiedImageError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
