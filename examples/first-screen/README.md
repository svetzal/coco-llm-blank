# Set up a graphics screen

This example selects a full-graphics mode of the CoCo 1/2 video chip (VDG) and
places the screen in memory. It stops when the screen is ready. It has no game
loop, no input and no timing.

## Choose a mode

Four-colour modes (CG) use two bits for each pixel. Two-colour modes (RG) use
one bit for each pixel. Extended Color BASIC gives five modes a `PMODE` number.

| Mode | PMODE | Pixels | Colours | Bytes per row | Screen bytes | SAM V2..V0 | `$FF22` bits 7..4 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CG1 | | 64x64 | 4 | 16 | 1024 | `001` | `1000` |
| RG1 | | 128x64 | 2 | 16 | 1024 | `001` | `1001` |
| CG2 | | 128x64 | 4 | 32 | 2048 | `010` | `1010` |
| RG2 | 0 | 128x96 | 2 | 16 | 1536 | `011` | `1011` |
| CG3 | 1 | 128x96 | 4 | 32 | 3072 | `100` | `1100` |
| RG3 | 2 | 128x192 | 2 | 16 | 3072 | `101` | `1101` |
| CG6 | 3 | 128x192 | 4 | 32 | 6144 | `110` | `1110` |
| RG6 | 4 | 256x192 | 2 | 32 | 6144 | `110` | `1111` |

- One colour set applies to the full screen: green, yellow, blue and red, or
  buff, cyan, magenta and orange. A two-colour mode shows black and green, or
  black and buff.
- A small mode uses less memory and is faster to redraw. Its pixels are larger.
- CG6 is a good default for a colour game. RG6 gives the most detail.
- Pixels are not square. The [graphics guide](../../guidance/techniques/graphics.md)
  gives the shape of each mode's pixels.
- The leftmost pixel of a byte is in the high bits: bit 7 in RG modes, bits 7
  and 6 in CG modes.

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

## See and check each mode

The plain build shows CG6. Each other mode is a variant in
[coco.toml](coco.toml), named after the mode in lowercase:

```sh
uv run python scripts/coco.py run examples/first-screen --variant rg6
uv run python scripts/coco.py check examples/first-screen --video
```

The check compares the screen bytes and XRoar's rendered picture of all eight
modes with [expected.py](expected.py), on the CoCo 1 target with colour set 0.
It does not prove the result on a television or a physical CoCo.

## Sources

Read these pages before you change a value. Use
[reference lookup](../../guidance/starter/references.md) to get them.

- Tandy, *Color Computer Technical Reference Manual*: PDF page 11 (SAM
  control), 14 (`$FF22` bits), 15 (SAM bits for each mode) and 31, Table 1
  (SAM and `$FF22` values for each mode).
- Motorola, *MC6847 Video Display Generator* datasheet, PDF pages 18 to 21:
  sizes, colours and the order of the pixels in a byte.
- *The Rainbow*, October 1986, PDF page 119: the `PMODE` number of each mode.

The Tandy manual gives 2K for RG2. The datasheet gives 1536 bytes. The rendered
check of RG2 passes with 1536 bytes.
