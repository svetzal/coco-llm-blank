"""CoCo 3 GIME graphics: the twenty modes, palette registers and colour codes.

Run `uv run python scripts/graphics.py --help`; this module holds the GIME part of that tool.

Sourced facts:

- Laurence A. Tepolt, *Assembly Language Programming for the CoCo3* (1987), PDF 41-42
  Table 4-10, and Tandy, *Color Computer 3 Service Manual*, PDF 18: the twenty graphics
  modes, with pixels across, bits per pixel (1, 2 or 4: 2, 4 or 16 colours), HRES and CRES.
  examples/gime-graphics ("Choose a mode") lists them with bytes per row and full or short
  width, and its check in XRoar shows all twenty. Rows are 192, 200 or 225 (LPF).
- Tepolt PDF 38-39: rows of pixels follow each other with no gap; in a byte the leftmost
  pixel is in the high bits; a pixel value is a palette register number, 0 to colours-1.
- Service Manual PDF 17: palette registers $FFB0-$FFBF hold six-bit colour codes (64 codes).
  A mode with N colours uses registers 0 to N-1. On an RGB monitor the bits are
  R1 G1 B1 R0 G0 B0 (bit 5 to bit 0); on a composite monitor bits 5-4 are the intensity and
  bits 3-0 the hue. A program writes the codes to $FFB0 and up.

Measured, not sourced: the RGB of each code (`GIME_COMPOSITE`, `GIME_RGB`) is XRoar's
rendering. The displayed pixel width is a deduction: see `samples_per_pixel`.
"""

import json
from collections.abc import Sequence
from typing import Literal

import numpy as np
from PIL import Image
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from raster import (
    RGB,
    ArtOptions,
    Display,
    GraphicsError,
    Prepared,
    as_rgba,
    fcb_rows,
    half_clock_width,
    linear_to_lab,
    pack_with_mask,
    prepare,
    preview_scale,
    quantize,
    srgb_to_linear,
    total_error,
    unpack,
)

GIME_SOURCE = (
    "Tepolt, Assembly Language Programming for the CoCo3, PDF 41-42 Table 4-10; "
    "Tandy CoCo 3 Service Manual PDF 18; examples/gime-graphics"
)
ROWS: tuple[int, ...] = (192, 200, 225)
REGISTERS = 16
CODES = 64
PALETTE_BASE = 0xFFB0
# XRoar 1.13.1 src/tcc1014/tcc1014.c: the active line is 640 samples (full width) or 512
# (short width), in the units in which the VDG's 256-pixel line is 512 samples.
FULL_LINE_SAMPLES = 640
SHORT_LINE_SAMPLES = 512
VDG_SAMPLES_PER_HALF_CLOCK = 2


class GimeMode(BaseModel):
    """One GIME graphics mode with a number of rows. Pixel values are palette registers."""

    model_config = ConfigDict(frozen=True)

    name: str
    width: int
    bits_per_pixel: Literal[1, 2, 4]
    hres: int = Field(ge=0, le=7)
    cres: int = Field(ge=0, le=2)
    full: bool
    rows: int = 192

    @model_validator(mode="after")
    def _known_rows(self) -> "GimeMode":
        if self.rows not in ROWS:
            raise ValueError(f"a GIME screen has 192, 200 or 225 rows, not {self.rows}")
        return self

    @property
    def height(self) -> int:
        return self.rows

    @property
    def pixels_per_byte(self) -> int:
        return 8 // self.bits_per_pixel

    @property
    def bytes_per_row(self) -> int:
        return self.width // self.pixels_per_byte

    @property
    def bytes_total(self) -> int:
        return self.bytes_per_row * self.rows

    @property
    def colour_count(self) -> int:
        return 2**self.bits_per_pixel

    @property
    def line_samples(self) -> int:
        return FULL_LINE_SAMPLES if self.full else SHORT_LINE_SAMPLES

    @property
    def samples_per_pixel(self) -> int:
        """XRoar samples for one pixel: 640 or 512 over the pixels across (a deduction)."""
        return self.line_samples // self.width


def _mode(width: int, bits: int, hres: int, cres: int, full: bool) -> GimeMode:
    return GimeMode(
        name=f"gime-{width}x{2**bits}", width=width, bits_per_pixel=bits, hres=hres,
        cres=cres, full=full,
    )  # fmt: skip


GIME_MODES: dict[str, GimeMode] = {
    mode.name: mode
    for mode in (
        _mode(320, 4, 0b111, 0b10, True),
        _mode(256, 4, 0b110, 0b10, False),
        _mode(160, 4, 0b101, 0b10, True),
        _mode(128, 4, 0b100, 0b10, False),
        _mode(640, 2, 0b111, 0b01, True),
        _mode(512, 2, 0b110, 0b01, False),
        _mode(320, 2, 0b101, 0b01, True),
        _mode(256, 2, 0b100, 0b01, False),
        _mode(160, 2, 0b011, 0b01, True),
        _mode(128, 2, 0b010, 0b01, False),
        _mode(640, 1, 0b101, 0b00, True),
        _mode(512, 1, 0b100, 0b00, False),
        _mode(320, 1, 0b011, 0b00, True),
        _mode(256, 1, 0b010, 0b00, False),
        _mode(160, 1, 0b001, 0b00, True),
        _mode(128, 1, 0b000, 0b00, False),
        _mode(80, 4, 0b011, 0b10, True),
        _mode(64, 4, 0b010, 0b10, False),
        _mode(80, 2, 0b001, 0b01, True),
        _mode(64, 2, 0b000, 0b01, False),
    )
}


def parse_gime_mode(name: str, rows: int = 192) -> GimeMode:
    """A mode by name, such as gime-320x16, with 192, 200 or 225 rows."""
    try:
        mode = GIME_MODES[name.strip().lower()]
    except KeyError:
        raise GraphicsError(
            f"Unknown GIME mode {name!r}. Known: {', '.join(GIME_MODES)}."
        ) from None
    if rows not in ROWS:
        raise GraphicsError(f"A GIME screen has 192, 200 or 225 rows, not {rows}.")
    return mode.model_copy(update={"rows": rows})


def gime_pixel_aspect(mode: GimeMode, display: Display = "ntsc") -> float:
    """A pixel's width divided by its height, with one scan line for each row.

    A deduction, not a sourced fact: XRoar draws a VDG 256-pixel line, one half-clock for each
    pixel, as 512 samples, and a GIME line as 640 or 512 samples (tcc1014.c). A GIME pixel is
    then samples_per_pixel / 2 VDG half-clocks wide, on the same `display` model as the VDG.
    """
    return half_clock_width(display) * mode.samples_per_pixel / VDG_SAMPLES_PER_HALF_CLOCK


def preview_columns(mode: GimeMode, display: Display | Literal["xroar"]) -> tuple[int, int]:
    """Preview columns for one pixel and rows for one scan line.

    `xroar` is the capture's layout: one column for each sample, one row for each line.
    """
    if display == "xroar":
        return mode.samples_per_pixel, 1
    columns, rows = preview_scale(display)
    return mode.samples_per_pixel * columns // VDG_SAMPLES_PER_HALF_CLOCK, rows


# --- Colour codes ---------------------------------------------------------------------------


class GimePalette(BaseModel):
    """The RGB that one display model shows for each of the 64 colour codes."""

    model_config = ConfigDict(frozen=True)

    name: str
    description: str
    colours: tuple[RGB, ...] = Field(min_length=CODES, max_length=CODES)

    def rgb(self, codes: Sequence[int]) -> np.ndarray:
        """An (n, 3) uint8 array of the codes' colours."""
        return np.array([self.colours[code] for code in codes], dtype=np.uint8).reshape(-1, 3)


GIME_COMPOSITE = GimePalette(
    name="gime-composite",
    description=(
        "Measured from XRoar 1.13.1 (this starter's instrumented build) through "
        "scripts/coco.py's rendered-frame capture: S-video input, cross-colour off, active "
        "area only (-tv-input svideo -ccr none), machine coco3, NTSC, GIME 1986. The NTSC "
        "composite picture the starter's checks capture. scripts/gime_swatches.py shows each "
        "code as a band of 256x192 pixels with 16 colours. One emulator's values, not a "
        "television's."
    ),
    colours=(
        (20, 20, 20), (5, 67, 0), (18, 60, 0), (42, 49, 0),  # $00-$03
        (79, 38, 0), (117, 29, 2), (146, 22, 19), (155, 18, 60),  # $04-$07
        (139, 16, 119), (106, 17, 181), (67, 21, 221), (34, 28, 222),  # $08-$0B
        (3, 49, 124), (0, 59, 63), (0, 67, 21), (0, 70, 2),  # $0C-$0F
        (63, 63, 63), (41, 157, 12), (71, 145, 5), (117, 128, 5),  # $10-$13
        (175, 110, 11), (231, 93, 31), (255, 79, 75), (255, 71, 145),  # $14-$17
        (255, 68, 234), (215, 71, 255), (157, 79, 255), (102, 92, 255),  # $18-$1B
        (34, 127, 241), (22, 145, 151), (19, 157, 79), (25, 161, 33),  # $1C-$1F
        (154, 154, 154), (99, 255, 48), (145, 249, 32), (211, 226, 31),  # $20-$23
        (255, 200, 46), (255, 176, 83), (255, 157, 151), (255, 145, 249),  # $24-$27
        (255, 141, 255), (255, 145, 255), (255, 157, 255), (189, 175, 255),  # $28-$2B
        (89, 225, 255), (67, 248, 255), (62, 255, 156), (72, 255, 87),  # $2C-$2F
        (255, 255, 255), (188, 255, 138), (228, 255, 118), (255, 255, 117),  # $30-$33
        (255, 255, 136), (255, 253, 174), (255, 238, 233), (255, 228, 255),  # $34-$37
        (255, 225, 255), (255, 228, 255), (255, 237, 255), (255, 252, 255),  # $38-$3B
        (179, 255, 255), (158, 255, 255), (153, 255, 237), (255, 255, 255),  # $3C-$3F
    ),
)  # fmt: skip
"""XRoar's composite colour of each code $00-$3F, measured, not computed.

XRoar 1.13.1, instrumented build, `scripts/coco.py` rendered capture (`-tv-input svideo
-ccr none`), NTSC coco3, GIME 1986. XRoar models composite with measured voltages and 16 hues
(src/coco3.c, about lines 560-632). Measured by `gime_swatches.measure`;
`gime_swatches_spec.py` measures again and requires these exact values. The 16 codes of examples/gime-graphics agree
with its expected.py RENDERED. Several codes look the same here ($30 and $3F are both white).
"""

GIME_RGB = GimePalette(
    name="gime-rgb",
    description=(
        "Measured from XRoar 1.13.1 (this starter's instrumented build) with its RGB monitor "
        "input (-tv-input rgb -ccr none), active area only, machine coco3, NTSC, GIME 1986, "
        "the same capture otherwise as gime-composite. Codes are R1 G1 B1 R0 G0 B0. One "
        "emulator's values, not a monitor's."
    ),
    colours=(
        (2, 2, 2), (2, 2, 71), (2, 71, 2), (2, 71, 71),  # $00-$03
        (71, 2, 2), (71, 2, 71), (71, 71, 2), (71, 71, 71),  # $04-$07
        (2, 2, 166), (2, 2, 253), (2, 71, 166), (2, 71, 253),  # $08-$0B
        (71, 2, 166), (71, 2, 253), (71, 71, 166), (71, 71, 253),  # $0C-$0F
        (2, 166, 2), (2, 166, 71), (2, 253, 2), (2, 253, 71),  # $10-$13
        (71, 166, 2), (71, 166, 71), (71, 253, 2), (71, 253, 71),  # $14-$17
        (2, 166, 166), (2, 166, 253), (2, 253, 166), (2, 253, 253),  # $18-$1B
        (71, 166, 166), (71, 166, 253), (71, 253, 166), (71, 253, 253),  # $1C-$1F
        (166, 2, 2), (166, 2, 71), (166, 71, 2), (166, 71, 71),  # $20-$23
        (253, 2, 2), (253, 2, 71), (253, 71, 2), (253, 71, 71),  # $24-$27
        (166, 2, 166), (166, 2, 253), (166, 71, 166), (166, 71, 253),  # $28-$2B
        (253, 2, 166), (253, 2, 253), (253, 71, 166), (253, 71, 253),  # $2C-$2F
        (166, 166, 2), (166, 166, 71), (166, 253, 2), (166, 253, 71),  # $30-$33
        (253, 166, 2), (253, 166, 71), (253, 253, 2), (253, 253, 71),  # $34-$37
        (166, 166, 166), (166, 166, 253), (166, 253, 166), (166, 253, 253),  # $38-$3B
        (253, 166, 166), (253, 166, 253), (253, 253, 166), (253, 253, 253),  # $3C-$3F
    ),
)  # fmt: skip
"""XRoar's RGB-monitor colour of each code $00-$3F, measured, not computed.

XRoar 1.13.1, instrumented build, `scripts/coco.py` rendered capture with the target's
`tv_input = "rgb"` in place of S-video, otherwise as `GIME_COMPOSITE`. XRoar's model
(src/coco3.c, about lines 560-632) takes each channel from rgb_intensity_map
{0.000, 0.460, 0.736, 0.920}: red from bits 5 and 2, green from bits 4 and 1, blue from bits 3
and 0. The capture shows those four levels as 2, 71, 166 and 253.
"""

GIME_PALETTES: dict[str, GimePalette] = {p.name: p for p in (GIME_COMPOSITE, GIME_RGB)}


def parse_gime_palette(name: str) -> GimePalette:
    try:
        return GIME_PALETTES[name]
    except KeyError:
        raise GraphicsError(
            f"Unknown GIME palette {name!r}; known: {', '.join(GIME_PALETTES)}."
        ) from None


# --- Palette registers ----------------------------------------------------------------------

Assignment = dict[int, int]
"""Colour code by palette register number."""


def check_assignment(codes: Assignment, colours: int = REGISTERS) -> Assignment:
    """Registers 0 to colours-1 holding codes $00-$3F, in register order."""
    for register, code in codes.items():
        if not 0 <= register < colours:
            raise GraphicsError(
                f"Register {register} is not one of the {colours} registers 0-{colours - 1}."
            )
        if not 0 <= code < CODES:
            raise GraphicsError(f"Colour code {code} is not a six-bit code $00-$3F.")
    return dict(sorted(codes.items()))


def merge_locks(*parts: Assignment) -> Assignment:
    """Combine locked registers from several places; one register cannot hold two codes."""
    merged: Assignment = {}
    for part in parts:
        for register, code in part.items():
            if merged.get(register, code) != code:
                raise GraphicsError(
                    f"Register {register} is locked to both ${merged[register]:02X} and "
                    f"${code:02X}."
                )
            merged[register] = code
    return dict(sorted(merged.items()))


def register_range(span: tuple[int, int] | None, colours: int) -> list[int]:
    """The registers pixels may use: the span (first, last), else all the mode's registers."""
    first, last = span if span is not None else (0, colours - 1)
    if not 0 <= first <= last < colours:
        raise GraphicsError(
            f"Registers {first}-{last} are not inside the mode's registers 0-{colours - 1}."
        )
    return list(range(first, last + 1))


def colour_samples(
    grids: Sequence[Prepared], equal_weight: bool = False
) -> tuple[np.ndarray, np.ndarray]:
    """Distinct opaque linear colours of the grids and how much each counts.

    Each pixel counts once; with `equal_weight` each grid counts the same in total.
    """
    colours, weights = [], []
    for grid in grids:
        pixels = grid.linear[grid.opaque]
        if not len(pixels):
            continue
        unique, counts = np.unique(pixels, axis=0, return_counts=True)
        colours.append(unique)
        weights.append(counts / (counts.sum() if equal_weight else 1))
    if not colours:
        return np.zeros((0, 3)), np.zeros(0)
    return np.concatenate(colours), np.concatenate(weights).astype(np.float64)


def assignment_error(
    colours: np.ndarray, weights: np.ndarray, codes: Sequence[int], palette: GimePalette
) -> float:
    """Weighted sum of CIELAB distances from each colour to the nearest of the codes."""
    if not len(colours):
        return 0.0
    gaps = _distances(colours, palette, list(codes))
    return float((weights * gaps.min(axis=1)).sum())


def _distances(colours: np.ndarray, palette: GimePalette, codes: list[int]) -> np.ndarray:
    lab = linear_to_lab(np.clip(colours, 0, 1))
    choices = linear_to_lab(srgb_to_linear(palette.rgb(codes)))
    return np.linalg.norm(lab[:, None] - choices[None], axis=-1)


def candidate_codes(palette: GimePalette, taken: Sequence[int]) -> list[int]:
    """Codes that show a colour no taken code and no lower code already shows."""
    seen = {palette.colours[code] for code in taken}
    candidates = []
    for code in range(CODES):
        if palette.colours[code] not in seen:
            seen.add(palette.colours[code])
            candidates.append(code)
    return candidates


def select_palette(
    colours: np.ndarray,
    weights: np.ndarray,
    palette: GimePalette,
    mode_colours: int,
    registers: tuple[int, int] | None = None,
    locks: Assignment | None = None,
) -> Assignment:
    """Codes for the registers pixels may use, keeping every locked register as it is.

    The unlocked registers in the span get the codes that make the weighted sum of CIELAB
    distances (each colour to its nearest usable code) smallest: a greedy choice, one register
    at a time, then single swaps of one chosen code for another while any swap lowers the sum.
    Codes are compared by their colour in `palette`; a code that shows the same colour as a
    taken code is not a candidate. The result is deterministic. The chosen codes fill the free
    registers from the darkest. Locked registers outside the span stay in the result.
    """
    locks = check_assignment(locks or {}, mode_colours)
    usable = register_range(registers, mode_colours)
    free = [r for r in usable if r not in locks]
    fixed = [locks[r] for r in usable if r in locks]
    chosen = _choose(colours, weights, palette, fixed, len(free))
    lightness = linear_to_lab(srgb_to_linear(palette.rgb(chosen)))[:, 0]
    ordered = [code for _, code in sorted(zip(lightness, chosen, strict=True))]
    return dict(sorted({**locks, **dict(zip(free, ordered, strict=True))}.items()))


def _choose(
    colours: np.ndarray, weights: np.ndarray, palette: GimePalette, fixed: list[int], count: int
) -> list[int]:
    candidates = candidate_codes(palette, fixed)  # at least 45: more than 16 registers
    if not len(colours):
        colours, weights = np.zeros((1, 3)), np.zeros(1)
    gaps = _distances(colours, palette, candidates)
    base = _distances(colours, palette, fixed).min(axis=1) if fixed else None
    picks = _swap(gaps, weights, base, _greedy(gaps, weights, base, count))
    return [candidates[i] for i in picks]


def _cost_with(gaps: np.ndarray, weights: np.ndarray, current: np.ndarray | None) -> np.ndarray:
    """The total cost of adding each candidate to the codes that give `current`."""
    nearest = gaps if current is None else np.minimum(current[:, None], gaps)
    return weights @ nearest


def _greedy(
    gaps: np.ndarray, weights: np.ndarray, base: np.ndarray | None, count: int
) -> list[int]:
    picks: list[int] = []
    current = base
    for _ in range(count):
        cost = _cost_with(gaps, weights, current)
        cost[picks] = np.inf
        best = int(cost.argmin())
        picks.append(best)
        current = gaps[:, best] if current is None else np.minimum(current, gaps[:, best])
    return picks


def _without(
    gaps: np.ndarray, base: np.ndarray | None, picks: list[int], skip: int
) -> np.ndarray | None:
    others = [p for i, p in enumerate(picks) if i != skip]
    parts = ([base] if base is not None else []) + ([gaps[:, others].min(axis=1)] if others else [])
    return np.minimum.reduce(parts) if parts else None


def _swap(
    gaps: np.ndarray, weights: np.ndarray, base: np.ndarray | None, picks: list[int]
) -> list[int]:
    picks = list(picks)
    improved = True
    while improved:
        improved = False
        for slot in range(len(picks)):
            cost = _cost_with(gaps, weights, _without(gaps, base, picks, slot))
            held = cost[picks[slot]]
            cost[[p for i, p in enumerate(picks) if i != slot]] = np.inf
            best = int(cost.argmin())
            if cost[best] < held - 1e-9:
                picks[slot] = best
                improved = True
    return picks


# --- Conversion -----------------------------------------------------------------------------


class GimeOptions(ArtOptions):
    """How to turn artwork into one GIME mode's register numbers and choose their codes."""

    mode: GimeMode
    palette: GimePalette = GIME_COMPOSITE
    registers: tuple[int, int] | None = None
    locks: Assignment = Field(default_factory=dict)


class GimeConversion(BaseModel):
    """Packed register numbers, the preserve mask (1 keeps what is underneath), and size."""

    model_config = ConfigDict(frozen=True)

    mode: GimeMode
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


class GimeResult(BaseModel):
    """The register assignment that every conversion shares, and the conversions."""

    model_config = ConfigDict(frozen=True)

    assignment: Assignment
    conversions: list[GimeConversion]


def convert_gime_images(images: Sequence[np.ndarray], options: GimeOptions) -> GimeResult:
    """Convert RGBA arrays with one shared palette, chosen from all of their pixels."""
    mode = options.mode
    aspect = gime_pixel_aspect(mode, options.display)
    grids = [prepare(as_rgba(image), options, mode, aspect) for image in images]
    assignment = select_palette(
        *colour_samples(grids), options.palette, mode.colour_count, options.registers,
        options.locks,
    )  # fmt: skip
    usable = register_range(options.registers, mode.colour_count)
    return GimeResult(
        assignment=assignment,
        conversions=[_reduce(grid, options, assignment, usable) for grid in grids],
    )


def _reduce(
    grid: Prepared, options: GimeOptions, assignment: Assignment, usable: list[int]
) -> GimeConversion:
    palette_linear = srgb_to_linear(options.palette.rgb([assignment[r] for r in usable]))
    index = quantize(
        grid.linear, grid.opaque, palette_linear, options.dither, options.dither_strength,
        options.mosaic,
    )  # fmt: skip
    registers = np.where(grid.opaque, np.array(usable, dtype=np.uint8)[index], 0)
    packed = pack_with_mask(registers.astype(np.uint8), grid.opaque, options.mode.bits_per_pixel)
    return GimeConversion(
        mode=options.mode,
        **packed.model_dump(),
        error=total_error(grid.linear, grid.opaque, index, palette_linear),
    )


def render_gime(
    codes: np.ndarray,
    mode: GimeMode,
    assignment: Assignment,
    palette: GimePalette,
    columns: int = 1,
    rows: int = 1,
) -> np.ndarray:
    """An RGB picture of register numbers: `columns` x `rows` preview pixels for each pixel."""
    used = sorted(int(r) for r in np.unique(codes))
    missing = [r for r in used if r not in assignment]
    if missing:
        raise GraphicsError(f"The pixels use registers {missing}, which the palette does not set.")
    table = np.zeros((mode.colour_count, 3), dtype=np.uint8)
    for register in used:
        table[register] = palette.colours[assignment[register]]
    return np.repeat(np.repeat(table[codes], rows, axis=0), columns, axis=1)


# --- Outputs --------------------------------------------------------------------------------


def gime_assembly_block(label: str, conversion: GimeConversion, with_mask: bool = False) -> str:
    """An lwasm `fcb` block of register numbers, one screen row per group of lines."""
    mode = conversion.mode
    bpr = conversion.bytes_per_row
    size = f"{conversion.width}x{conversion.height} {mode.name} pixels"
    layout = f"{bpr} bytes per row, {bpr * conversion.height} bytes"
    lines = [
        f"* {label}: {size}, {mode.bits_per_pixel} bits each, {layout}.",
        "* Pixel values are palette registers; the -palette.asm file holds their colour codes.",
        "* Leftmost pixel in the high bits.",
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


def palette_assembly(
    label: str, assignment: Assignment, palette: GimePalette, mode: GimeMode
) -> str:
    """The codes for registers 0 to colours-1 as one `fcb` line, register 0 first."""
    count = mode.colour_count
    unset = [r for r in range(count) if r not in assignment]
    codes = bytes(assignment.get(r, 0) for r in range(count))
    addresses = f"${PALETTE_BASE:04X}-${PALETTE_BASE + count - 1:04X}"
    lines = [
        "* Generated by scripts/graphics.py. Regenerate rather than edit.",
        f"* {label}: colour codes for palette registers 0-{count - 1} ({addresses}) of",
        f"* {mode.name}, register 0 first.",
        f"* Chosen with the {palette.name} colours (XRoar 1.13.1). Another display shows the",
        "* same codes in other colours.",
        *(
            f"*   register {r:>2}: ${assignment[r]:02X} {palette.colours[assignment[r]]}"
            for r in assignment
            if r < count
        ),
    ]
    if unset:
        lines.append(f"* Registers {unset} are not set by this palette; they hold $00 here.")
    lines += [f"{label}_count equ {count}", *fcb_rows(label, codes, count)]
    return "\n".join(lines) + "\n"


class RegisterCode(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    number: int = Field(alias="register", ge=0, lt=REGISTERS)
    code: int = Field(ge=0, lt=CODES)


class PaletteFile(BaseModel):
    """PREFIX-palette.json: the registers a palette sets and the model it was chosen with."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    palette: str
    registers: list[RegisterCode]

    @model_validator(mode="after")
    def _each_register_once(self) -> "PaletteFile":
        numbers = [entry.number for entry in self.registers]
        if len(numbers) != len(set(numbers)):
            raise ValueError("each register appears at most once")
        return self


def palette_json(assignment: Assignment, palette: GimePalette, mode: GimeMode) -> str:
    """A JSON document with one line for each register the palette sets."""
    header = {"generator": "scripts/graphics.py", "mode": mode.name, "palette": palette.name}
    entries = [
        json.dumps({"register": r, "code": c, "hex": f"${c:02X}", "rgb": list(palette.colours[c])})
        for r, c in assignment.items()
    ]
    fields = [f"  {json.dumps(key)}: {json.dumps(value)}," for key, value in header.items()]
    body = ",\n".join(f"    {entry}" for entry in entries)
    return "{\n" + "\n".join(fields) + '\n  "registers": [\n' + body + "\n  ]\n}\n"


def parse_palette_file(text: str | bytes, source: str = "palette file") -> tuple[Assignment, str]:
    """The register assignment of a PREFIX-palette.json document, and its palette's name."""
    try:
        document = PaletteFile.model_validate_json(text)
    except ValidationError as error:
        raise GraphicsError(f"{source} is not a palette file: {error}") from None
    return {entry.number: entry.code for entry in document.registers}, document.palette


def palette_grid(rgba: np.ndarray, max_pixels: int, alpha_threshold: int = 128) -> Prepared:
    """An image's pixels for palette selection, box-reduced to at most `max_pixels`."""
    rgba = as_rgba(rgba)
    height, width = rgba.shape[:2]
    scale = min(1.0, (max_pixels / (width * height)) ** 0.5)
    if scale < 1:
        size = (max(1, int(width * scale)), max(1, int(height * scale)))
        rgba = np.asarray(Image.fromarray(rgba, "RGBA").resize(size, Image.Resampling.BOX))
    return Prepared(linear=srgb_to_linear(rgba[..., :3]), opaque=rgba[..., 3] >= alpha_threshold)
