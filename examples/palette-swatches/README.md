# Palette swatches

This original example shows every colour of the VDG full-graphics modes as bars.
It is the evidence for the `xroar` palette in `scripts/graphics.py`. It is not a
game.

Ask your agent to run these steps. Commands start in the project folder:

```sh
sh scripts/bootstrap.sh coco1
uv run python scripts/coco.py check examples/palette-swatches --video
uv run python scripts/coco.py run examples/palette-swatches
uv run python scripts/coco.py run examples/palette-swatches --variant css1
```

The `run` commands open XRoar. Close the window to stop it.

## What the screen shows

The program draws the same 6144 screen bytes in four builds:

| Build | Mode | Colour set | Bars from the left |
| --- | --- | --- | --- |
| main | CG6, 128x192, four colours | CSS=0 | green, yellow, blue, red |
| `css1` | CG6 | CSS=1 | buff, cyan, magenta, orange |
| `rg6` | RG6, 256x192, two colours | CSS=0 | black, stripes, stripes, green |
| `rg6-css1` | RG6 | CSS=1 | black, stripes, stripes, buff |

Rows 0 to 159 hold four bars. Each bar is 8 bytes wide: `$00`, `$55`, `$AA` and
`$FF`. In CG6, each pair of bits is one pixel, so each bar is one colour code.

Rows 160 to 191 hold `$1B` in every byte. In CG6 that is codes 0, 1, 2 and 3
from the left. This band shows the order of pixels inside a byte.

## What the check proves

`check --video` assembles all four builds and runs them in XRoar. For each build
it compares:

- All 6144 screen bytes with `expected_screen` in [expected.py](expected.py).
- All 512x192 samples of XRoar's rendered frame with `expected_frame`.

`expected_frame` uses `unpack` and `render` from `scripts/graphics.py` with the
`xroar` palette. So the check tests three things against XRoar's renderer: the
palette values, the bit order inside a byte, and the pixel sizes. CG6 pixels
are 4 samples wide and RG6 pixels are 2 samples wide.

The spec, [palette_swatches_spec.py](palette_swatches_spec.py), has negative
controls. Each of these frames must fail the rendered comparison:

- A frame for the other colour set.
- A frame for the other mode.
- A frame with yellow and blue swapped.

A manual test made each of these changes to `expected.py`:

- Use the wrong colour set.
- Swap yellow and blue.
- Reverse the pixel order inside each byte.

The real `check --video` run failed each time. That manual test is not
automated.

## Palette values and their limits

The values were measured from these captures. XRoar 1.12.1 was built with this
starter's instrumented patch series. `scripts/coco.py` captures with S-video
colours, cross-colour off, and the active area only (`-tv-input svideo -ccr none`).
The machine is `cocous`, NTSC, with a 6847 VDG.

| Colour | RGB |
| --- | --- |
| green | 46, 188, 36 |
| yellow | 255, 255, 151 |
| blue | 44, 37, 129 |
| red | 131, 26, 55 |
| buff | 255, 255, 255 |
| cyan | 46, 173, 115 |
| magenta | 255, 90, 255 |
| orange | 255, 112, 59 |
| black with CSS=0 | 0, 31, 0 |
| black with CSS=1 | 13, 13, 13 |

XRoar shows two-colour "black" differently for each colour set.

These values are one emulator path. They are not measurements of a television,
a monitor or a physical CoCo. Other XRoar settings, such as composite video
with artifact colours, give different colours.

The capture shows only the active area. The border colour (green with CSS=0,
buff with CSS=1) is not in the capture, so this example does not measure it.
Use the `run` window to look at the border.

## Target and memory

The target is a CoCo 1 with 32 KiB RAM, NTSC video and a stock-clock 6809. It
uses the same memory layout as [first-screen](../first-screen/README.md).

| Purpose | Address range |
| --- | --- |
| Screen | $0400-$1BFF |
| Ready marker | $2FFF |
| Program | Starts at $3000 |
| Reserved stack | $7E00-$7EFF. Starts at $7F00 and grows down. |

## Check the sources before adapting it

The program is original code. Its hardware facts were checked against:

- Motorola, *MC6847/MC6847Y Video Display Generator* datasheet. PDF page 20:
  CG6 and RG6 sizes and pixel sizes. PDF page 19 Table 3 and PDF page 21
  Figure 22: one bit per pixel in RG6 and one pair of bits per pixel in CG6,
  leftmost pixel in the high bits. PDF page 21: the colour of each code for each
  colour set.

- Tandy, *Color Computer Technical Reference Manual*, PDF page 31 Table 1: CG6
  and RG6 use SAM V2..V0 = 110.
  `$FF22` bits 7 to 4 are 1110 for CG6 and 1111 for RG6. Bit 3 is CSS.
  The program keeps bits 2 to 0.
  PDF pages 14 and 15: the PIA data register and the SAM display offset, as in
  first-screen.

Use [reference lookup](../../guidance/starter/references.md) to get those pages.
No book pages, converted text or firmware are in this folder. Build outputs and
captures stay in ignored `build/palette-swatches/`.
