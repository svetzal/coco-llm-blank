# Design colours for the display

Read this when a recreation has the right shapes but the wrong colours.
Read it also when you choose a palette for a new game.
Record the display path as part of the target.
Pixel memory does not by itself describe the final appearance.

## CoCo 2 artifact colours

Tandy's **Color Computer 2 NTSC Service Manual**, models 26-3134 and 26-3136,
explains video generation and artifact circuitry on printed/PDF 31–33.
The discussion connects colour appearance with the colour burst and its phase.
[Tandy, PDF 31–33][coco2]

This is a useful source when bitmap bytes match but colours differ.
Its scope is the named NTSC boards.
It does not establish the appearance of every CoCo 2 revision, CoCo 1, PAL
output, or another display connection.
Do not silently extend its conclusions to those targets.

## CoCo 3 palette meanings

Tandy's **Color Computer 3 Service Manual**, printed/PDF 17, separates the RGB
meanings of the palette bits from the composite meanings.
It also gives a PAL caveat.
Read the appropriate table for the actual display. [Tandy, PDF 17][coco3]

Check the page image when you select values.
Converted text can merge table labels.
A value chosen for one display path is not a promise of the same visible
colour on another.

Tepolt's advanced graphics discussion also describes colour blending.
Treat the resulting appearance as display-dependent.
Do not count it as extra independently addressable palette entries.
[Tepolt, PDF 59][tepolt]

## Check pixel order before interpreting colour

Motorola's **MC6847/MC6847Y Video Display Generator** datasheet gives direct
pixel-order evidence.
Table 3 on printed/PDF 19 maps the RG6 display from `L7` at the left to `L0`
at the right.

Figure 22 on printed/PDF 21 identifies the corresponding byte positions as
`D7` through `D0`.
Thus the chip's RG6 format places the most significant bit at the left.
[Motorola][mc6847-pixels]

This is chip-level evidence for MC6847/MC6847Y, not a complete CoCo setup.
Check the board's data wiring and selected mode before applying it.
It does not establish MC6847T1, PAL adaptations, or native CoCo 3 GIME
behaviour.
An asymmetric pattern remains useful to check the complete emulator or display
path.

Do not confuse pixel order with artifact colour.
The datasheet's mode and encoding tables describe nominal pixel values.
Actual composite appearance also depends on the board's video circuitry and
display, as the CoCo 2 manual explains.

## Treat sync timing as a hardware contract

The same datasheet distinguishes active display, borders, and synchronization.
PDF 8 specifies a field-sync pulse lasting 32 line periods.
PDF 13 associates its falling edge with the end of the active area.
These are chip signals, not measured deadlines for a CoCo drawing routine.
[Motorola, PDF 8 and 13][mc6847-sync]

PDF 22 first describes a system without the MC6883, then discusses the SAM's
transparent memory access separately.

The generic system has an update window.
Do not turn that window into a rule that a CoCo can write screen RAM only
during that interval.
Memory access and visually clean animation are different requirements.
[Motorola, PDF 22][mc6847-system]

For a new synchronization routine, check the CoCo board's signal routing and
PIA interrupt handling.
Measure the drawing time at the selected CPU clock.
The datasheet alone does not prove that a page change or redraw finishes without
tearing.

## Make a display test before making the art

Correct screen bytes do not prove a correct picture. With a wrong SAM mode or
a reversed bit order, every byte stays correct, but the picture is wrong.
Add `--video` to `scripts/coco.py check` to compare XRoar's rendered frame
with `expected_frame`.

These checks already run on the examples:

| Check | Target | What it proves |
| --- | --- | --- |
| [First screen](../../examples/first-screen/README.md) `check --video` | CoCo 1 | Border pixels at each edge and four bars, in each of the eight modes. |
| [Palette swatches](../../examples/palette-swatches/README.md) `check --video` | CoCo 1 and CoCo 2 | Every colour of CG6 and RG6 in both colour sets, bit order, byte boundaries and orientation. |
| Wrong SAM mode, in `scripts/coco_spec.py` | CoCo 1 and CoCo 2 | The memory check passes and the rendered check fails. |
| Mirrored, upside-down or shifted frames, in the palette spec | Model only | The expected picture is not symmetric, so orientation and row errors fail. |

The wrong-SAM control writes `$FFC4` in place of `$FFC5`. That write clears
SAM bit V2, so the mode bits are not `110`, the value for CG6 and RG6.
[Tandy, PDF 15 and PDF 31 Table 1][technical]

Every `check` also sets a trap on an address that the program must never
reach. A fired trap or a missing checkpoint fails the check. A plausible
image alone is not evidence that the program ran.

The CoCo 2 target is an explicit configuration: XRoar `cocous`, NTSC, 32 KiB,
a normal-clock 6809, a non-T1 MC6847, and BASIC 1.2 with Extended BASIC 1.1.
XRoar's `coco2bus` profile selects a T1 VDG instead. The palette-swatches
results do not apply to it.

### Limits of the rendered check

- The capture uses S-video colours with cross-colour off, and shows the active
  area only. It does not show the border or artifact colours.
- Each RG6 pixel is two samples wide in a 512x192 frame. There is no 4:3
  stretch.
- The RGB values are XRoar's palette, not a monitor or a television.
- The capture is one still frame. It does not show cadence or tearing. Read
  the [animation guide](animation.md) for those.
- PAL, the MC6847T1, CoCo 3 and physical hardware are not tested.

An earlier private XRoar 1.12.1 build also captured frozen animation frames.
A self-loop at the checkpoint stopped each scene after a completed draw.

On CoCo 1, moving-objects frames 1, 35 and 65 matched every renderer sample. On
the CoCo 2 target above, tile-room steps 0, 5, 39 and 41 and masked-object
scenes 0, 2, 3 and 8 to 11 matched. Captures after half a second and after one
emulated second were identical. They show selected still scenes, not motion.
The examples do not run them again.

### Test your own display path

1. Record the machine, the video standard, the connection and the emulator
   settings in the project contract.
2. Write `expected_frame` from your pixel layout, not from the assembled
   bytes.
3. Make the picture asymmetric, with pixels at the edges.
4. Add a negative control that the memory check cannot catch.
5. Open the PNG, then look at the `run` window.
6. Repeat for each display path that the project promises to support.

If physical hardware is a target, repeat the test on that hardware.
An emulator capture shows only that emulator configuration.
A RAM snapshot shows the stored values, not their visible colour.

## Sources and provenance

- Tandy, *Color Computer 2 NTSC Service Manual (26-3134 & 26-3136)*,
  printed/PDF 31–33. Resource `coco2-service`. [Archive][coco2]

- Tandy, *Color Computer Technical Reference Manual*, PDF 15 (printed 8) and
  PDF 31 Table 1. Resource `coco1-technical`. [Archive][technical]

- Tandy, *Color Computer 3 Service Manual*, printed/PDF 17.
  Resource `coco3-service`. [Archive][coco3]

- Laurence A. Tepolt, *Assembly Language Programming for the CoCo3* (1987),
  PDF 59. Resource `tepolt-coco3`. [Archive][tepolt]

- Motorola, *MC6847/MC6847Y Video Display Generator*, 1984, DS9823-R1,
  printed/PDF 8, 13, 19, 21–22. Technical pages 1–23 examined as images.
  Resource `mc6847`. Archive filename: *MC6847 MOS Video Display Generator
  (Motorola)*. [Archive][mc6847-pixels]

We examined these source pages as images.
We have not compared colours across physical displays.
The [research notes](research/README.md) record the source selection.

[coco2]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%202%20NTSC%20Service%20Manual%20(26-3134%20&%2026-3136)%20(Tandy).pdf#page=31>

[coco3]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%203%20Service%20Manual%20(Tandy).pdf#page=17>

[tepolt]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20(1987)%20(Laurence%20A%20Tepolt).pdf#page=59>

[mc6847-pixels]: <https://colorcomputerarchive.com/repo/Documents/Datasheets/MC6847%20MOS%20Video%20Display%20Generator%20(Motorola).pdf#page=19>

[mc6847-sync]: <https://colorcomputerarchive.com/repo/Documents/Datasheets/MC6847%20MOS%20Video%20Display%20Generator%20(Motorola).pdf#page=8>

[mc6847-system]: <https://colorcomputerarchive.com/repo/Documents/Datasheets/MC6847%20MOS%20Video%20Display%20Generator%20(Motorola).pdf#page=22>

[technical]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%20Technical%20Reference%20Manual%20%28Tandy%29.pdf#page=15>
