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

## Keep the neighbour pixel and the palette separate

**Published explanation.** Robert Gault's *Symmetry* (1993, CoCo 3) has a BASIC
host and an assembly plotter. `SYMMETRY.BAS` lines 70–110 and 130–140 ask for
RGB or composite, choose one of two 16-entry tables, enter `HSCREEN2` and set
the palette.

In `SYM.ASM`, `COLOR` (00940–00980) stores an index 1–15 at the
foreground-colour location `$FE0A` (`HFCOLR`, 00180). It writes no palette
register. `HPOINT`/`HSET` (01140–01380) use a 160-byte row stride. They keep
the other nibble of the byte and insert the colour. [Symmetry ZIP][symmetry]

So a new drawing index changes only new points. This is not palette cycling.
The two tables are the author's display choices, not proof of equal colour on
every RGB or composite display.

**Our adaptation.** Define art in colour indices. Choose the mapping for the
display path at setup. To change one pixel, keep its neighbour:

```text
address = framebuffer_start + y * row_stride + floor(x / 2)
shift = 4 if x is even else 0
mask = 15 << shift
memory[address] = (memory[address] AND (255 XOR mask)) OR (colour_index << shift)
```

This assumes the packing that `HPOINT` uses: the even pixel in the high nibble.
Check the selected mode in the hardware reference first. Test both parities
with different neighbours, every edge, and rejected input next to guard bytes.

The plotter is not self-contained. `START` and `EXIT` call ROM entry points
through `TASK1`/`TASK0` (00190–00200, 00290, 00800–00810), as the source
comments name them. `RAND` uses the BASIC random state. BASIC line 20 loads
`SYM6809`, but the ZIP holds `Sym.bin`. We did not assemble or run it.

## Check pixel order before interpreting colour

Motorola's **MC6847/MC6847Y Video Display Generator** datasheet gives direct
pixel-order evidence.
Table 3 on printed/PDF 19 maps the RG6 display from `L7` at the left to `L0`
at the right.

Figure 22 on printed/PDF 21 identifies the corresponding byte positions as
`D7` through `D0`.
Thus the chip's RG6 format places the most significant bit at the left.
[Motorola][mc6847-pixels]

PDF 12 gives the address order: left to right, then
top to bottom. PDF 11 separates the 192 active lines from borders and retrace.
The RG6 paragraph on PDF 20 says 256×193, but its heading and the tables on PDF
14, 18 and 19 say 256×192. We use 256×192.

This is chip-level evidence for MC6847/MC6847Y, not a complete CoCo setup.
Check the board's data wiring and selected mode before applying it.
It does not establish PAL adaptations or native CoCo 3 GIME behaviour.
The MC6847T1 has the same graphics modes and the same colour for each code
and colour set. It is different only in the text and semigraphics modes.
[MC6847T1 datasheet, PDF 15, 16 and 25][mc6847t1]
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
| [First screen](../../examples/first-screen/README.md) `check --video` | CoCo 1, CoCo 2 and CoCo 3 | Border pixels at each edge and four bars, in each of the eight modes. On the CoCo 3, the check does not run RG1, RG2 and RG3. |
| [Palette swatches](../../examples/palette-swatches/README.md) `check --video` | `coco1`, `coco2`, `coco2b` and `coco3` | Every colour of CG6 and RG6 in both colour sets, bit order, byte boundaries and orientation. The picture is not symmetric, so a mirrored, upside-down or shifted frame fails. |
| Wrong SAM mode, in `scripts/coco_spec.py` | CoCo 1 and CoCo 2 | The memory check passes and the rendered check fails. |

The wrong-SAM control writes `$FFC4` in place of `$FFC5`. That write clears
SAM bit V2, so the mode bits are not `110`, the value for CG6 and RG6.
[Tandy, PDF 15 and PDF 31 Table 1][technical]

Every `check` also sets a trap on an address that the program must never
reach. A fired trap or a missing checkpoint fails the check. A plausible
image alone is not evidence that the program ran.

The palette-swatches check passes on `coco2` (MC6847) and `coco2b`
(MC6847T1) with the same `xroar` palette in all four variants (measured). The
[standard targets](../starter/toolchain.md#standard-targets)
table gives each machine.

### Limits of the rendered check

- The capture uses S-video colours with cross-colour off, and shows the active
  area only. It does not show the border or artifact colours.
- Each RG6 pixel is two samples wide in a 512x192 frame. There is no 4:3
  stretch.
- The RGB values are XRoar's palette, not a monitor or a television.
- The capture is one still frame. It does not show cadence or tearing. Read
  the [animation guide](animation.md) for those.
- PAL and physical hardware are not tested. T1 text and semigraphics modes
  are not tested.

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
  printed/PDF 8, 11–14, 18–22. Technical pages 1–23 examined as images.
  Resource `mc6847`. Archive filename: *MC6847 MOS Video Display Generator
  (Motorola)*. It is not the separate MC6847T1 datasheet. [Archive][mc6847-pixels]

- Motorola, *MC6847T1 Video Display Generator*, PDF 15 Table 1, PDF 16
  Tables 2 and 3, and PDF 25 Figure 26(c). Archive copy only. It is not a converted
  resource. [Archive][mc6847t1]

- Robert Gault, *Symmetry* (1993). We read all of `SYM.ASM` and `SYMMETRY.BAS`
  and analysed the cited routines. `SYM.ASM` cites use the embedded source
  numbers. ZIP SHA-256
  `dafe532a230b2595fc40b67bdc34aa263e22f372620167abc7ac9f523786131f`. No
  member gives reuse terms. [Archive][symmetry]

We examined these source pages as images.
We have not compared colours across physical displays.

[coco2]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%202%20NTSC%20Service%20Manual%20(26-3134%20&%2026-3136)%20(Tandy).pdf#page=31>
[coco3]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%203%20Service%20Manual%20(Tandy).pdf#page=17>
[tepolt]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20(1987)%20(Laurence%20A%20Tepolt).pdf#page=59>
[mc6847t1]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Motorola%20MC6847T1%20VDG%20Spec.pdf#page=15>
[mc6847-pixels]: <https://colorcomputerarchive.com/repo/Documents/Datasheets/MC6847%20MOS%20Video%20Display%20Generator%20(Motorola).pdf#page=19>
[mc6847-sync]: <https://colorcomputerarchive.com/repo/Documents/Datasheets/MC6847%20MOS%20Video%20Display%20Generator%20(Motorola).pdf#page=8>
[mc6847-system]: <https://colorcomputerarchive.com/repo/Documents/Datasheets/MC6847%20MOS%20Video%20Display%20Generator%20(Motorola).pdf#page=22>
[technical]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%20Technical%20Reference%20Manual%20%28Tandy%29.pdf#page=15>
[symmetry]: <https://colorcomputerarchive.com/repo/Programming/Source/Symmetry/Symmetry.zip>
