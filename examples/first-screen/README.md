# Set up a graphics screen

This example shows how to select each full-graphics mode of the CoCo 1/2 video
chip (VDG), how to place the screen in memory, and how to start to draw into it.
It stops when the screen is ready. It has no game loop, no input and no timing.

Use it when you start a project that draws graphics. Do not copy the folder as
the base of a project. Copy the setup steps and the mode values that you need.

## Choose a mode

The VDG has eight full-graphics modes. Four-colour modes (CG) use two bits for
each pixel. Two-colour modes (RG) use one bit for each pixel. Extended Color
BASIC gives five of the modes a `PMODE` number.

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

Think about these points before you choose:

- Four colours from one colour set apply to the full screen. The two colour
  sets are green, yellow, blue and red, or buff, cyan, magenta and orange.
- A two-colour mode shows black and one colour: green or buff.
- A small mode uses less memory and is faster to redraw. Its pixels are larger.
- CG6 is a good default for a colour game. RG6 gives the most detail.
- Pixels are not square. A CG6 pixel is almost two times as wide as it is high.
  The [graphics guide](../../guidance/techniques/graphics.md) gives the pixel
  shape of each mode.

In the leftmost pixel of a byte, the bits are the high bits: bit 7 in RG modes,
bits 7 and 6 in CG modes.

## Set up the screen

[main.asm](main.asm) does three steps. Each step is one block of the code.

1. Set the SAM display offset, F6 to F0. The value is the screen address
   divided by 512. The screen address must be a multiple of 512.
2. Set the SAM display mode, V2 to V0.
3. Set bits 7 to 3 of `$FF22`: the VDG mode in bits 7 to 4 and the colour set
   (CSS) in bit 3. Do not change bits 2 to 0. Other hardware uses them.

The SAM has no data register. Each SAM bit has two addresses. A write to the
even address clears the bit. A write to the odd address sets the bit.

The `samset` routine writes a value to a series of these bits.

The example draws the picture before it shows it. Thus the screen never shows a
half-drawn picture.

The example does not change the interrupts, the stack or the CPU clock. It keeps
the state that BASIC sets. After the setup, the program loops at `ready` to keep
the picture on the screen. A project replaces that loop with its own main loop.

## See each mode

The plain build shows CG6. Each other mode has a variant in
[coco.toml](coco.toml), named after the mode in lowercase. Each variant sets an
assembler define. Commands start in the starter folder:

```sh
uv run python scripts/coco.py run examples/first-screen
uv run python scripts/coco.py run examples/first-screen --variant rg6
```

The picture is the same in each mode: a border one pixel wide and four bars.
In CG modes, the bars are yellow, blue, red and green, with a red border.
In RG modes, the bars are two striped bars, a green bar and a black bar, with a
green border. The border width and the stripe width show the pixel size.

To check all eight modes against [expected.py](expected.py), run this command:

```sh
uv run python scripts/coco.py check examples/first-screen --video
```

The check compares the screen bytes and XRoar's rendered picture of each mode,
on the CoCo 1 target with colour set 0. It does not prove the result on a
television or on a physical CoCo.

## Sources

The program is original code. Read these pages before you change a value:

- Tandy, *Color Computer Technical Reference Manual*:
  - PDF page 11: SAM control addresses.
  - PDF page 14: the `$FF22` bits.
  - PDF page 15: SAM display offset and display mode bits for each mode.
  - PDF page 31, Table 1: the SAM and `$FF22` values for each mode.
- Motorola, *MC6847 Video Display Generator* datasheet, PDF pages 18 to 21:
  sizes, colours and the order of the pixels in a byte.
- *The Rainbow*, October 1986, PDF page 119: the `PMODE` number of each mode.

The Tandy manual gives 2K for RG2. The datasheet gives 1536 bytes. The rendered
check of RG2 passes with 1536 bytes.

Use [reference lookup](../../guidance/starter/references.md) to get those
pages. Build outputs stay in the ignored `build/first-screen/` folder.
