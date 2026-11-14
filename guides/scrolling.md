# Plan scrolling and memory on CoCo 3

Read this before designing a scrolling playfield or combining banked assets
with interrupts. This guide covers examined CoCo 3 ideas. It does not provide
a tested scrolling engine or apply GIME behaviour to CoCo 1 or 2.

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

The budget procedure, map review, and checks above are original guidance.
No scrolling program or changing-map interrupt program was reproduced in this
research. [Research notes](../guidance/game-research.md#coco-3-graphics-and-memory)
retain the source selection and limits.

[scroll]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20(1987)%20(Laurence%20A%20Tepolt).pdf#page=59>

[mapping]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20(1987)%20(Laurence%20A%20Tepolt).pdf#page=60>
