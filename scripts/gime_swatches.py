"""Measure XRoar's rendered colour of all 64 GIME colour codes, through scripts/coco.py.

`measure` writes a small CoCo 3 project, assembles it once for each batch of 16 codes and
captures XRoar's rendered frame on two targets: the starter's normal capture (S-video, no
cross-colour) and XRoar's RGB monitor input (`-tv-input rgb`). The program shows 256x192
pixels with 16 colours and puts palette register r in rows 12r to 12r+11, so every line is one
colour and no horizontal filter mixes two colours. It writes codes 16b to 16b+15 to registers 0
to 15 for batch b. `swatch_colours` reads the centre of each band.

The display setup is the one examples/gime-graphics uses and checks: its `$FF90`, `$FF98`,
`$FF9C`-`$FF9F` writes, the CPU window at `$FFA2`, and `$FF99` = `$1A` for 256 pixels with 16
colours (HRES 110, CRES 10, 192 rows). Palette registers are `$FFB0`-`$FFBF` (Tandy, Color
Computer 3 Service Manual, PDF 17).

The colours are one emulator's (XRoar 1.13.1) rendering, not measurements of a monitor or a
television. `gime_swatches_spec.py` measures them again and compares them with the tables
in gime.py.
"""

from pathlib import Path

import numpy as np
from coco import Equipment, Host, build, capture, load_project
from raster import RGB

BATCHES = 4
BAND_ROWS = 12
SOURCE = """\
* Sixteen horizontal bands, one for each palette register, in 256x192 with 16 colours.
* Registers 0-15 hold colour codes BASE to BASE+15. See scripts/gime_swatches.py.
        ifdef BATCH1
BASE    equ 16
        endc
        ifdef BATCH2
BASE    equ 32
        endc
        ifdef BATCH3
BASE    equ 48
        endc
        ifndef BASE
BASE    equ 0
        endc
WINDOW  equ $4000                   CPU $4000-$5FFF is MMU entry $FFA2
        org $3000
start   clr page                    physical $00000: page 0
        clr $FFA2
        ldx #WINDOW
        clr band
nextb   lda #12
        sta count
        lda band
        ldb #$11                    both pixels of each byte are the band's register
        mul
        stb value
row     ldy #128                    128 bytes in one row
byte    lda value
        sta ,x+
        cmpx #WINDOW+$2000
        blo next
        inc page
        lda page
        sta $FFA2
        ldx #WINDOW
next    leay -1,y
        bne byte
        dec count
        bne row
        inc band
        lda band
        cmpa #16
        blo nextb
        ldu #$FFB0
        lda #BASE
pal     sta ,u+
        inca
        cmpu #$FFC0
        blo pal
        clr $FF9A                   border: code 0
        lda #%01001110              CoCo 3 modes, MMU on, as examples/gime-graphics
        sta $FF90
        lda #%10000000              graphics, one line for each row
        sta $FF98
        lda #$1A                    256 pixels, 16 colours, 192 rows
        sta $FF99
        clr $FF9C
        clr $FF9D                   display from physical $00000
        clr $FF9E
        clr $FF9F
ready   bra ready
page    fcb 0
band    fcb 0
count   fcb 0
value   fcb 0
        end start
"""
SETTINGS = """\
source = "main.asm"

[targets.gime-composite]
firmware = "coco3"
machine = "coco3"
cpu = "6809"
tv = "ntsc"
vdg = "gime1986"
ram_kib = 128
extended = "coco3.rom"

[targets.gime-rgb]
firmware = "coco3"
machine = "coco3"
cpu = "6809"
tv = "ntsc"
tv_input = "rgb"
vdg = "gime1986"
ram_kib = 128
extended = "coco3.rom"

[memory]
at = { start = 0x3000 }

[variants.batch1]
defines = ["BATCH1"]

[variants.batch2]
defines = ["BATCH2"]

[variants.batch3]
defines = ["BATCH3"]

[capture]
video = true

[check]
checkpoint = "ready"
frames = [1]
unreachable = "ready+1"
emulated_seconds = 10
"""
TARGETS = ("gime-composite", "gime-rgb")
VARIANTS = ("", "batch1", "batch2", "batch3")


class SwatchError(ValueError):
    """A captured frame does not show sixteen uniform bands."""


def swatch_colours(pixels: np.ndarray) -> list[RGB]:
    """The colour of each of the 16 bands of a 512x192 capture, register 0 first.

    Each band must be one colour over its middle rows and middle 448 samples.
    """
    if pixels.shape != (192, 512, 3):
        raise SwatchError(f"Expected a 512x192 RGB capture, not {pixels.shape}.")
    colours = []
    for register in range(16):
        top = register * BAND_ROWS
        band = pixels[top + 2 : top + BAND_ROWS - 2, 32:480].reshape(-1, 3)
        values = np.unique(band, axis=0)
        if len(values) != 1:
            raise SwatchError(f"Band {register} holds {len(values)} colours, not one.")
        red, green, blue = (int(v) for v in values[0])
        colours.append((red, green, blue))
    return colours


def palette_differences(measured: list[RGB], table: tuple[RGB, ...]) -> list[str]:
    """One line for each code whose measured colour differs from the table; none if equal."""
    if len(measured) != len(table):
        return [f"{len(measured)} colours measured, {len(table)} in the table"]
    return [
        f"${code:02X}: measured {got}, table {want}"
        for code, (got, want) in enumerate(zip(measured, table, strict=True))
        if tuple(got) != tuple(want)
    ]


def write_project(directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "main.asm").write_text(SOURCE)
    (directory / "coco.toml").write_text(SETTINGS)
    return directory


def measure(directory: Path, host: Host | None = None) -> dict[str, list[RGB]]:
    """Codes $00-$3F as XRoar renders them on each target, from a project in `directory`."""
    host = host or Host()
    project = load_project(write_project(directory))
    built = [build(project, host, variant) for variant in VARIANTS]
    return {
        target: [
            colour
            for program in built
            for colour in swatch_colours(
                capture(project, host, program, target, 1, Equipment(video=True)).picture.pixels
            )
        ]
        for target in TARGETS
    }
