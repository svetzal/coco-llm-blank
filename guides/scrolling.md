# Plan scrolling and memory on CoCo 3

Read this before designing a scrolling playfield, smooth text output, or
combining banked assets with interrupts. This guide covers examined CoCo 3 ideas.
It does not provide a tested scrolling engine or apply GIME behaviour to CoCo 1
or 2.

## Trade stored pictures for drawing work

Laurence A. Tepolt describes pre-shifted buffers with horizontal and vertical
display offsets in **Assembly Language Programming for the CoCo3** (1987),
PDF 59. This gives a starting point for motion across a larger picture.
It also creates a memory cost that must be understood before implementation.
[Tepolt, PDF 59][scroll]

Our proposed approach is to make that cost explicit:

1. Choose the display mode from the target's mode table.
2. Check the offset granularity, alignment, and wrap behaviour in the hardware references.
3. Decide which motion steps need distinct prepared pictures.
4. Budget those pictures alongside the map, assets, stack, and code.
5. Prototype one scrolling direction before adding map updates or objects.

For a design with `N` complete prepared buffers of `B` bytes each, storage is
`N * B` bytes. This is our accounting rule, not a speed measurement.
Include any borders or off-screen rows in `B`. More buffers may reduce work
during display updates, but this research has not measured that tradeoff.

Do not infer register values or alignment from this guide. Read the selected
mode's complete register description before setting its offsets.
The examined page supplies a technique, not every constraint of your engine.

## Scroll text a scan line at a time

John Blochowiak's **"A Smooth Operator"**, *The Rainbow*, January 1988,
printed 78 and 80 / PDF 80 and 82, modifies BASIC's 40-column text scrolling.
It applies to output such as `LIST`, `DIR`, and `PRINT`. Its complete listing
and April correction were examined. This is a text-output technique, not a
bitmap camera or tile engine. [Article][smoothy]

The hardware cross-check separates two controls:

- `$FF9C` adjusts the position within a text row. Tepolt describes values 0–7
  and the transition back to zero after completing a row.
- `$FF9D` and `$FF9E` supply physical display-address bits 18–3. The buffer
  therefore starts on an eight-byte boundary. They do not hold a CPU virtual address.

Tandy names these registers on printed/PDF 13. Tepolt explains their operation
on PDF 33. His description concerns text with eight scan lines
per character. Do not transfer that procedure to another character height
without checking its mode. [Tandy][registers] [Tepolt][text-scroll]

Our design interpretation is to prepare the next text row before exposing it,
step the within-row offset, then advance the buffer origin at the row boundary.
That follows Tepolt's explanation. It does not establish a tested update rate
or a tear-free change. The BASIC patch also contains memory copies and
firmware-specific entry points, so the register idea alone is not a complete port.

## Understand the 512K correction

The April 1988 Rainbow notice, printed/PDF 14, changes 25 to 217 in line 170
and 24 to 216 in line 220. It reports that the original SMOOTHY does not work
properly on 512K machines. Keep the correction with the original article.
[Correction][smoothy-fix]

Those numbers are bytes inside the machine-code DATA, not separate BASIC
screen coordinates. Our interpretation of the listing places them in the
values later written to `$FF9D`. Small LWASM opcode probes confirmed that
interpretation. We did not run the original program.

Tandy's table assigns `$FF9D` to address bits 18–11.
The original values `$18` and `$19` contribute `$0C000` and `$0C800` to the
physical display address. The corrected `$D8` and `$D9` contribute `$6C000`
and `$6C800`. `$FF9E` supplies the remaining address bits.
These are derived addresses, calculated from the documented bit assignments.
[Tandy, PDF 13][registers]

Tepolt explains that a 128K machine ignores address bits 18 and 17, so the
same RAM appears in four regions. His BASIC memory map places the high-resolution
text buffer at `$6C000`. [PDF 29][aliasing] [PDF 58][basic-map]

Together, these sources explain why the original constants can reach the same
RAM on 128K, while selecting different RAM on 512K. The correction adds
`$60000`, changing those two upper address bits without changing the lower 17.
This is our cross-source explanation of the published correction.
The original [display-address probe](../examples/text-addressing/README.md) now
checks this specific selection at an instrumented XRoar GIME fetch boundary.
All eight memory-size/address combinations matched the predicted words.
That result does not validate SMOOTHY, rendered appearance, timing, or
physical hardware.

For a new implementation, derive display addresses from the intended physical
buffer. Do not rely on the 128K alias. Keep CPU mappings and display addresses
separate when calculating where to write and what to show.

## Validate text scrolling before adapting it

The following experiment remains proposed:

1. Use explicit CoCo 3 firmware, video settings, and 128K or 512K RAM.
2. Fill text rows with distinct labels and distinct data in the candidate
   physical regions.
3. Observe display-address writes through one complete within-row offset cycle.
4. Check the incoming bottom row and the transition back to offset zero.
5. Compare original and corrected address choices on both memory sizes.
6. Inspect the displayed transition for tearing at the normal CPU clock.

Check `LIST`, `DIR`, ordinary printing, and reset separately before claiming
that the published BASIC patch works. A new standalone credits routine needs
its own memory and input contract. Do not silently treat it as a reproduction
of SMOOTHY.

## Keep interrupt code reachable

Tepolt, PDF 60, explains why interrupt jump tables and handlers must remain
accessible when memory mappings change. A foreground asset bank change must
not hide the code needed to handle an interrupt. [Tepolt, PDF 60][mapping]

Our proposed memory-map review includes more than the handler address.
Mark the vector path, handler, stack, and data used by the handler in every
mapping the foreground can select. Then check their accessibility during each
transition. This review procedure is our synthesis of the mapping requirement.

The [timer-sound example](../examples/timer-sound/README.md) checks interrupts
with a fixed mapping. Its successful run does not validate bank switching.
Do not add asset banks to that example and retain its old support claim.

## Evidence needed for a scrolling implementation

These checks remain proposed:

- Compare visible pixels at the first offset, each alignment boundary, and wraparound.
- Check that objects and the playfield use the same coordinate convention.
- Check memory guards around prepared pictures and map storage.
- Trigger interrupts during every mapping transition.
- Inspect the running display for tearing and seams.
- Measure redraw work and interrupt work together at the chosen CPU clock.

A correct framebuffer alone cannot prove that the display selected the intended
address or that switching is visually clean. Preserve both memory evidence
and observations of the display.

## Sources and provenance

Laurence A. Tepolt, *Assembly Language Programming for the CoCo3* (1987),
resource `tepolt-coco3`: [PDF 59, advanced graphics][scroll];
[PDF 60, mapping and interrupts][mapping]. Both page images were examined.

The text-scrolling cross-check also uses:

- Tandy, *Color Computer 3 Service Manual*, printed/PDF 13, display registers,
  and 15–16, MMU addressing. Resource `coco3-service`. [Archive][registers]
- Tepolt, PDF 29, 128K memory aliasing; PDF 33, display controls;
  PDF 58, BASIC memory map.
  Resource `tepolt-coco3`. [Aliasing][aliasing] [Controls][text-scroll] [Map][basic-map]
- John Blochowiak, "A Smooth Operator," *The Rainbow*, January 1988,
  printed 78, 80 / PDF 80, 82. Resource `rainbow-1988-01`. [Archive][smoothy]
- "Corrections," *The Rainbow*, April 1988, printed/PDF 14.
  Resource `rainbow-1988-04`. [Archive][smoothy-fix]

The budget procedure, map review, and proposed checks above are original guidance.
No scrolling program or changing-map interrupt program was reproduced in this
research. [Research notes](../guidance/game-research.md#coco-3-graphics-and-memory)
retain the source selection and limits.

[scroll]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20(1987)%20(Laurence%20A%20Tepolt).pdf#page=59>

[mapping]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20(1987)%20(Laurence%20A%20Tepolt).pdf#page=60>

[registers]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%203%20Service%20Manual%20(Tandy).pdf#page=13>

[text-scroll]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20(1987)%20(Laurence%20A%20Tepolt).pdf#page=33>

[aliasing]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20(1987)%20(Laurence%20A%20Tepolt).pdf#page=29>

[basic-map]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20(1987)%20(Laurence%20A%20Tepolt).pdf#page=58>

[smoothy]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow,%20The%20(OCR)/The%20Rainbow%20Vol.%2007%20No.%2006%20-%20January%201988.pdf#page=80>

[smoothy-fix]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow,%20The%20(OCR)/The%20Rainbow%20Vol.%2007%20No.%2009%20-%20April%201988.pdf#page=14>
