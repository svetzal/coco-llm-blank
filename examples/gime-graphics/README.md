# Set up a CoCo 3 graphics screen

This example selects one of twenty graphics modes of the CoCo 3 video chip
(GIME). It puts the screen at a physical address that you choose, sets
the sixteen palette registers and shows the screen.

The CPU writes the screen through one 8 KiB MMU window. The GIME shows it from
the display address. Both values come from the same physical address. Thus the
program works on 128 KiB and 512 KiB machines, and on the 1986 and 1987 GIME.

The example stops when the GIME shows the screen. It has no game loop, no
input, no scrolling, no page flip and no return to BASIC. It does not use the
VDG modes of the CoCo 1 and 2. [First-screen](../first-screen/README.md) shows
those modes.

## Choose a mode

Each mode has a width in pixels and 2, 4 or 16 colours. Each pixel selects a
palette register. The table gives the `$FF99` value for 192 rows.

| Define | Pixels | Colours | HRES | CRES | `$FF99` | Bytes per row | Screen bytes | Width | BASIC |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| (none) | 320 | 16 | `111` | `10` | `$1E` | 160 | 30720 | Full | `HSCREEN 2` |
| `G256X16` | 256 | 16 | `110` | `10` | `$1A` | 128 | 24576 | Short | |
| `G160X16` | 160 | 16 | `101` | `10` | `$16` | 80 | 15360 | Full | |
| `G128X16` | 128 | 16 | `100` | `10` | `$12` | 64 | 12288 | Short | |
| `G640X4` | 640 | 4 | `111` | `01` | `$1D` | 160 | 30720 | Full | `HSCREEN 4` |
| `G512X4` | 512 | 4 | `110` | `01` | `$19` | 128 | 24576 | Short | |
| `G320X4` | 320 | 4 | `101` | `01` | `$15` | 80 | 15360 | Full | `HSCREEN 1` |
| `G256X4` | 256 | 4 | `100` | `01` | `$11` | 64 | 12288 | Short | |
| `G160X4` | 160 | 4 | `011` | `01` | `$0D` | 40 | 7680 | Full | |
| `G128X4` | 128 | 4 | `010` | `01` | `$09` | 32 | 6144 | Short | |
| `G640X2` | 640 | 2 | `101` | `00` | `$14` | 80 | 15360 | Full | `HSCREEN 3` |
| `G512X2` | 512 | 2 | `100` | `00` | `$10` | 64 | 12288 | Short | |
| `G320X2` | 320 | 2 | `011` | `00` | `$0C` | 40 | 7680 | Full | |
| `G256X2` | 256 | 2 | `010` | `00` | `$08` | 32 | 6144 | Short | |
| `G160X2` | 160 | 2 | `001` | `00` | `$04` | 20 | 3840 | Full | |
| `G128X2` | 128 | 2 | `000` | `00` | `$00` | 16 | 3072 | Short | |
| `G80X16` | 80 | 16 | `011` | `10` | `$0E` | 40 | 7680 | Full | |
| `G64X16` | 64 | 16 | `010` | `10` | `$0A` | 32 | 6144 | Short | |
| `G80X4` | 80 | 4 | `001` | `01` | `$05` | 20 | 3840 | Full | |
| `G64X4` | 64 | 4 | `000` | `01` | `$01` | 16 | 3072 | Short | |

- A full-width row is 20, 40, 80 or 160 bytes. HRES bit 0 is 1. The picture
  fills the width of the screen. A short row is 16, 32, 64 or 128 bytes. The
  picture has a border at the left and the right.
- 320 pixels with 16 colours is the default. It is the 16-colour mode with
  the most pixels, and BASIC's `HSCREEN 2`. It uses 30720 bytes, four 8 KiB
  pages.
- 256 pixels with 16 colours has the same colours in 24576 bytes, three
  pages.
- The Service Manual lists ten of these modes. Sock's reference lists the
  first sixteen. Tepolt's Table 4-10 lists all twenty.
- Tepolt lists two more values: HRES `110` or `111` with CRES `00`. Each pixel
  then uses two bytes (Tepolt's format X). The example does not show them.
- HRES `000` or `001` with CRES `10` is not used. CRES `11` blanks the
  screen.

### Choose the number of rows

`$FF99` bits 6 and 5 (LPF) select the rows. Add the value to the table value.

| Define | Rows | LPF | Add to `$FF99` | Largest screen |
| --- | --- | --- | --- | --- |
| (none) | 192 | `00` | `$00` | 30720 bytes |
| `L200` | 200 | `01` | `$20` | 32000 bytes |
| `L225` | 225 | `11` | `$60` | 36000 bytes |

LPF `10` is reserved. XRoar's source shows 199 rows for LPF `01`, not 200,
and calls the value measured. Do not put important pixels on row 199.

### Choose the physical address

The CPU sees 64 KiB. The GIME reads physical memory directly. Calculate these
values from one physical address `A`:

| Value | Calculation | `A = $00000` |
| --- | --- | --- |
| MMU page for the CPU window | `A / $2000` | `$00` |
| `$FF9D`, address bits 18..11 | `A / $800` | `$00` |
| `$FF9E`, address bits 10..3 | `(A / 8) AND $FF` | `$00` |
| CPU address of the first byte | window + `(A AND $1FFF)` | `$4000` |

- `A` must be a multiple of 8. Sock's reference says that some GIMEs crash
  with an odd value in `$FF9E` in some modes. Use a multiple of 16.
- A graphics screen is larger than one 8 KiB page. Write it one page at a
  time through the window, or map more windows.
- A 128 KiB CoCo 3 does not use address bits 18 and 17. An address below
  `$20000` is the same RAM on both sizes. The
  [text-addressing example](../text-addressing/README.md#choose-the-physical-address)
  explains the 128 KiB alias.
- The example uses `$00000`. On 128 KiB, this is also the RAM at `$60000`.

## Set up the screen

The example is the three `>>> EXAMPLE` parts of [main.asm](main.asm). The
other code is context: it draws a test card and holds it at the `ready` label.
A project replaces that loop with its own main loop.

1. The values for each mode and the address values from the tables above.
   One assembler define selects the mode, and one selects the rows. The labels
   are `WIDTH`, `BPP`, `HRES`, `ROWS`, `LPF`, `COLOURS`, `CRES`, `RES`,
   `BYTES`, `SCREEN`, `PAGE`, `BASEHI`, `BASELO` and `WINDOW`.

2. The CPU window, at the labels `first` and `put`. `first` writes `PAGE` to
   `$FFA2`. CPU `$4000-$5FFF` then shows the first screen page. `put` stores
   one byte. At the end of the window, it maps the next page.

3. The display setup. It starts at the palette writes:

   1. Write the sixteen colour codes to `$FFB0-$FFBF`. A 2- or 4-colour mode
      uses only the first 2 or 4 registers.

   2. Write 0 to `$FF9A`: a border of colour code 0.

   3. Write `$4E` to `$FF90`. This selects native mode, the MMU on, no GIME
      interrupt outputs, constant RAM at `$FExx`, standard SCS and 32 KiB
      internal ROM.

   4. Write `$80` to `$FF98`: graphics (BP=1), one scan line for each row of
      pixels.

   5. Write `RES` to `$FF99`.

   6. Write 0 to `$FF9C`: no vertical scroll.

   7. Write `BASEHI` to `$FF9D` and `BASELO` to `$FF9E`.

   8. Write 0 to `$FF9F`: a normal buffer width and no horizontal offset.

The example writes each display register that the mode uses, with all eight
bits. It does not read back the GIME registers.

Each byte holds 8, 4 or 2 pixels. The leftmost pixel is in the high bits. A
row of pixels follows the row above it with no gap.

A palette register holds a six-bit colour code. On an RGB monitor, the bits
are R1 G1 B1 R0 G0 B0. On a television or composite monitor, the same code
has a different meaning: bits 5 and 4 are the intensity and bits 3 to 0 are
the hue. The [colour guide](../../guidance/techniques/colour.md#coco-3-palette-meanings)
explains this. The example's codes are for the composite picture.

The test card puts the last colour on the outer rows and columns. Inside, it
draws one vertical bar of each colour. Every 16 rows, each bar takes the next
colour.

The example does not change the interrupts, the stack, the direct page, the
CPU clock or `$FF91`. It keeps the MMU task that BASIC uses. It leaves `$FFA2`
mapped to the last screen page. A project that needs CPU `$4000-$5FFF` for
other data must map it back. Read `$FFA2` before the first write. Keep only
its low six bits: Sock's reference says the two high bits are not defined.

Another way to do the practice is to map four windows, for example
`$FFA2-$FFA5`, and write the screen as one 32 KiB block. Keep the windows
clear of the stack, the code and the interrupt handlers.

## See and check each mode

Open a terminal in the starter folder. Copy one line and paste it to see that
mode in XRoar. Close the window to stop it.

```sh
uv run python scripts/coco.py run examples/gime-graphics                    # 320x192, 16 colours
uv run python scripts/coco.py run examples/gime-graphics --variant g256x16  # 256x192, 16 colours
uv run python scripts/coco.py run examples/gime-graphics --variant g160x16  # 160x192, 16 colours
uv run python scripts/coco.py run examples/gime-graphics --variant g128x16  # 128x192, 16 colours
uv run python scripts/coco.py run examples/gime-graphics --variant g640x4   # 640x192, 4 colours
uv run python scripts/coco.py run examples/gime-graphics --variant g512x4   # 512x192, 4 colours
uv run python scripts/coco.py run examples/gime-graphics --variant g320x4   # 320x192, 4 colours
uv run python scripts/coco.py run examples/gime-graphics --variant g256x4   # 256x192, 4 colours
uv run python scripts/coco.py run examples/gime-graphics --variant g160x4   # 160x192, 4 colours
uv run python scripts/coco.py run examples/gime-graphics --variant g128x4   # 128x192, 4 colours
uv run python scripts/coco.py run examples/gime-graphics --variant g640x2   # 640x192, 2 colours
uv run python scripts/coco.py run examples/gime-graphics --variant g512x2   # 512x192, 2 colours
uv run python scripts/coco.py run examples/gime-graphics --variant g320x2   # 320x192, 2 colours
uv run python scripts/coco.py run examples/gime-graphics --variant g256x2   # 256x192, 2 colours
uv run python scripts/coco.py run examples/gime-graphics --variant g160x2   # 160x192, 2 colours
uv run python scripts/coco.py run examples/gime-graphics --variant g128x2   # 128x192, 2 colours
uv run python scripts/coco.py run examples/gime-graphics --variant g80x16   # 80x192, 16 colours
uv run python scripts/coco.py run examples/gime-graphics --variant g64x16   # 64x192, 16 colours
uv run python scripts/coco.py run examples/gime-graphics --variant g80x4    # 80x192, 4 colours
uv run python scripts/coco.py run examples/gime-graphics --variant g64x4    # 64x192, 4 colours
uv run python scripts/coco.py run examples/gime-graphics --variant l200     # 320x200, 16 colours
uv run python scripts/coco.py run examples/gime-graphics --variant l225     # 320x225, 16 colours
```

Add `--target coco3-1987` to see a mode on the 1987 GIME. Each mode other
than the default is a variant in [coco.toml](coco.toml). To check all
twenty-two builds on the 1986 GIME at 128 KiB, the 1987 GIME at 128 KiB and the
1986 GIME at 512 KiB, paste this line:

```sh
uv run python scripts/coco.py check examples/gime-graphics
```

The check compares the screen bytes at physical `$00000` and XRoar's rendered
picture with [expected.py](expected.py). The `[capture]` table turns on the
rendered check. Only the rendered check finds a wrong mode or palette, because
the screen bytes stay correct. `scripts/coco_spec.py` holds four negative
controls. Each one keeps the screen bytes correct and fails the rendered
check:

- a wrong palette code (`$31` in place of `$30`)
- a wrong HRES (512×4 shown as 256×4)
- a wrong LPF (225 rows shown as 200)
- a model without the 1987 GIME's later start of a short line

The check has these limits:

- The rendered capture is 512 samples wide and 192 lines high. A full-width
  line is 640 samples, so the check sees only its middle. The capture shows
  rows 2 to 193 of a 200-row screen and rows 17 to 208 of a 225-row screen.
  The screen bytes include all rows and columns.
- The capture is XRoar's composite picture, not an RGB monitor.
- On the 1987 GIME, XRoar starts a short line with HRES bit 2 set 2 samples
  later. The check models this. It is XRoar's model, not a measurement of a
  real GIME.
- The check does not prove the result on a television or a physical CoCo 3.

## Sources

Read these pages before you change a value. Use
[reference lookup](../../guidance/starter/references.md) to get them.

- Tandy, *Color Computer 3 Service Manual*:
  - PDF 11: `$FF90` bits.
  - PDF 12: `$FF98` and `$FF99` bits, and 192, 200 or 225 lines.
  - PDF 13: `$FF9D` and `$FF9E` as physical address bits 18..3.
  - PDF 15 and 16: the MMU registers. Data bits 5..0 are address bits 18..13.
  - PDF 17: the palette registers, with the RGB and composite bit meanings.
  - PDF 18: HRES and CRES of ten graphics modes.
- Laurence A. Tepolt, *Assembly Language Programming for the CoCo3* (1987):
  - PDF 29: a 128 KiB machine does not use address bits 18 and 17.
  - PDF 32: `$FF99` bits 6 and 5: 192, 200 or 225 rows.
  - PDF 38 and 39: the byte formats. The leftmost pixel is in the high bits.
    A pixel value selects a palette register. HRES bit 0 gives the full
    width.
  - PDF 41 and 42, Table 4-10: HRES and CRES of every graphics mode, format
    X, the `HSCREEN` numbers, and "Not Used" and "Blank".
- Spectral Associates, revised by Walter K. Zydhek, *Super Extended Basic
  Unravelled II* (1999). Resource `super-extended-basic-unravelled`.
  - PDF 58: the `$FF99` value of each `HSCREEN` mode, and `$80` in `$FF98`.
- John Kowalski, *Sock's GIME register reference*,
  <http://users.axess.com/twilight/sock/gime.html>
  ([Wayback Machine](http://web.archive.org/web/20211201002932/http://users.axess.com/twilight/sock/gime.html)).
  - The sixteen commonly used graphics modes.
  - The warning about odd `$FF9E` values.
  - The two high bits of an MMU read are not defined.
- XRoar 1.13.1, `src/tcc1014/tcc1014.c`: the rows for each LPF, and the top
  border and the left border of each GIME revision. This is the emulator's
  model.

These facts come only from the check, in XRoar 1.13.1:

- All twenty modes and both larger row counts show the expected picture on
  both GIME revisions. The four negative controls above fail.
- The rendered colour of each of the sixteen palette codes in
  [expected.py](expected.py).
- The first row of the capture for 200 and 225 rows, and the 1987 GIME's
  later short line. XRoar's source gives the same values.
