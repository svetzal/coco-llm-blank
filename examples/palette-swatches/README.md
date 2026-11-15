# Select a colour set

This example selects one of the two colour sets of the CoCo 1/2 video chip
(VDG) in a full-graphics mode. It shows a bar of each colour code, so you can
see which colour each code gives. It stops when the picture is on the screen.

The same program runs on a CoCo 1, a CoCo 2 and a CoCo 3. The CoCo 3 shows
these modes with its VDG-compatible modes. On a CoCo 3, each colour code
selects a palette register. Thus the RGB values on a CoCo 3 are different.
[Machines](#machines) tells what is different.

The example does not select other graphics modes or place the screen in
memory. [First-screen](../first-screen/README.md) shows those steps. It does
not change colours while the program runs, and it does not use artifact
colours. It does not write the CoCo 3 palette registers.

This example is also the evidence for the `xroar` and `xroar-coco3` palettes
in `scripts/graphics.py`. The check compares every rendered sample with one of
these palettes.

## Choose a colour set

`$FF22` bit 3 is the colour-set select (CSS). One colour set applies to the
full screen and to the border. The mode sets how many bits each pixel has.

| Variant | Mode | CSS | `$FF22` bits 7..3 | Code 0 | Code 1 | Code 2 | Code 3 | Border |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| (none) | CG6, PMODE 3 | 0 | `11100` | green | yellow | blue | red | green |
| `css1` | CG6, PMODE 3 | 1 | `11101` | buff | cyan | magenta | orange | buff |
| `rg6` | RG6, PMODE 4 | 0 | `11110` | black | green | | | green |
| `rg6-css1` | RG6, PMODE 4 | 1 | `11111` | black | buff | | | buff |

- In a four-colour (CG) mode, each pixel has two bits. It is one code from 0
  to 3.
- In a two-colour (RG) mode, each pixel has one bit. A 0 is black. A 1 is the
  one colour of the set.
- A picture can use only the colours of one set.
- The default is CG6 with CSS=0. The other examples use this colour set, so
  their colours agree with this table.

The datasheet gives the colour names, not RGB values. These are the RGB values
of the `xroar` palette (CoCo 1 and 2) and the `xroar-coco3` palette (CoCo 3).
They are measured in XRoar. The check compares them with XRoar's rendered
frame.

| Colour | RGB, CoCo 1 and 2 | RGB, CoCo 3 | CoCo 3 register and BASIC code |
| --- | --- | --- | --- |
| green | 46, 188, 36 | 71, 145, 5 | 0 and 9: `$12` |
| yellow | 255, 255, 151 | 255, 200, 46 | 1: `$24` |
| blue | 44, 37, 129 | 34, 28, 222 | 2: `$0B` |
| red | 131, 26, 55 | 155, 18, 60 | 3: `$07` |
| buff | 255, 255, 255 | 255, 255, 255 | 4 and 11: `$3F` |
| cyan | 46, 173, 115 | 25, 161, 33 | 5: `$1F` |
| magenta | 255, 90, 255 | 106, 17, 181 | 6: `$09` |
| orange | 255, 112, 59 | 255, 157, 151 | 7: `$26` |
| black with CSS=0 | 0, 31, 0 | 20, 20, 20 | 8: `$00` |
| black with CSS=1 | 13, 13, 13 | 20, 20, 20 | 10: `$00` |

On the CoCo 1 and 2, XRoar shows RG "black" with a small tint for each colour
set. On the CoCo 3, XRoar shows the same grey for both. These values are one
emulator path. They are not the colours of a television, a monitor or a
physical CoCo. Composite video with artifact colours gives other colours.

## Machines

The program, the screen bytes and the picture are the same on each machine.
Only the RGB values are different.

- CoCo 1 and CoCo 2: the MC6847 gives each code a fixed colour.
- CoCo 3: the `$FF22` and SAM values select the same G6C (CG6) and G6R (RG6)
  modes. A CG code selects palette register 0 to 3 with CSS=0, or 4 to 7 with
  CSS=1. An RG bit selects register 8 or 9 with CSS=0, or 10 or 11 with
  CSS=1. BASIC loads the registers at reset (Tepolt PDF 46 and 57).

The CoCo 3 needs no other setup. The program keeps the palette registers that
BASIC loads. If a program writes `$FFB0` to `$FFBB`, the colours change, and
the `xroar-coco3` palette does not apply.

The CoCo 3 service manual (PDF 17) gives other codes "for CoCo compatibility".
Its yellow, red, cyan and magenta codes are not the codes that BASIC loads.
XRoar reads back the codes that Tepolt gives. In XRoar, the captured frame on
the CoCo 3 has the same size and position as on the CoCo 1 and 2.

The [graphics guide](../../guidance/techniques/graphics.md#know-the-colours)
gives the colour table. The [colour guide](../../guidance/techniques/colour.md)
tells how to design art for these colours.

## Select the colour set

The example is the two `>>> EXAMPLE` parts of [main.asm](main.asm):

1. The `CSS` and `VDG` values. The `CSS1` define sets `CSS` to `%00001000`.
   The `RG6` define sets `VDG` to `%11110000` in place of `%11100000`.
2. The write to `$FF22`. Read `$FF22`, keep bits 2 to 0, then set bits 7 to 3
   to `VDG+CSS`. Other hardware uses bits 2 to 0.

The `--- CONTEXT` blocks are not part of the practice:

- They draw the picture. Rows 0 to 159 hold four bars of bytes `$00`, `$55`,
  `$AA` and `$FF`. In CG6, each bar is one code: 0, 1, 2 and 3 from the left.

- Rows 160 to 191 hold `$1B` in each byte. In CG6, that shows codes 0, 1, 2
  and 3 from the left in each byte. This band shows that the leftmost pixel is
  in the high bits.

- They set the SAM display offset and mode for a screen at `$0400`, as in
  first-screen.
- They hold the picture at the `ready` label. A project replaces this loop
  with its own main loop.

The program keeps the interrupts, stack, direct page and CPU clock that BASIC
sets.

## See and check each colour set

Open a terminal in the starter folder. Copy one line and paste it to see that
colour set in XRoar. Close the window to stop it.

```sh
uv run python scripts/coco.py run examples/palette-swatches                       # CG6, CSS=0
uv run python scripts/coco.py run examples/palette-swatches --variant css1        # CG6, CSS=1
uv run python scripts/coco.py run examples/palette-swatches --variant rg6         # RG6, CSS=0
uv run python scripts/coco.py run examples/palette-swatches --variant rg6-css1    # RG6, CSS=1
```

To see a colour set on the CoCo 3, add `--target coco3`:

```sh
uv run python scripts/coco.py run examples/palette-swatches --target coco3                      # CG6, CSS=0
uv run python scripts/coco.py run examples/palette-swatches --target coco3 --variant css1       # CG6, CSS=1
uv run python scripts/coco.py run examples/palette-swatches --target coco3 --variant rg6        # RG6, CSS=0
uv run python scripts/coco.py run examples/palette-swatches --target coco3 --variant rg6-css1   # RG6, CSS=1
```

Look at the border in the `run` window. The check does not capture the border.

To check all four variants on all three machines, paste this line:

```sh
uv run python scripts/coco.py check examples/palette-swatches --video
```

The `--video` option needs the
[instrumented XRoar](../../guidance/starter/toolchain.md#instrumented-xroar).
The colour set is not in screen memory. Without `--video`, the check cannot
find a wrong colour set.

The check runs each variant on three targets in [coco.toml](coco.toml). Each
target has NTSC and a normal-clock 6809:

- `coco1`: a CoCo 1 with Color BASIC 1.1, 32 KiB and the non-T1 MC6847.
- `coco2`: a CoCo 2 with Color BASIC 1.2, 32 KiB and the non-T1 MC6847.
  XRoar's `coco2bus` profile has a T1 VDG, so this target uses `cocous` with
  an explicit `6847`.
- `coco3`: a CoCo 3 with Super Extended Color BASIC, 128 KiB and the 1986
  GIME.

For each variant, the check compares these with [expected.py](expected.py):

- All 6144 screen bytes.
- All 512x192 samples of XRoar's rendered frame.

The model draws the frame with the `unpack` and `render` functions of
`scripts/graphics.py`. It uses the `xroar` palette on `coco1` and `coco2`, and
the `xroar-coco3` palette on `coco3`. Thus the check tests these items:

- The palette values.
- The pixel order in a byte.
- The pixel sizes. A CG6 pixel is 4 samples wide. An RG6 pixel is 2 samples
  wide.

The picture is not symmetric. A mirrored, upside-down or shifted frame does
not match it.

The capture uses S-video colours with cross-colour off, and the active area
only. It does not prove the result on a television, an RGB monitor, a
physical CoCo, PAL or the MC6847T1.

## Sources

Read these pages before you change a value. Use
[reference lookup](../../guidance/starter/references.md) to get them.

- Motorola, *MC6847 Video Display Generator* datasheet:
  - PDF page 20: CG6 is 128x192 with four colours, and RG6 is 256x192 with
    two colours. Both use 6K bytes. CSS selects the colour set and the border
    colour.
  - PDF page 21, Figure 22(c): the colour of each code for each colour set.
  - PDF page 19, Table 3: the leftmost pixel is in the high bits of a byte.
- Tandy, *Color Computer Technical Reference Manual*:
  - PDF page 14: `$FF22` bit 3 is CSS. Bits 4 to 7 are GM0, GM1, GM2 and A/G.
  - PDF page 31, Table 1: CG6 and RG6 use SAM V2..V0 = `110`, and `$FF22`
    bits 7 to 4 are `1110` and `1111`. Do not change bits 2 to 0.
  - PDF pages 11 and 15: the SAM display offset and mode bits.
- Laurence A. Tepolt, *Assembly Language Programming for the CoCo3*:
  - PDF page 46: on a CoCo 3, the same `$FF22` and SAM values select G6C and
    G6R. Each code selects a palette register. CSS selects the registers and
    the border.
  - PDF page 57, step 44: the values that BASIC loads into palette registers
    0 to 15 at reset.
  - PDF page 20, Table 2-1: palette registers 0 to 15 are at `$FFB0` to
    `$FFBF`.
- Tandy, *Color Computer 3 Service Manual*:
  - PDF page 17: the palette registers have 6 bits. This page gives other
    codes "for CoCo compatibility". BASIC does not load them.
