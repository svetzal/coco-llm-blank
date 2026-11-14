# Selective-redraw RAM validation

The [original bounded experiment](../../../experiments/selective-redraw/README.md)
passes 12 framebuffer checkpoints on each of two CoCo 3 NTSC configurations,
128 KiB and 512 KiB. Both the selective and full-region-redraw builds match an
independent pixel oracle. This is emulator RAM evidence, not a rendered-image
or physical-hardware result.

## Examined basis, before implementation

The hardware passages below were read as page images before the dependent
implementation. PDF page numbers include the cover. The service-manual
printed page numbers match the PDF numbers cited here.

- Tandy, *Color Computer 3 Service Manual*, resource `coco3-service`,
  [archive PDF][service], PDF 11, 15–16: INIT0, task selection, six-bit MMU
  entries, 8 KiB pages, and the `$38–$3F` executive map. PDF 8 gives the
  128/512 KiB memory-map relationship. These support the explicit map and
  snapshot addressing contract. PDF 12 and 18 establish the 192-line and
  160-pixel/16-colour mode fields; this experiment uses that packed storage
  layout without configuring a display.
- Laurence A. Tepolt, *Assembly Language Programming for the CoCo3* (1987),
  resource `tepolt-coco3`, [archive PDF][tepolt], PDF 58, Fig. 7-2: top memory
  layout for 128/512 KiB machines. PDF 59, “Smooth Horizontal Scrolling”:
  two bytes represent four pixels in a 16-colour mode. Derived here:
  160 / 2 = 80 bytes per row; eight rows occupy 640 bytes. This is a bounded
  window allocation, not a full-screen allocation.
- Robert Gault, *Symmetry* (1993), [source archive][symmetry], `SYM.ASM`
  embedded lines 01140–01380, specifically 01250–01370: even/odd nibble
  placement and neighbour-preserving masks. This was inspected as source;
  no PDF page applies. The oracle packs the left pixel in the high nibble.
  Our renderer deliberately fills complete equal-colour byte pairs and needs
  no partial-byte masks.
- John Kowalski, *Gloom 3-D V1.2* (1996), [assembly][gloom], embedded
  01600–02520 and 02640–03100: colour/distance descriptions, comparisons,
  and exposed floor/ceiling restoration. [README][gloom-readme], normalized
  physical lines 94–98, explicitly describes one screen and proposes two.
  No claim that Gloom implements our per-framebuffer histories is made.
  Neither historical program was built or executed for this experiment.
- Ciaran Anscomb, XRoar 1.12.1, [release source][xroar],
  `src/tcc1014/tcc1014.c` lines 232–243, 811–829 and 1621–1626: `$FFD8`
  clears SAM R1; the emulator selects 16 master ticks per CPU cycle when
  R1 is clear, versus 8 when set. This examined implementation supports the
  explicit slow-rate selection in this emulator test. It is not a physical
  clock measurement. No new emulator instrumentation was added.

The general graphics book was consulted first, but its original-CoCo examples
do not establish CoCo 3 native mode fields. The CoCo 3 primary passages above
supply those facts. The older local Tepolt PDF-8 render was blank, including
an attempted PDFium rerender. It was not used as evidence for any register
value. Service-manual images and the examined XRoar implementation supplied
the required facts instead.

Whole-region repainting, valid flags, separate per-buffer histories, the
world-background fixture, and external-write invalidation are our original
adaptation of the [existing guide](../selective-redraw.md). They are
not copied historical implementation. A fixed camera does not make a changed
background safe to skip; the description must include that background.

## Measured scope

The development Mac run used LWTOOLS 4.25 and XRoar 1.12.1. Both runs used
`coco3`, `6809`, `ntsc`, `gime1986`, no cartridge, null UI/audio, and explicit
128 or 512 KiB RAM. Each starts with nonzero RAM (`-ram-init set`) and poisons
both allocated windows with `$A5`. The initial records are invalid.

The combined `coco3.rom` is 32,768 bytes with SHA-256
`ad358430568250eb8330a37f85361d9ce67e5ae6d5a28c17b31802cd3953a5d2`.
The runner calls the repository's checksum verifier before launching and
records the ROM hash, executable paths/hashes/versions, input hashes and
complete commands in ignored `build/selective-redraw/results.json`.

All 12 checkpoints pass for the selective and full builds on both capacities.
They cover initial invalid state, unchanged state, colour-only change,
shrinkage, growth to the whole region, changed world background, first use of
B, return to A, a distinct update to B, return to A's own retained contents,
external-write invalidation, and the unchanged frame after restoration.
The untouched portions of both windows and four adjacent guard bytes are
checked at each checkpoint.

The selective software store counts in fixture order are
`64, 0, 32, 32, 32, 32, 64, 0, 64, 0, 32, 0`.
The full-region build counts 64 at each checkpoint. Each painted region is
four bytes on eight rows. These counts describe executed instrumented pixel
stores only. They exclude initialization and bookkeeping. No trustworthy
whole-render elapsed-cost instrumentation was applied, so this work makes
**no speed claim**.

Both deliberate broken builds were run on both RAM capacities. Shared history
leaves 64 incorrect bytes on first use of B. Omitting invalidation leaves one
incorrect byte after the external write and on the next unchanged frame.
The preserved controls demonstrate that byte-oracle agreement is sensitive to
the two retained-state errors this experiment targets. The unreachable data
checkpoint creates no snapshot in any run.

The scoped specification run passes eight tests with 90.96% combined
statement/branch coverage of the host runner. Ruff and Markdown checks are
part of the reproduction commands. Coverage describes Python paths; it is
not assembly instruction coverage.

## Use and remaining limits

Use the adaptation when a few compact records completely determine a few
non-overlapping regions. Keep a full redraw oracle during development. Give
each destination its own history, and invalidate a region after anything else
writes it. Include all changing world inputs in the description or invalidate
when they change. Repaint exposed background on shrinkage.

This experiment owns two 8×8 regions in each eight-row window. It does not
present alternating screens, configure GIME display registers, demonstrate
tearing-free updates, measure palette appearance, or establish a full-screen
budget. General geometry, partial-byte edges, overlapping objects, DMA-like
writers, interrupt-driven rendering, disk loading, PAL, GIME 1987, 6309, CoCo
1/2 and physical machines remain outside the tested contract. Colour means
pixel index here, not the displayed RGB/composite colour.

The first follow-up for a displayed demo is explicit mode/base/palette setup
with a rendered-output check. A performance comparison needs trustworthy
emulated timing around complete rendering, including comparison and history
cost. Neither follows from the RAM agreement or store counts recorded here.

[service]: https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%203%20Service%20Manual%20(Tandy).pdf
[tepolt]: https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20(1987)%20(Laurence%20A%20Tepolt).pdf
[symmetry]: https://colorcomputerarchive.com/repo/Programming/Source/Symmetry/Symmetry.zip
[gloom]: https://colorcomputerarchive.com/repo/Programming/Source/Gloom3D/gloom.asm
[gloom-readme]: https://colorcomputerarchive.com/repo/Programming/Source/Gloom3D/readme.txt
[xroar]: https://www.6809.org.uk/xroar/dl/xroar-1.12.1.tar.gz
