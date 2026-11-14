# Design colours for the display

Read this when a recreation has the right shapes but the wrong colours,
or when choosing a palette for a new game. Record the display path as part
of the target. Pixel memory does not by itself describe the final appearance.

## CoCo 2 artifact colours

Tandy's **Color Computer 2 NTSC Service Manual**, models 26-3134 and 26-3136,
explains video generation and artifact circuitry on printed/PDF 31–33.
The discussion connects colour appearance with the colour burst and its phase.
[Tandy, PDF 31–33][coco2]

This is a useful source when bitmap bytes match but colours differ.
Its scope is the named NTSC boards. It does not establish the appearance of
every CoCo 2 revision, CoCo 1, PAL output, or another display connection.
Do not silently extend its conclusions to those targets.

## CoCo 3 palette meanings

Tandy's **Color Computer 3 Service Manual**, printed/PDF 17, separates RGB
palette bit meanings from composite meanings. It also gives a PAL caveat.
Read the appropriate table for the actual display. [Tandy, PDF 17][coco3]

Check the page image when selecting values. Converted text can merge table
labels. A value chosen for one display path is not a promise of the same
visible colour on another.

Tepolt's advanced graphics discussion also describes colour blending.
Treat the resulting appearance as display-dependent. Do not count it as extra
independently addressable palette entries. [Tepolt, PDF 59][tepolt]

## Make a display test before making the art

This procedure is our proposed validation method. We have not tested it
as part of this research.

1. Record the machine revision, video standard, connection, and emulator settings.
2. Make an asymmetric pattern with isolated pixels and alternating pixel pairs.
3. Include labelled colour swatches for the selected mode and palette.
4. Check the bitmap and palette values independently of the displayed image.
5. Inspect the running display and record the observed colours.
6. Repeat for each display path the project promises to support.

The asymmetric pattern helps expose phase or orientation differences.
The swatches provide a reference when drawing later assets. These are reasons
for the proposed test, not observations from a completed experiment.

If physical hardware is a target, repeat the test on that hardware.
An emulator screenshot establishes only that emulator configuration's output.
A RAM snapshot establishes the stored values, not their visible colour.

## Sources and provenance

- Tandy, *Color Computer 2 NTSC Service Manual (26-3134 & 26-3136)*,
  printed/PDF 31–33. Resource `coco2-service`. [Archive][coco2]
- Tandy, *Color Computer 3 Service Manual*, printed/PDF 17.
  Resource `coco3-service`. [Archive][coco3]
- Laurence A. Tepolt, *Assembly Language Programming for the CoCo3* (1987),
  PDF 59. Resource `tepolt-coco3`. [Archive][tepolt]

These source pages were examined as images. We have not compared colours across
physical displays. The
[research notes](../guidance/game-research.md#coco-2-display-differences)
record the narrower board scope and conversion limitations.

[coco2]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%202%20NTSC%20Service%20Manual%20(26-3134%20&%2026-3136)%20(Tandy).pdf#page=31>

[coco3]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%203%20Service%20Manual%20(Tandy).pdf#page=17>

[tepolt]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20(1987)%20(Laurence%20A%20Tepolt).pdf#page=59>
