# Draw in the VDG graphics modes

Read this before you choose a graphics mode for a CoCo 1 or CoCo 2 project.
Read it also before you turn artwork into screen bytes.

This guide covers the eight full-graphics modes of the MC6847 video chip (VDG).
For these modes, it covers:

- size
- colours
- how pixels pack into bytes
- pixel shape

It also covers `scripts/graphics.py`, the tool that converts images into those
bytes.

Other guides cover the next steps:

- [Colour](colour.md): how colours look on a given display, and artifact
  colours.
- [Assets](assets.md): picture IDs, descriptors, where the bytes live, and
  conversion at each build.
- [Moving objects](moving-objects.md): how to draw pictures over scenery.

CoCo 3 GIME modes are not in this guide, and the tool rejects them.

## Choose a mode

The VDG has eight full-graphics modes. Colour modes (CG) use two bits for each
pixel and show four colours. Resolution modes (RG) use one bit for each pixel
and show two colours. [Motorola, PDF 18 Table 2 and PDF 20][mc6847-modes]

| Mode | Pixels | Colours | Bytes per row | Bytes | Pixel size |
| --- | --- | --- | --- | --- | --- |
| CG1 | 64x64 | 4 | 16 | 1024 | 4 half-clocks x 3 lines |
| RG1 | 128x64 | 2 | 16 | 1024 | 2 x 3 |
| CG2 | 128x64 | 4 | 32 | 2048 | 2 x 3 |
| RG2 | 128x96 | 2 | 16 | 1536 | 2 x 2 |
| CG3 | 128x96 | 4 | 32 | 3072 | 2 x 2 |
| RG3 | 128x192 | 2 | 16 | 3072 | 2 x 1 |
| CG6 | 128x192 | 4 | 32 | 6144 | 2 x 1 |
| RG6 | 256x192 | 2 | 32 | 6144 | 1 x 1 |

Run `uv run python scripts/graphics.py modes` to print this table.

For most games, select CG6 for colour or RG6 for detail. Both use 6144 bytes.
The smaller modes use less memory and are faster to redraw, but their pixels
are larger.

Select the mode before you draw any art. A change of mode changes the pixel
grid, the colours and the pixel shape.

The Tandy Technical Reference Manual gives 2K for RG2.
The datasheet gives 1.5K. The tool uses 1536 bytes from the datasheet.
The rendered check of RG2 in [first-screen](../../examples/first-screen/README.md)
passes with 1536 bytes in XRoar. [Tandy, PDF 30][coco-modes]

To set the mode, write the SAM display bits and the PIA bits at `$FF22`.
[Tandy, PDF 31 Table 1][coco-modes]

- SAM bits V2 to V0: `110` for CG6 and RG6.
- `$FF22` bits 7 to 4: `1110` for CG6, `1111` for RG6.
- `$FF22` bit 3: the colour-set select (CSS).

[First-screen](../../examples/first-screen/README.md) sets up each of the eight
modes and gives the values for each mode. Copy the setup steps from it.

## Know the colours

The CSS bit selects one of two colour sets for the whole screen.
[Motorola, PDF 21][mc6847-colours]

| Code | CG modes, CSS=0 | CG modes, CSS=1 | RG modes, CSS=0 | RG modes, CSS=1 |
| --- | --- | --- | --- | --- |
| 00 or 0 | green | buff | black | black |
| 01 or 1 | yellow | cyan | green | buff |
| 10 | blue | magenta | | |
| 11 | red | orange | | |

CSS=0 gives a green border and CSS=1 gives a buff border. A picture can only
use the four colours (or two) of one set.

The datasheet names the colours, but it does not give RGB values. We
measured the tool's `xroar` palette from the instrumented XRoar's rendered
frame.

[Palette swatches](../../examples/palette-swatches/README.md) is the
evidence: its `check --video` compares every rendered sample with the palette.
Run `uv run python scripts/graphics.py palettes` to see the values.

These values apply to one emulator path: S-video input, with no composite
artifact decoding. They are not the colours of a real television.

XRoar shows RG "black" with a small tint of the colour set: dark green when
CSS=0 and dark grey when CSS=1. The palette stores each black separately.

## Know the pixel order

In RG modes, bit 7 of a byte is the leftmost pixel. In CG modes, bits 7 and 6
are the leftmost pixel.
[Motorola, PDF 19 Table 3 and PDF 21 Figure 22][mc6847-order]

The `$1B` band in palette-swatches shows this. In CG6 it shows green, yellow,
blue and red from the left. If you reverse the bit order, the rendered check
fails.

## Correct for pixel shape

CoCo pixels are not square, and the shape changes with the mode. A circle
drawn with square pixels looks like an oval on the CoCo. The tool corrects
for this when it resizes an image.

These facts come from the datasheet:

- One pixel is a number of half-clocks wide and a number of scan lines high
  (the table above). [Motorola, PDF 20][mc6847-modes]
- The clock is 3.579545 MHz. [Motorola, PDF 13][mc6847-clock]
- One scan line is 227.5 clocks. [Motorola, PDF 8 Figure 8][mc6847-sync]

The tool's `ntsc` display setting adds one assumption that is not from our
sources. The assumption is that a square pixel on a 4:3 NTSC picture of about
240 lines is about 6.136 MHz. From that, one half-clock is about 6/7 of a line
height.

- An RG6 pixel is 6:7, a little narrow.
- A CG6 pixel is about 12:7, almost twice as wide as it is high.

This is a deduction. Nobody has measured it on a television.

The `square` setting treats one half-clock as one line height. Use it to match
XRoar's capture layout. `ntsc` is the default.

## Convert an image

Run `uv run python scripts/graphics.py --help`. Then run the help of the
command you need. Do not read the source. The commands are:

- `convert`: one image to one screen or one sprite.
- `sheet`: a sprite sheet to one labelled block for each cell.
- `render`: packed bytes back to a PNG.

The conversion does these steps in this sequence:

1. Crop the source (`--box`) and fit it to the target's displayed shape.
2. Resize to the mode's pixel grid, with correction for pixel shape.
3. Find the nearest colour in the colour set (CIELAB distance).
4. Dither, if you ask for it (`--dither bayer` or `floyd-steinberg`).
5. Pack the pixels into bytes.

The outputs are:

- `PREFIX.bin`: the packed bytes.
- `PREFIX.asm`: an lwasm include of `fcb` rows with a label.
- `PREFIX.png`: a preview. The tool draws it from the packed bytes, so the
  preview also shows that the packing is correct.
- `PREFIX-mask.bin`: a mask, with `--mask`. Draw with
  `(screen AND mask) OR picture`, as in
  [masked objects](../../examples/masked-objects/README.md).

Look at the preview before you use the bytes. Then show the result in XRoar.
To convert the art at each build, read
[assets](assets.md#convert-the-pictures-at-each-build).

### Get good results

- Use `--resample nearest` for pixel art. Use `lanczos` for illustrations.
- For pixel art with one source pixel for each mode pixel, also use
  `--fit stretch`. The default `--fit crop` corrects for pixel shape, so it
  removes columns and changes the bytes.
- Do not dither flat art. Dithering scatters noise across a background that is
  near, but not equal to, a palette colour.
- Use `--auto-css` to let the tool select the colour set with less error.
- Make the art at the size you need. A large picture that the tool shrinks
  loses thin lines.
- A sprite's width must be a full number of bytes: 4 pixels for CG, 8 for RG.
  Use `--pad` to add blank pixels.
- For many sprites in one image, use `sheet` with equal cells and no gaps.

## Use generated concept art

An image generator can make concept art quickly. The same rules apply as for
any other art:

1. Ask for flat colour, large shapes, thick outlines and no text.
2. Name the four colours of the selected colour set in the request.
3. Ask for a solid background in one of those colours. Then the background
   converts cleanly.
4. Ask for the target shape, with correction for pixel shape. For a full CG6
   screen, a 128x192 grid of pixels at about 12:7 displays at about 4:3.
5. Convert the image. Look at the preview. Correct pixels by hand when
   necessary.

Do not let a generator draw words, numbers or scores. Draw those from data in
the program. Keep the source image and the conversion command in the project,
so that the conversion gives the same bytes again.

The starter does not call an image service. If the owner uses one, they
supply its account and key.

## Know what is verified

- Mode sizes, colour sets, bit order and the clock come from the datasheet.
  We read them from the page images.
- We measured the `xroar` palette in CG6 and RG6, for both colour sets, on
  the CoCo 1 target and the non-T1 CoCo 2 target. The rendered check fails
  for each negative control. The controls are a changed colour set, two exchanged colours, a
  reversed bit order, a mirrored or shifted picture and a wrong SAM mode.
- The [display test](colour.md#make-a-display-test-before-making-the-art)
  lists those controls and their limits.
- [Tile-room](../../examples/tile-room/README.md) converts its pictures with
  `sheet` at each build. Its check compares 42 rendered frames on CoCo 1 and
  CoCo 2 with text drawings.
- First-screen's rendered check passes for all eight modes on the CoCo 1
  target with colour set 0.
- We did not measure the border colour, colour set 1 outside CG6 and RG6, a T1
  VDG or other XRoar video paths in a capture.
- The `ntsc` pixel shape is a deduction. Nobody has tuned the dither settings.
- Nobody has checked a colour or a shape on real hardware or a television.

## Sources

- Motorola, *MC6847/MC6847Y Video Display Generator*, 1984, DS9823-R1, PDF 8,
  13, 18–21. Resource `mc6847`.
- Tandy, *Color Computer Technical Reference Manual*, PDF 30–31. Resource
  `coco1-technical`.

[mc6847-modes]: <https://colorcomputerarchive.com/repo/Documents/Datasheets/MC6847%20MOS%20Video%20Display%20Generator%20(Motorola).pdf#page=18>
[mc6847-colours]: <https://colorcomputerarchive.com/repo/Documents/Datasheets/MC6847%20MOS%20Video%20Display%20Generator%20(Motorola).pdf#page=21>
[mc6847-order]: <https://colorcomputerarchive.com/repo/Documents/Datasheets/MC6847%20MOS%20Video%20Display%20Generator%20(Motorola).pdf#page=19>
[mc6847-clock]: <https://colorcomputerarchive.com/repo/Documents/Datasheets/MC6847%20MOS%20Video%20Display%20Generator%20(Motorola).pdf#page=13>
[mc6847-sync]: <https://colorcomputerarchive.com/repo/Documents/Datasheets/MC6847%20MOS%20Video%20Display%20Generator%20(Motorola).pdf#page=8>
[coco-modes]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%20Technical%20Reference%20Manual%20%28Tandy%29.pdf#page=31>
