"""The pixel core that the VDG and GIME converters share: no CoCo mode or palette lives here.

Colour matching (CIELAB, D65), colour reduction (nearest, Bayer and Floyd-Steinberg dither,
mosaic blocks), packing of pixel codes into bytes, the shape of a sample on the display, the
crop and resize of artwork, and lwasm labels. `graphics.py` holds the VDG modes and the
command line; `gime.py` holds the GIME modes and palette registers.

The display proportions are a deduction with an external assumption: see `half_clock_width`.
"""

import re
from fractions import Fraction
from typing import Annotated, Literal, Protocol

import numpy as np
from PIL import Image
from pydantic import BaseModel, ConfigDict, Field, model_validator


class GraphicsError(ValueError):
    """An input that cannot be converted, packed or rendered as asked."""


Channel = Annotated[int, Field(ge=0, le=255)]
RGB = tuple[Channel, Channel, Channel]

# --- Display proportions --------------------------------------------------------------------

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


def preview_scale(display: Display) -> tuple[int, int]:
    """Preview samples per half-clock and rows per scan line, in the display's proportion."""
    ratio = Fraction(half_clock_width(display)).limit_denominator(8)
    factor = 2 if ratio == 1 else 1
    return ratio.numerator * factor, ratio.denominator * factor


# --- Packing --------------------------------------------------------------------------------


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


class Packed(BaseModel):
    """Picture bytes and the preserve mask (1 keeps what is underneath) of one padded grid."""

    model_config = ConfigDict(frozen=True)

    width: int
    height: int
    data: bytes
    mask: bytes


def pack_with_mask(codes: np.ndarray, opaque: np.ndarray, bits_per_pixel: int) -> Packed:
    """Pad the right edge with transparent code-0 pixels to whole bytes, then pack both."""
    pad = -codes.shape[1] % (8 // bits_per_pixel)
    codes = np.pad(codes, ((0, 0), (0, pad)))
    opaque = np.pad(opaque, ((0, 0), (0, pad)))
    keep = np.where(opaque, 0, 2**bits_per_pixel - 1).astype(np.uint8)
    return Packed(
        width=codes.shape[1],
        height=codes.shape[0],
        data=pack(codes, bits_per_pixel),
        mask=pack(keep, bits_per_pixel),
    )


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
    mosaic: tuple[int, int] | None = None,
) -> np.ndarray:
    """Pixel codes for linear-light pixels; transparent pixels get code 0.

    Nearest colour is by CIELAB distance. `bayer` adds a 4x4 ordered threshold to all three
    channels, scaled by `strength` times the palette's spread (a heuristic, not tuned).
    `floyd-steinberg` diffuses `strength` times each pixel's linear-light error, left to
    right on every row; the error is taken after clipping to 0-1, so colours the set cannot
    reach do not pile up error. `mosaic` (width, height) gives each block of the grid one
    colour: see `mosaic_codes`. A mosaic cannot also dither. All are deterministic.
    """
    if mosaic is not None:
        if dither != "none":
            raise GraphicsError("A mosaic gives each block one colour; it cannot also dither.")
        codes = mosaic_codes(linear, opaque, palette_linear, mosaic)
    elif dither == "floyd-steinberg":
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


def mosaic_codes(
    linear: np.ndarray, opaque: np.ndarray, palette_linear: np.ndarray, block: tuple[int, int]
) -> np.ndarray:
    """One palette index for each block of `block` (width, height) pixels from the top left.

    The block's opaque pixels are averaged in linear light, and the mean takes the nearest
    palette colour by CIELAB distance. Blocks at the right and bottom edges can be smaller.
    """
    block_width, block_height = block
    if block_width < 1 or block_height < 1:
        raise GraphicsError(
            f"A mosaic block is at least 1x1 pixels, not {block_width}x{block_height}."
        )
    height, width = opaque.shape
    across = -(-width // block_width)
    ids = (np.arange(height) // block_height)[:, None] * across + np.arange(width) // block_width
    count = ids.max() + 1
    weight = opaque.astype(np.float64).ravel()
    sums = np.stack(
        [np.bincount(ids.ravel(), linear[..., c].ravel() * weight, count) for c in range(3)],
        axis=-1,
    )
    means = sums / np.maximum(np.bincount(ids.ravel(), weight, count), 1)[:, None]
    return nearest_codes(means, palette_linear)[ids]


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


# --- Fitting artwork to a pixel grid --------------------------------------------------------

Resample = Literal["nearest", "box", "bilinear", "lanczos"]
RESAMPLES: dict[str, Image.Resampling] = {
    "nearest": Image.Resampling.NEAREST,
    "box": Image.Resampling.BOX,
    "bilinear": Image.Resampling.BILINEAR,
    "lanczos": Image.Resampling.LANCZOS,
}
Fit = Literal["crop", "stretch"]


class Screen(Protocol):
    """The part of a graphics mode that limits a picture's size."""

    @property
    def name(self) -> str: ...

    @property
    def width(self) -> int: ...

    @property
    def height(self) -> int: ...

    @property
    def pixels_per_byte(self) -> int: ...


class ArtOptions(BaseModel):
    """How to fit square-pixel RGBA artwork to a pixel grid and reduce its colours."""

    model_config = ConfigDict(frozen=True)

    size: tuple[int, int] | None = None
    box: tuple[int, int, int, int] | None = None
    fit: Fit = "crop"
    resample: Resample = "box"
    dither: Dither = "none"
    dither_strength: float = Field(default=1.0, ge=0)
    mosaic: tuple[int, int] | None = None
    alpha_threshold: int = Field(default=128, ge=0, le=256)
    pad: bool = False
    display: Display = "ntsc"

    @model_validator(mode="after")
    def _mosaic_without_dither(self) -> "ArtOptions":
        if self.mosaic is not None and self.dither != "none":
            raise ValueError("a mosaic gives each block one colour; it cannot also dither")
        return self


class Prepared(BaseModel):
    """Resized artwork: linear-light RGB and which pixels are opaque."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    linear: np.ndarray
    opaque: np.ndarray


def target_size(screen: Screen, options: ArtOptions) -> tuple[int, int]:
    """The requested pixel grid; the whole screen when no size is given."""
    width, height = options.size or (screen.width, screen.height)
    if width < 1 or height < 1:
        raise GraphicsError(f"Size {width}x{height} must be at least 1x1 pixels.")
    if width > screen.width or height > screen.height:
        raise GraphicsError(
            f"Size {width}x{height} is larger than the {screen.name} screen "
            f"({screen.width}x{screen.height})."
        )
    if width % screen.pixels_per_byte and not options.pad:
        raise GraphicsError(
            f"Width {width} is not a multiple of {screen.pixels_per_byte} pixels per byte in "
            f"{screen.name}. Choose another width, or pad the right edge with transparent pixels."
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


def as_rgba(image: np.ndarray) -> np.ndarray:
    if image.ndim != 3 or image.shape[2] not in (3, 4) or 0 in image.shape[:2]:
        raise GraphicsError("Expected a non-empty RGB or RGBA image.")
    if image.shape[2] == 3:
        image = np.dstack((image, np.full(image.shape[:2], 255, dtype=np.uint8)))
    return image.astype(np.uint8)


def prepare(rgba: np.ndarray, options: ArtOptions, screen: Screen, pixel_aspect: float) -> Prepared:
    """Crop to the box, fit the displayed shape of the grid, and resize to the grid."""
    width, height = target_size(screen, options)
    region = crop_box(rgba, options.box)
    if options.fit == "crop":
        region = crop_to_aspect(region, width * pixel_aspect / height)
    image = Image.fromarray(np.ascontiguousarray(region), "RGBA")
    resized = np.asarray(image.resize((width, height), RESAMPLES[options.resample]))
    return Prepared(
        linear=srgb_to_linear(resized[..., :3]), opaque=resized[..., 3] >= options.alpha_threshold
    )


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


# --- Assembly labels and rows ---------------------------------------------------------------

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


def fcb_rows(label: str, data: bytes, bytes_per_row: int) -> list[str]:
    """The label, then `fcb` lines of at most 16 bytes; a row never shares a line."""
    lines = [label]
    for start in range(0, len(data), bytes_per_row):
        row = data[start : start + bytes_per_row]
        for part in range(0, len(row), BYTES_PER_LINE):
            values = ",".join(f"${b:02X}" for b in row[part : part + BYTES_PER_LINE])
            lines.append(f"        fcb {values}")
    return lines
