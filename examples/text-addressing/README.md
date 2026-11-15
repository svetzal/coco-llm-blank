# Set up a CoCo 3 text screen

This example selects a high-resolution text mode of the CoCo 3 video chip
(GIME). It puts the screen at a physical address that you choose.

The CPU writes the screen through an MMU page. The GIME shows it from the
display address.

Both values come from the same physical address. Thus the program works on
128 KiB and 512 KiB machines.

The example stops when the GIME shows the screen. It has no game loop, no
input, no scrolling and no return to BASIC. It does not print with BASIC ROM
calls.

## Choose a width

All four widths have 24 rows of eight scan lines. Each character uses two
bytes: the character code, then the attribute.

| Columns | `$FF99` | HRES2..0 | Bytes per row | Screen bytes | Image |
| --- | --- | --- | --- | --- | --- |
| 32 | `$01` | `000` | 64 | 1536 | Centred, with a border on all sides |
| 40 | `$05` | `001` | 80 | 1920 | Full width, border at top and bottom |
| 64 | `$11` | `100` | 128 | 3072 | Centred, with a border on all sides |
| 80 | `$15` | `101` | 160 | 3840 | Full width, border at top and bottom |

- 40 columns is the default. Its characters are easy to read on a television,
  and it has more columns than 32.
- 64 and 80 columns have smaller characters. They are hard to read on a
  television. Use them for an RGB or composite monitor.
- `$FF99` bit 0 (CRES0) is 1. This gives each character an attribute byte.
- More rows are available: 25 or 28 (`$FF99` bits 6 and 5). This example
  uses 24.

The attribute byte has these bits:

| Bit | 7 | 6 | 5..3 | 2..0 |
| --- | --- | --- | --- | --- |
| Use | Blink | Underline | Foreground: palette 8-15 | Background: palette 0-7 |

### Choose the physical address

The CPU sees 64 KiB. The GIME reads physical memory directly. Calculate these
values from one physical address `A`:

| Value | Calculation | `A = $0C000` |
| --- | --- | --- |
| MMU page for the CPU window | `A / $2000` | `$06` |
| `$FF9D`, address bits 18..11 | `A / $800` | `$18` |
| `$FF9E`, address bits 10..3 | `(A / 8) AND $FF` | `$00` |
| CPU address of the screen | window + `(A AND $1FFF)` | `$4000` |

- `A` must be a multiple of 8. The screen must not cross an 8 KiB page.

- A 128 KiB CoCo 3 does not use address bits 18 and 17. Thus `$0C000`,
  `$2C000`, `$4C000` and `$6C000` are the same RAM on 128 KiB. They are
  different RAM on 512 KiB.

- Do not mix the two forms of one address. An MMU page of `$36` with a
  `$FF9D` of `$18` works on 128 KiB and fails on 512 KiB. The
  [scrolling guide](../../guidance/techniques/scrolling.md#understand-the-512k-correction)
  explains a published program that had this error.

- An address below `$20000` is the same RAM on both sizes. The example uses
  `$0C000`. On 128 KiB, this is also the RAM of BASIC's own text screen at
  `$6C000`.

## Set up the screen

The example is the three `>>> EXAMPLE` parts of [main.asm](main.asm). The other
code is context: it fills the screen with a test card and holds it at the
`ready` label. A project replaces that loop with its own main loop.

1. The values for each width and the address values from the table above.
   One assembler define selects the width. The labels are `COLS`, `RES`,
   `SCREEN`, `PAGE`, `BASEHI`, `BASELO`, `WINDOW` and `CPUSCR`.

2. The CPU window. Write `PAGE` to `$FFA2`. CPU `$4000-$5FFF` then shows the
   screen page. The window stays mapped. The program can write the screen at
   `CPUSCR` at any time.

3. The display setup. It starts at the palette writes:

   1. Set the palette entries that the attributes use: 0 black (`$00`), 1 white
      (`$3F`) and 8 white.

   2. Write `$4E` to `$FF90`. This selects native mode, the MMU on, no GIME
      interrupt outputs, constant RAM at `$FExx`, standard SCS and 32 KiB
      internal ROM.

   3. Write `$03` to `$FF98`: text (BP=0), eight lines for each row.

   4. Write `RES` to `$FF99`.

   5. Write 0 to `$FF9C`: no vertical scroll.

   6. Write `BASEHI` to `$FF9D` and `BASELO` to `$FF9E`.

   7. Write 0 to `$FF9F`: a normal buffer width and no horizontal offset.

The example does not read back the GIME registers. It writes each display
register that the mode uses, with all eight bits.

The test card puts a space (code 32) in each cell. The border cells and the
cells where the column equals the row have a white background. The other cells
have a black background.

A project writes its own character codes. Codes 32 to 127 are the ASCII
characters.

The example does not change the interrupts, the stack, the direct page, the
CPU clock or `$FF91`. It keeps the MMU task that BASIC uses. The check shows
that the writes through `$FFA2` reach the screen.

Another way to do the practice is to map the screen page into a different CPU
window. Keep the window clear of the stack, the code and the interrupt
handlers.

## See and check each width

Open a terminal in the starter folder. Copy one line and paste it to see that
width in XRoar. Close the window to stop it.

```sh
uv run python scripts/coco.py run examples/text-addressing                # 40 columns
uv run python scripts/coco.py run examples/text-addressing --variant c32  # 32 columns
uv run python scripts/coco.py run examples/text-addressing --variant c64  # 64 columns
uv run python scripts/coco.py run examples/text-addressing --variant c80  # 80 columns
```

Each width other than 40 columns is a variant in [coco.toml](coco.toml). To
check all four widths on 128 KiB and on 512 KiB, paste this line:

```sh
uv run python scripts/coco.py check examples/text-addressing
```

The check compares the screen bytes at physical `$0C000` and XRoar's rendered
picture with [expected.py](expected.py). The `[capture]` table turns on the
rendered check. A check on both RAM sizes finds the address errors that the
128 KiB alias hides:

- A wrong MMU page puts the screen bytes in other RAM on 512 KiB.
- A wrong `$FF9D` shows other RAM on 512 KiB. Only the rendered check sees
  this error, because the screen bytes are correct.

`scripts/coco_spec.py` holds both errors as negative controls.

The check has these limits:

- The rendered capture is 512 samples wide. A 40 or 80 column line is 640
  samples wide, so the check sees only its middle. The screen bytes include
  all columns.
- The test card has only spaces. The check does not compare the shapes of
  the characters.
- The check uses XRoar with GIME 1986. It does not prove the result for GIME
  1987, a television or a physical CoCo 3.

## Sources

Read these pages before you change a value. Use
[reference lookup](../../guidance/starter/references.md) to get them.

- Tandy, *Color Computer 3 Service Manual*:
  - PDF 11: `$FF90` bits.
  - PDF 12: `$FF98` and `$FF99` bits, lines for each row and rows.
  - PDF 13: `$FF9C`, and `$FF9D` and `$FF9E` as physical address bits 18..3.
  - PDF 15 and 16: the MMU registers `$FFA0-$FFAF`. Data bits 5..0 are
    address bits 18..13.
  - PDF 17: the palette registers. `$00` is black and `$3F` is white (RGB).
  - PDF 18: HRES and CRES for 32, 40 and 80 characters.
- Laurence A. Tepolt, *Assembly Language Programming for the CoCo3* (1987):
  - PDF 29: a 128 KiB machine does not use address bits 18 and 17.
  - PDF 31: the buffer is rows of character pairs from the upper left.
  - PDF 32 and 33: `$FF99` rows, `$FF9C` scroll and the eight-byte display
    start.
  - PDF 34 and 35: `$FF9F`, the character and attribute bytes, the attribute
    bits and the readability of each width.
  - PDF 36, Table 4-8: HRES, CRES and buffer size for 32, 40, 64 and 80
    columns.
  - PDF 58: BASIC's text screen at physical `$6C000`.

The service manual does not list 64 columns. Tepolt does. The check of the
`c64` variant passes in XRoar with GIME 1986.
