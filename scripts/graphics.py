"""Convert artwork to MC6847 VDG full-graphics bytes, and render those bytes back to pictures.

Run `uv run python scripts/graphics.py --help`. CoCo 1/2 only: the eight VDG full-graphics
modes. CoCo 3 GIME modes are out of scope.

Sourced facts (Motorola MC6847/MC6847Y datasheet, 1984, DS9823-R1; resource `mc6847`):

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
deduction with an external assumption: see `half_clock_width`.
"""

import argparse
import re
import sys
from collections.abc import Sequence
from enum import StrEnum
from fractions import Fraction
from pathlib import Path
from typing import Annotated, Literal

import numpy as np
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, Field, model_validator


class GraphicsError(ValueError):
    """An input that cannot be converted, packed or rendered as asked."""


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


def parse_mode(name: str) -> Mode:
    try:
        return MODES[name.strip().upper()]
    except KeyError:
        raise GraphicsError(
            f"Unknown mode {name!r}. Known MC6847 full-graphics modes: {', '.join(MODES)}. "
            "CoCo 3 GIME modes are not supported by this tool."
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

Channel = Annotated[int, Field(ge=0, le=255)]
RGB = tuple[Channel, Channel, Channel]


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
        "Measured from XRoar 1.12.1 (with this starter's instrumented patch series) through "
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

XRoar 1.12.1, instrumented build, `scripts/coco.py` renderer path: S-video palette without
cross-colour artifacts (`-tv-input svideo -ccr none`), active area only, NTSC `cocous` with a
6847 VDG. Black in the two-colour modes is shown as (0, 31, 0) with CSS=0 and (13, 13, 13)
with CSS=1. They approximate one emulator path, not a real television.
"""

PALETTES: dict[str, Palette] = {XROAR.name: XROAR}


def parse_palette(name: str) -> Palette:
    try:
        return PALETTES[name]
    except KeyError:
        raise GraphicsError(f"Unknown palette {name!r}; known: {', '.join(PALETTES)}.") from None


def palette_rgb(mode: Mode, css: int, palette: Palette) -> np.ndarray:
    """The mode's colours as an (n, 3) uint8 array indexed by pixel code."""
    return np.array([palette.rgb(c, css) for c in colour_set(mode, css)], dtype=np.uint8)


# --- Pixel aspect ---------------------------------------------------------------------------

Display = Literal["ntsc", "square"]
DISPLAYS: tuple[Display, ...] = ("ntsc", "square")
VDG_CLOCK_MHZ = 3.579545
HALF_CLOCK_MHZ = 2 * VDG_CLOCK_MHZ
NTSC_SQUARE_PIXEL_MHZ = 135 / 11 / 2


def half_clock_width(display: Display) -> float:
    """Width of one VDG half-clock, in units of one scan line's height.

    `ntsc` is a deduction, not a sourced fact: it assumes a 4:3 NTSC picture with about 240
    visible lines per non-interlaced field, whose square-pixel sampling rate is half the
    BT.601 square-pixel rate for 480 lines (135/11 MHz / 2, about 6.136 MHz). A half-clock
    lasts 1/7.159 us, so it is 6.136/7.159 (about 6/7) of a line height wide.
    `square` treats one half-clock as one line high, the proportions of a sample grid.
    """
    if display == "ntsc":
        return NTSC_SQUARE_PIXEL_MHZ / HALF_CLOCK_MHZ
    if display == "square":
        return 1.0
    raise GraphicsError(f"Unknown display {display!r}; known: {', '.join(DISPLAYS)}.")


def pixel_aspect(mode: Mode, display: Display = "ntsc") -> float:
    """A mode's pixel width divided by its height on the named display."""
    return mode.half_clocks * half_clock_width(display) / mode.scan_lines


def preview_scale(display: Display) -> tuple[int, int]:
    """Preview samples per half-clock and rows per scan line, in the display's proportion."""
    ratio = Fraction(half_clock_width(display)).limit_denominator(8)
    factor = 2 if ratio == 1 else 1
    return ratio.numerator * factor, ratio.denominator * factor


# --- Packing and rendering ------------------------------------------------------------------


def pack(codes: np.ndarray, bits_per_pixel: int) -> bytes:
    """Pack rows of pixel codes, leftmost pixel in the most significant bits of each byte."""
    height, width = codes.shape
    per_byte = 8 // bits_per_pixel
    if width % per_byte:
        raise GraphicsError(f"Width {width} is not a whole number of {per_byte}-pixel bytes.")
    if codes.size and int(codes.max()) >= 2**bits_per_pixel:
        raise GraphicsError(f"A pixel code does not fit in {bits_per_pixel} bits.")
    shifts = np.arange(per_byte - 1, -1, -1, dtype=np.uint16) * bits_per_pixel
    grouped = codes.astype(np.uint16).reshape(height, width // per_byte, per_byte)
    return (grouped << shifts).sum(axis=2).astype(np.uint8).tobytes()


def unpack(data: bytes, width: int, height: int, bits_per_pixel: int) -> np.ndarray:
    """Pixel codes, one row per screen row, from bytes packed as `pack` packs them."""
    per_byte = 8 // bits_per_pixel
    if width <= 0 or height <= 0 or width % per_byte:
        raise GraphicsError(f"{width}x{height} is not a whole number of {per_byte}-pixel bytes.")
    expected = width // per_byte * height
    if len(data) != expected:
        raise GraphicsError(f"{width}x{height} needs {expected} bytes, not {len(data)}.")
    raw = np.frombuffer(data, dtype=np.uint8).reshape(height, width // per_byte, 1)
    shifts = np.arange(per_byte - 1, -1, -1, dtype=np.uint8) * bits_per_pixel
    return ((raw >> shifts) & (2**bits_per_pixel - 1)).reshape(height, width)


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


# --- Colour science -------------------------------------------------------------------------

_SRGB_TO_XYZ = np.array(
    [
        [0.4124564, 0.3575761, 0.1804375],
        [0.2126729, 0.7151522, 0.0721750],
        [0.0193339, 0.1191920, 0.9503041],
    ]
)
_D65_WHITE = np.array([0.95047, 1.0, 1.08883])
_LAB_EDGE = 6 / 29


def srgb_to_linear(rgb: np.ndarray) -> np.ndarray:
    """sRGB 0-255 values to linear light 0-1."""
    c = np.asarray(rgb, dtype=np.float64) / 255
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def linear_to_lab(linear: np.ndarray) -> np.ndarray:
    """Linear-light sRGB (last axis RGB) to CIELAB, D65 white."""
    xyz = np.asarray(linear, dtype=np.float64) @ _SRGB_TO_XYZ.T / _D65_WHITE
    f = np.where(xyz > _LAB_EDGE**3, np.cbrt(xyz), xyz / (3 * _LAB_EDGE**2) + 4 / 29)
    fx, fy, fz = f[..., 0], f[..., 1], f[..., 2]
    return np.stack((116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)), axis=-1)


def nearest_codes(linear: np.ndarray, palette_linear: np.ndarray) -> np.ndarray:
    """Index of the palette colour nearest each pixel by CIELAB distance (Delta E 1976)."""
    lab = linear_to_lab(np.clip(linear, 0, 1))[..., None, :]
    distances = ((lab - linear_to_lab(palette_linear)) ** 2).sum(axis=-1)
    return distances.argmin(axis=-1).astype(np.uint8)


Dither = Literal["none", "bayer", "floyd-steinberg"]
DITHERS: tuple[Dither, ...] = ("none", "bayer", "floyd-steinberg")
BAYER_4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]])
_DIFFUSION = ((0, 1, 7 / 16), (1, -1, 3 / 16), (1, 0, 5 / 16), (1, 1, 1 / 16))


def palette_spread(palette_linear: np.ndarray) -> float:
    """Mean linear-light distance from each palette colour to its nearest other colour."""
    gaps = np.linalg.norm(palette_linear[:, None] - palette_linear[None], axis=-1)
    np.fill_diagonal(gaps, np.inf)
    return float(gaps.min(axis=1).mean())


def quantize(
    linear: np.ndarray,
    opaque: np.ndarray,
    palette_linear: np.ndarray,
    dither: Dither = "none",
    strength: float = 1.0,
) -> np.ndarray:
    """Pixel codes for linear-light pixels; transparent pixels get code 0.

    Nearest colour is by CIELAB distance. `bayer` adds a 4x4 ordered threshold to all three
    channels, scaled by `strength` times the palette's spread (a heuristic, not tuned).
    `floyd-steinberg` diffuses `strength` times each pixel's linear-light error, left to
    right on every row; the error is taken after clipping to 0-1, so colours the set cannot
    reach do not pile up error. Both are deterministic.
    """
    if dither == "floyd-steinberg":
        codes = _diffuse(linear, opaque, palette_linear, strength)
    elif dither == "bayer":
        height, width = opaque.shape
        threshold = (BAYER_4[np.arange(height)[:, None] % 4, np.arange(width) % 4] + 0.5) / 16
        offset = (threshold - 0.5) * strength * palette_spread(palette_linear)
        codes = nearest_codes(linear + offset[..., None], palette_linear)
    elif dither == "none":
        codes = nearest_codes(linear, palette_linear)
    else:
        raise GraphicsError(f"Unknown dither {dither!r}; known: {', '.join(DITHERS)}.")
    return np.where(opaque, codes, 0).astype(np.uint8)


def _diffuse(
    linear: np.ndarray, opaque: np.ndarray, palette_linear: np.ndarray, strength: float
) -> np.ndarray:
    work = np.array(linear, dtype=np.float64)
    palette_lab = linear_to_lab(palette_linear)
    codes = np.zeros(opaque.shape, dtype=np.uint8)
    for y, x in zip(*np.nonzero(opaque), strict=True):
        pixel = np.clip(work[y, x], 0, 1)
        code = int(((palette_lab - linear_to_lab(pixel)) ** 2).sum(axis=1).argmin())
        codes[y, x] = code
        _spread_error(work, y, x, (pixel - palette_linear[code]) * strength)
    return codes


def _spread_error(work: np.ndarray, y: int, x: int, error: np.ndarray) -> None:
    height, width, _ = work.shape
    for dy, dx, weight in _DIFFUSION:
        if y + dy < height and 0 <= x + dx < width:
            work[y + dy, x + dx] += error * weight


def total_error(
    linear: np.ndarray, opaque: np.ndarray, codes: np.ndarray, palette_linear: np.ndarray
) -> float:
    """Sum of CIELAB distances between opaque pixels and their chosen colours."""
    chosen = linear_to_lab(palette_linear)[codes]
    gaps = np.linalg.norm(linear_to_lab(np.clip(linear, 0, 1)) - chosen, axis=-1)
    return float(gaps[opaque].sum())


# --- Conversion -----------------------------------------------------------------------------

Resample = Literal["nearest", "box", "bilinear", "lanczos"]
RESAMPLES: dict[str, Image.Resampling] = {
    "nearest": Image.Resampling.NEAREST,
    "box": Image.Resampling.BOX,
    "bilinear": Image.Resampling.BILINEAR,
    "lanczos": Image.Resampling.LANCZOS,
}
Fit = Literal["crop", "stretch"]


class ConvertOptions(BaseModel):
    """How to turn square-pixel RGBA artwork into one mode's pixel codes."""

    model_config = ConfigDict(frozen=True)

    mode: Mode
    css: Literal[0, 1, "auto"] = 0
    size: tuple[int, int] | None = None
    box: tuple[int, int, int, int] | None = None
    fit: Fit = "crop"
    resample: Resample = "box"
    dither: Dither = "none"
    dither_strength: float = Field(default=1.0, ge=0)
    alpha_threshold: int = Field(default=128, ge=0, le=256)
    pad: bool = False
    display: Display = "ntsc"
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


class _Prepared(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    linear: np.ndarray
    opaque: np.ndarray


def target_size(options: ConvertOptions) -> tuple[int, int]:
    """The requested pixel grid; the whole screen when no size is given."""
    mode = options.mode
    width, height = options.size or (mode.width, mode.height)
    if width < 1 or height < 1:
        raise GraphicsError(f"Size {width}x{height} must be at least 1x1 pixels.")
    if width > mode.width or height > mode.height:
        raise GraphicsError(
            f"Size {width}x{height} is larger than the {mode.name} screen "
            f"({mode.width}x{mode.height})."
        )
    if width % mode.pixels_per_byte and not options.pad:
        raise GraphicsError(
            f"Width {width} is not a multiple of {mode.pixels_per_byte} pixels per byte in "
            f"{mode.name}. Choose another width, or pad the right edge with transparent pixels."
        )
    return width, height


def crop_box(rgba: np.ndarray, box: tuple[int, int, int, int] | None) -> np.ndarray:
    if box is None:
        return rgba
    x, y, width, height = box
    if x < 0 or y < 0 or width < 1 or height < 1 or x + width > rgba.shape[1]:
        raise GraphicsError(f"Box {box} is not inside the {rgba.shape[1]}x{rgba.shape[0]} image.")
    if y + height > rgba.shape[0]:
        raise GraphicsError(f"Box {box} is not inside the {rgba.shape[1]}x{rgba.shape[0]} image.")
    return rgba[y : y + height, x : x + width]


def crop_to_aspect(rgba: np.ndarray, aspect: float) -> np.ndarray:
    """The centred largest region of the image whose width/height is `aspect`."""
    height, width = rgba.shape[:2]
    if width / height > aspect:
        keep = max(1, round(height * aspect))
        left = (width - keep) // 2
        return rgba[:, left : left + keep]
    keep = max(1, round(width / aspect))
    top = (height - keep) // 2
    return rgba[top : top + keep]


def _prepare(rgba: np.ndarray, options: ConvertOptions) -> _Prepared:
    width, height = target_size(options)
    region = crop_box(rgba, options.box)
    if options.fit == "crop":
        region = crop_to_aspect(
            region, width * pixel_aspect(options.mode, options.display) / height
        )
    image = Image.fromarray(np.ascontiguousarray(region), "RGBA")
    resized = np.asarray(image.resize((width, height), RESAMPLES[options.resample]))
    return _Prepared(
        linear=srgb_to_linear(resized[..., :3]), opaque=resized[..., 3] >= options.alpha_threshold
    )


def _quantized(prepared: _Prepared, options: ConvertOptions, css: int) -> tuple[np.ndarray, float]:
    palette_linear = srgb_to_linear(palette_rgb(options.mode, css, options.palette))
    codes = quantize(
        prepared.linear, prepared.opaque, palette_linear, options.dither, options.dither_strength
    )
    return codes, total_error(prepared.linear, prepared.opaque, codes, palette_linear)


def _finish(
    codes: np.ndarray, opaque: np.ndarray, mode: Mode, css: int, error: float
) -> Conversion:
    pad = -codes.shape[1] % mode.pixels_per_byte
    codes = np.pad(codes, ((0, 0), (0, pad)))
    opaque = np.pad(opaque, ((0, 0), (0, pad)))
    keep = np.where(opaque, 0, mode.colour_count - 1).astype(np.uint8)
    return Conversion(
        mode=mode,
        css=css,
        width=codes.shape[1],
        height=codes.shape[0],
        data=pack(codes, mode.bits_per_pixel),
        mask=pack(keep, mode.bits_per_pixel),
        error=error,
    )


def convert_images(images: Sequence[np.ndarray], options: ConvertOptions) -> list[Conversion]:
    """Convert RGBA arrays with one colour set for all; `auto` picks the lower total error."""
    prepared = [_prepare(_as_rgba(image), options) for image in images]
    candidates = (0, 1) if options.css == "auto" else (options.css,)
    attempts = {css: [_quantized(p, options, css) for p in prepared] for css in candidates}
    css = min(candidates, key=lambda c: sum(error for _, error in attempts[c]))
    return [
        _finish(codes, p.opaque, options.mode, css, error)
        for p, (codes, error) in zip(prepared, attempts[css], strict=True)
    ]


def convert_image(rgba: np.ndarray, options: ConvertOptions) -> Conversion:
    return convert_images([rgba], options)[0]


def _as_rgba(image: np.ndarray) -> np.ndarray:
    if image.ndim != 3 or image.shape[2] not in (3, 4) or 0 in image.shape[:2]:
        raise GraphicsError("Expected a non-empty RGB or RGBA image.")
    if image.shape[2] == 3:
        image = np.dstack((image, np.full(image.shape[:2], 255, dtype=np.uint8)))
    return image.astype(np.uint8)


def slice_cells(rgba: np.ndarray, cell_width: int, cell_height: int) -> list[list[np.ndarray]]:
    """Rows of equal cells from a sprite sheet, top-left first, with no gaps or margins."""
    height, width = rgba.shape[:2]
    if cell_width < 1 or cell_height < 1 or width % cell_width or height % cell_height:
        raise GraphicsError(
            f"The {width}x{height} sheet is not a whole grid of {cell_width}x{cell_height} cells."
        )
    return [
        [rgba[y : y + cell_height, x : x + cell_width] for x in range(0, width, cell_width)]
        for y in range(0, height, cell_height)
    ]


# --- Assembly include -----------------------------------------------------------------------

LABEL = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
BYTES_PER_LINE = 16


def check_label(label: str) -> str:
    if not LABEL.match(label):
        raise GraphicsError(
            f"Label {label!r} must start with a letter or underscore and hold only letters, "
            "digits and underscores."
        )
    return label


def label_from_name(name: str) -> str:
    """Turn a file name such as ``hands-cg6`` into a label lwasm accepts."""
    label = re.sub(r"\W", "_", name)
    return label if LABEL.match(label) else f"_{label}"


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
        *_fcb_rows(label, conversion.data, bpr),
    ]
    if with_mask:
        lines += [
            f"* {label}_mask: preserve mask, (screen AND mask) OR {label}; 1 bits keep the screen.",
            *_fcb_rows(f"{label}_mask", conversion.mask, bpr),
        ]
    return "\n".join(lines) + "\n"


def _fcb_rows(label: str, data: bytes, bytes_per_row: int) -> list[str]:
    lines = [label]
    for start in range(0, len(data), bytes_per_row):
        row = data[start : start + bytes_per_row]
        for part in range(0, len(row), BYTES_PER_LINE):
            values = ",".join(f"${b:02X}" for b in row[part : part + BYTES_PER_LINE])
            lines.append(f"        fcb {values}")
    return lines


def assembly_include(
    blocks: Sequence[tuple[str, Conversion]], source: str, with_mask: bool = False
) -> str:
    header = f"* Generated by scripts/graphics.py from {source}. Regenerate rather than edit.\n"
    return header + "".join(assembly_block(label, c, with_mask) for label, c in blocks)


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


# --- Command line ---------------------------------------------------------------------------

DESCRIPTION = """\
Convert artwork to MC6847 VDG full-graphics bytes for the CoCo 1/2, and render bytes back to
pictures. Modes: CG1 RG1 CG2 RG2 CG3 RG3 CG6 RG6. CoCo 3 GIME modes are not supported.

Conversion assumes square-pixel input (for example a PNG of concept art). It crops (optional
--box), fits the region to the shape the target pixels have on the display, resizes, picks
the nearest colour of the mode's colour set by CIELAB distance (Delta E 1976, D65), optionally
dithers in linear light, and packs pixels with the leftmost pixel in the high bits (bit 7 in
two-colour modes, bits 7-6 in four-colour modes).

Colour sets (CSS): four-colour modes show green, yellow, blue, red (CSS=0) or buff, cyan,
magenta, orange (CSS=1) for codes 0-3. Two-colour modes show black and green (CSS=0) or black
and buff (CSS=1). The border is green or buff. Mode sizes, packing and colour codes are from
the Motorola MC6847 datasheet (PDF pages 18-21). Palette RGB values are XRoar's rendered
colours, measured in examples/palette-swatches; they are not a real TV's colours.

Commands:
  modes     list the modes: size, bits per pixel, bytes, pixel size and pixel aspect
  palettes  list the palettes and their RGB values
  convert   one image to one screen or sprite
  sheet     a sprite sheet to one labelled block per cell
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
"""


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


def _conversion_options() -> argparse.ArgumentParser:
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("image", type=Path, help="PNG or other image Pillow can read")
    shared.add_argument("--mode", required=True, help="CG1 RG1 CG2 RG2 CG3 RG3 CG6 or RG6")
    shared.add_argument("--out", required=True, type=Path, help="output path without suffix")
    shared.add_argument(
        "--label",
        help="assembly label (default: the --out file name, with other characters turned into _)",
    )
    css = shared.add_mutually_exclusive_group()
    css.add_argument("--css", type=int, choices=(0, 1), default=0, help="colour set (default 0)")
    css.add_argument(
        "--auto-css", action="store_true", help="choose the colour set with less colour error"
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
    shared.add_argument(
        "--dither",
        choices=DITHERS,
        default="none",
        help="none (default); bayer: 4x4 ordered pattern; floyd-steinberg: error diffusion, "
        "left to right on every row. Both are deterministic",
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
    shared.add_argument("--palette", default="xroar", help="preview palette (default: xroar)")
    return shared


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="graphics.py",
        description=DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    commands = parser.add_subparsers(dest="command", required=True, metavar="command")
    commands.add_parser("modes", help="list the VDG full-graphics modes")
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
            "set, and label them <label>_r<row>c<col>, row 0 column 0 at the top left.\n"
            "PREFIX.bin and PREFIX-mask.bin hold the cells row by row; the preview shows the grid."
        ),
        epilog=CONVERT_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sheet.add_argument("--cell", type=_size, required=True, help="source cell size, WxH pixels")
    sheet.add_argument("--size", type=_size, required=True, help="each cell in mode pixels, WxH")
    render_cmd = commands.add_parser(
        "render",
        help="packed bytes to a PNG",
        description="Render packed bytes (leftmost pixel in the high bits) as a PNG picture.",
    )
    render_cmd.add_argument("data", type=Path, help="packed bytes, top row first")
    render_cmd.add_argument("--mode", required=True, help="CG1 RG1 CG2 RG2 CG3 RG3 CG6 or RG6")
    render_cmd.add_argument("--css", type=int, choices=(0, 1), default=0, help="default 0")
    render_cmd.add_argument("--size", type=_size, help="WIDTHxHEIGHT pixels (default: screen)")
    render_cmd.add_argument("--out", required=True, type=Path, help="PNG to write")
    render_cmd.add_argument(
        "--display",
        choices=(*DISPLAYS, "xroar"),
        default="ntsc",
        help="ntsc (default) or square proportions; xroar matches scripts/coco.py's capture "
        "layout, 2 samples per half-clock",
    )
    render_cmd.add_argument("--palette", default="xroar", help="default: xroar")
    return parser


def options_from(args: argparse.Namespace) -> ConvertOptions:
    return ConvertOptions(
        mode=parse_mode(args.mode),
        css="auto" if args.auto_css else args.css,
        size=args.size,
        box=args.box,
        fit=args.fit,
        resample=args.resample,
        dither=args.dither,
        dither_strength=args.dither_strength,
        alpha_threshold=args.alpha_threshold,
        pad=args.pad,
        display=args.display,
        palette=parse_palette(args.palette),
    )


def load_rgba(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        return np.asarray(image.convert("RGBA"))


def save_png(path: Path, picture: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(picture, "RGB").save(path)


def output_paths(prefix: Path, image: Path, with_mask: bool) -> list[Path]:
    """PREFIX.bin, .asm, .png and, with a mask, PREFIX-mask.bin; never the input image."""
    names = [".bin", ".asm", ".png", *(["-mask.bin"] if with_mask else [])]
    paths = [prefix.with_name(prefix.name + name) for name in names]
    if any(path.resolve() == image.resolve() for path in paths):
        raise GraphicsError(f"--out {prefix} would overwrite the input image {image}.")
    return paths


def _write_outputs(
    args: argparse.Namespace,
    grid: list[list[Conversion]],
    labels: list[list[str]],
    options: ConvertOptions,
) -> list[Path]:
    paths = output_paths(args.out, args.image, args.mask)
    paths[0].parent.mkdir(parents=True, exist_ok=True)
    cells = [(label, c) for row_labels, row in zip(labels, grid, strict=True)
             for label, c in zip(row_labels, row, strict=True)]  # fmt: skip
    paths[0].write_bytes(b"".join(c.data for _, c in cells))
    paths[1].write_text(assembly_include(cells, args.image.name, args.mask))
    save_png(paths[2], sheet_preview(grid, options.palette, options.display))
    if args.mask:
        paths[3].write_bytes(b"".join(c.mask for _, c in cells))
    return paths


def run_convert(args: argparse.Namespace) -> list[str]:
    options = options_from(args)
    label = check_label(args.label or label_from_name(args.out.name))
    output_paths(args.out, args.image, args.mask)
    conversion = convert_image(load_rgba(args.image), options)
    paths = _write_outputs(args, [[conversion]], [[label]], options)
    return _report(conversion, conversion.error, paths)


def run_sheet(args: argparse.Namespace) -> list[str]:
    options = options_from(args)
    label = check_label(args.label or label_from_name(args.out.name))
    output_paths(args.out, args.image, args.mask)
    rows = slice_cells(crop_box(load_rgba(args.image), options.box), *args.cell)
    options = options.model_copy(update={"box": None})
    flat = convert_images([cell for row in rows for cell in row], options)
    width = len(rows[0])
    grid = [flat[r * width : (r + 1) * width] for r in range(len(rows))]
    labels = [[f"{label}_r{r}c{c}" for c in range(width)] for r in range(len(rows))]
    paths = _write_outputs(args, grid, labels, options)
    error = sum(c.error for c in flat)
    return [f"{len(flat)} cells in {len(rows)} rows of {width}", *_report(flat[0], error, paths)]


def _report(conversion: Conversion, error: float, paths: list[Path]) -> list[str]:
    mode = conversion.mode
    return [
        f"{mode.name} colour set {conversion.css}: {', '.join(colour_set(mode, conversion.css))}",
        f"colour error (sum of CIELAB distances): {error:.1f}",
        *(str(path) for path in paths),
    ]


def run_render(args: argparse.Namespace) -> list[str]:
    mode = parse_mode(args.mode)
    width, height = args.size or (mode.width, mode.height)
    codes = unpack(args.data.read_bytes(), width, height, mode.bits_per_pixel)
    scale = (2, 1) if args.display == "xroar" else preview_scale(args.display)
    save_png(args.out, render(codes, mode, args.css, parse_palette(args.palette), *scale))
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
    return [*lines, f"Source: {_SOURCE}; CG2 from the PDF 20 page image."]


def run_palettes(_: argparse.Namespace) -> list[str]:
    lines = []
    for palette in PALETTES.values():
        lines += [f"{palette.name}: {palette.description}"]
        lines += [f"  black (CSS={css}): {rgb}" for css, rgb in enumerate(palette.black)]
        lines += [f"  {colour.value}: {rgb}" for colour, rgb in palette.colours.items()]
    return lines


COMMANDS = {
    "modes": run_modes,
    "palettes": run_palettes,
    "convert": run_convert,
    "sheet": run_sheet,
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
