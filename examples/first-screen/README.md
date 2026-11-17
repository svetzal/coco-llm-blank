# Set up a graphics screen

This example selects a full-graphics mode of the CoCo 1/2 video chip (VDG) and
places the screen in memory. It stops when the screen is ready. It has no game
loop, no input and no timing.

The same program runs on a CoCo 1, two CoCo 2 models and a CoCo 3. The CoCo 3
shows these modes with its VDG-compatible modes. [Machines](#machines) tells
what is different. The example does not use the CoCo 3 high-resolution (GIME)
modes.

## Choose a mode

Four-colour modes (CG) use two bits for each pixel. Two-colour modes (RG) use
one bit for each pixel. Extended Color BASIC gives five modes a `PMODE` number.

| Mode | PMODE | Pixels | Colours | Bytes per row | Screen bytes | SAM V2..V0 | `$FF22` bits 7..4 | Checked on |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CG1 | | 64x64 | 4 | 16 | 1024 | `001` | `1000` | CoCo 1, 2, 2B, 3 |
| RG1 | | 128x64 | 2 | 16 | 1024 | `001` | `1001` | CoCo 1, 2, 2B, 3 |
| CG2 | | 128x64 | 4 | 32 | 2048 | `010` | `1010` | CoCo 1, 2, 2B, 3 |
| RG2 | 0 | 128x96 | 2 | 16 | 1536 | `011` | `1011` | CoCo 1, 2, 2B, 3 |
| CG3 | 1 | 128x96 | 4 | 32 | 3072 | `100` | `1100` | CoCo 1, 2, 2B, 3 |
| RG3 | 2 | 128x192 | 2 | 16 | 3072 | `101` | `1101` | CoCo 1, 2, 2B, 3 |
| CG6 | 3 | 128x192 | 4 | 32 | 6144 | `110` | `1110` | CoCo 1, 2, 2B, 3 |
| RG6 | 4 | 256x192 | 2 | 32 | 6144 | `110` | `1111` | CoCo 1, 2, 2B, 3 |

- One colour set applies to the full screen: green, yellow, blue and red, or
  buff, cyan, magenta and orange. A two-colour mode shows black and green, or
  black and buff.
- A small mode uses less memory and is faster to redraw. Its pixels are larger.
- CG6 is a good default for a colour game. RG6 gives the most detail.
- Pixels are not square. The [graphics guide](../../guidance/techniques/graphics.md)
  gives the shape of each mode's pixels.
- The leftmost pixel of a byte is in the high bits: bit 7 in RG modes, bits 7
  and 6 in CG modes.
- Tepolt names the CoCo 3 modes G1C, G1R, G2C, G2R, G3C, G3R, G6C and G6R.

## Machines

The program and the screen bytes are the same on each machine. The setup steps
and the mode values are the same (Tepolt PDF 46, Table 5-5). The CoCo 3 needs
no other setup.

- CoCo 1 and CoCo 2: the MC6847 gives each colour code a fixed colour. The
  CoCo 2B has the MC6847T1. The rendered check measures the same colours on it.
- CoCo 3: each colour code selects a palette register. BASIC loads the
  registers at reset (Tepolt PDF 46 and 57). The program keeps them. Thus the
  colours have the same names, but the RGB values are different.
  [Palette-swatches](../palette-swatches/README.md) gives both sets of RGB
  values. They are measured in XRoar.

RG1, RG2 and RG3 on the CoCo 3: two sources give these modes with the same
values as the VDG. They are Tepolt PDF 46 (G1R, G2R and G3R) and the *Color
Computer 3 Service Manual* PDF 18. The rendered check on the CoCo 3 measures
normal pixels in XRoar 1.13.1, which agrees with the two sources.

The negative control is XRoar 1.13.1 with upstream commit 4e862c46 reverted.
That build shows each pixel two pixels wide, and the `rg3` check fails. XRoar
1.13 and older show the modes with that double-width rendering. The `run`
command uses the same pinned XRoar as the check. We know of no test on a
physical CoCo 3.

## Set up the screen

The example is the three `>>> EXAMPLE` parts of [main.asm](main.asm). The other
code is context: it draws a test picture and holds it at the `ready` label. A
project replaces that loop with its own main loop.

1. The mode values from the table, selected by one assembler define.
2. The setup steps:
   1. Set the SAM display offset, F6 to F0, to the screen address divided by
      512. The screen address must be a multiple of 512.
   2. Set the SAM display mode, V2 to V0.
   3. Set `$FF22` bits 7 to 4 to the VDG mode and bit 3 to the colour set
      (CSS). Do not change bits 2 to 0. Other hardware uses them.
3. The `samset` routine. Each SAM bit has two addresses. A write to the even
   address clears the bit. A write to the odd address sets it.

The example does not change the interrupts, the stack or the CPU clock.
BASIC's field-sync interrupt stays on. Its handler runs each field, but it does
not change the screen. The example does no timed work, so it does not need to
stop the interrupt. The check measures the same screen bytes on each target.

## See and check each mode

Open a terminal in the starter folder. Copy one line and paste it to see that
mode in XRoar. Close the window to stop it.

```sh
uv run python scripts/coco.py run examples/first-screen                # CG6, PMODE 3
uv run python scripts/coco.py run examples/first-screen --variant rg6  # RG6, PMODE 4
uv run python scripts/coco.py run examples/first-screen --variant rg3  # RG3, PMODE 2
uv run python scripts/coco.py run examples/first-screen --variant cg3  # CG3, PMODE 1
uv run python scripts/coco.py run examples/first-screen --variant rg2  # RG2, PMODE 0
uv run python scripts/coco.py run examples/first-screen --variant cg2  # CG2
uv run python scripts/coco.py run examples/first-screen --variant rg1  # RG1
uv run python scripts/coco.py run examples/first-screen --variant cg1  # CG1
```

To see a mode on the CoCo 3, add `--target coco3`. Use `coco2` or `coco2b`
for a CoCo 2.

```sh
uv run python scripts/coco.py run examples/first-screen --target coco3                # CG6, PMODE 3
uv run python scripts/coco.py run examples/first-screen --target coco3 --variant rg6  # RG6, PMODE 4
uv run python scripts/coco.py run examples/first-screen --target coco3 --variant cg3  # CG3, PMODE 1
uv run python scripts/coco.py run examples/first-screen --target coco3 --variant cg2  # CG2
uv run python scripts/coco.py run examples/first-screen --target coco3 --variant cg1  # CG1
```

Each mode other than CG6 is a variant in [coco.toml](coco.toml). To check all
the modes on all four targets, paste this line:

```sh
uv run python scripts/coco.py check examples/first-screen --video
```

The `--video` option needs the
[instrumented XRoar](../../guidance/starter/toolchain.md#instrumented-xroar).

The check runs on four targets in [coco.toml](coco.toml). Each target has
NTSC and a normal-clock 6809:

- `coco1`: a CoCo 1 with Color BASIC 1.1, Extended Color BASIC 1.1, 32 KiB
  and the MC6847.
- `coco2`: a CoCo 2 with Color BASIC 1.2, Extended Color BASIC 1.1, 32 KiB
  and the MC6847.
- `coco2b`: a CoCo 2B with Color BASIC 1.3, Extended Color BASIC 1.1, 32 KiB
  and the MC6847T1.
- `coco3`: a CoCo 3 with Super Extended Color BASIC, 128 KiB and the 1986
  GIME.

The program does not use Extended Color BASIC.

On each target, the check compares the screen bytes and XRoar's rendered
picture of each mode with [expected.py](expected.py), with colour set 0. The
"Checked on" column of the mode table gives the modes for each target. The
model uses the `xroar` palette on the CoCo 1 and both CoCo 2 targets, and the
`xroar-coco3` palette on the CoCo 3.

On the CoCo 3, the RAM snapshot holds physical memory. The screen at `$0400`
is at offset `$10400` in the snapshot (Tepolt PDF 58). The `screen` value of
the `coco3` target tells this to the check. In XRoar, the captured frame on the
CoCo 3 has the same size and position as on the CoCo 1 and 2.

The check does not prove the result on a television, a monitor or a physical
CoCo.

## Sources

Read these pages before you change a value. Use
[reference lookup](../../guidance/starter/references.md) to get them.

- Tandy, *Color Computer Technical Reference Manual*:
  - PDF 11: SAM control.
  - PDF 14: `$FF22` bits.
  - PDF 15: SAM bits for each mode.
  - PDF 30: the size of each mode and its pixels, in dot clocks and scan lines.
  - PDF 31, Table 1: SAM and `$FF22` values for each mode.
- Motorola, *MC6847 Video Display Generator* datasheet, PDF pages 18 to 21:
  sizes, colours and the order of the pixels in a byte.
- *The Rainbow*, October 1986, PDF page 119: the `PMODE` number of each mode.
- Laurence A. Tepolt, *Assembly Language Programming for the CoCo3*:
  - PDF 46, Table 5-5: the same `$FF22` and SAM values select the eight modes
    on a CoCo 3. Each pixel code selects a palette register.
  - PDF 57, step 44: the values that BASIC loads into the palette registers.
  - PDF 58: where BASIC's memory is in the CoCo 3 physical memory.
- Tandy, *Color Computer 3 Service Manual*, PDF 18: the CoCo 3 has the CoCo 1
  and 2 modes.

The Tandy manual gives 2K for RG2. The datasheet gives 1536 bytes. The rendered
check of RG2 passes with 1536 bytes.
