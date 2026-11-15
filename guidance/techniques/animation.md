# Plan animation and redraw

Read this when you plan moving objects, an animation cycle or a scene that you
redraw often. It tells how to show only finished frames, how to decide what to
redraw, and how to budget animation storage.

## Show only finished frames

**Measured result.** A program that redraws the screen that the display shows
can show a frame that is not complete. Correct memory does not prove correct
output. The [page flip](../../examples/page-flip/README.md) negative control
shows this: with one screen, memory passes and the rendered check fails.

**Our adaptation.** Draw into a screen that the display does not show. When the
frame is complete, show that screen. Then draw the next frame into the other
screen. A slow frame is not visible while the program draws it.
Two 256x192 two-colour screens need 12,288 bytes.

### Flip pages on CoCo 1 and CoCo 2

These published facts come from page images:

- The SAM display offset is in 512-byte units. F4 is `$FFCE` (clear) and
  `$FFCF` (set). [Tandy, PDF 15][tandy-15]
- `$FF03` bit 7 is the field-sync flag. Bit 1 selects the edge (0 is falling).
  Bit 0 enables the IRQ output. Bit 2 selects data at `$FF02`. [Tandy, PDF 13][tandy-13]
- A read of the data register clears the flag. [MC6821, PDF 10][mc6821]
- Field sync goes low at the end of the active display, for 32 lines.
  [MC6847, PDF 22][mc6847]

Screens at `$0400` and `$2400` differ only in F4, so one strobe changes the
screen. The [page flip](../../examples/page-flip/README.md) example does these
steps:

1. Draw the complete frame into the screen that the display does not show.
2. Read `$FF02` to clear an old flag. Wait for a new falling edge.
3. Write `$FFCE` or `$FFCF` to show the new screen.
4. Select the rising edge and wait for it. Then draw into the other screen.

The flag records an event, not the current level. Let one routine only read
`$FF02`. A keyboard scan or a ROM interrupt handler can clear the flag first.
Keep the other `$FF03` bits when you change bits 0 and 1.

The example's check runs 14 checkpoints on CoCo 1 and non-T1 CoCo 2 targets.
At each checkpoint it compares the drawn screen and every rendered sample.

### Flip pages on a CoCo 3

The native GIME display start is `$FF9D` x 2048 + `$FF9E` x 8, a physical
address. [Tandy CoCo 3, PDF 13][coco3-13] Bit 3 of `$FF92` enables the vertical
border (VBORD) IRQ source. [Tandy CoCo 3, PDF 11][coco3-11]
A read of `$FF92` clears a pending GIME IRQ. [Tepolt, PDF 50][tepolt-50]

VBORD is not the PIA field-sync flag. Do not use the SAM strobes for a native
display. The [CoCo 3 page flip](../../examples/page-flip-coco3/README.md) gives
both buffers the same `$FF9E`, so only `$FF9D` changes. It writes `$FF9D` after
a new VBORD and waits for the next VBORD before it uses the old buffer again.

Its check runs six checkpoints at 128 and 512 KiB. A wrong display base passes
the memory check and fails the rendered check.

### What the sources do not settle

The SAM datasheet describes a vertical preload of the display counter from the
offset bits. [SAM, PDF 8][sam] The advance information puts the effect in the
time that field sync is low. [SAM advance information, PDF 15][sam-advance]
Neither gives the exact instant, a limit for the last strobe, or when the old
screen is free.

The GIME pages do not give the instant at which the GIME loads `$FF9D` and
`$FF9E`. They do not say if a change to both bytes is atomic.

The pinned XRoar loads the SAM offset at the rising edge of field sync. So the
CoCo 1/2 example also passes without the wait in step 2. The examples keep the
conservative waits. Only a physical test with a sweep of the write time can
settle these limits.

The `--video` check sees one frame: the second frame after each checkpoint.
A fault that shows only in later frames can pass it.

### Measured with a private XRoar build

An earlier lab recorded 150 consecutive frames in XRoar 1.12.1 on CoCo 1 and
non-T1 CoCo 2. With one screen, 47 were complete and two showed a partly erased
object. With page flipping, all 150 were complete, also with 32 more NOPs for
each background byte. One frame took 98.97 ms to draw, about seven video frames.
On CoCo 3 (GIME 1986), 42 consecutive frames were complete. These are emulator
results only, not physical tearing, PAL or host smoothness.

## Decide what to redraw

Start with a full redraw. It is the correctness baseline, and the examples use
it. Consider a selective redraw only when a small record describes all pixels of
a column or cell.

**Published explanation.** John Kowalski's *Gloom 3-D V1.2* (1996, CoCo 3)
compares colour and distance records for each column with the previous frame.
It updates only the changed columns. See `ENGINE`/`OUTRAN` 00360-01700 and
`CLOSAM`/`CLODIF` 01860-02300 in [the source][gloom]. Its README, lines 94-98,
describes one screen and proposes two. [Readme][gloom-readme]

**Our adaptation** is this procedure:

1. Mark every region invalid at the start. A zero record is not a valid one.
2. Keep a record set for each screen. Compare with what that screen holds.
3. Repaint a changed or invalid region completely, with its background.
4. Save the record after the drawing. Invalidate a region after other writes.

```text
for each region in destination:
    next = describe(world, region)
    if not valid[destination][region] or next != drawn[destination][region]:
        paint_complete_region(destination, region, next)
        drawn[destination][region] = next
        valid[destination][region] = true
```

Put every input that changes pixels in the record: geometry, colour indices and
background. A fixed camera does not make a changed background safe.

**Measured result, not rerun here.** A lab on XRoar 1.12.1 checked this
procedure in two 640-byte RAM windows on CoCo 3 (GIME 1986, 128 and 512 KiB).
Selective and full redraw matched an independent pixel model at 12 checkpoints.
A shared record set left 64 wrong bytes. A missing invalidation left one wrong
byte. The lab had no display and no timing, so it makes no speed claim.

Selective redraw adds record storage, comparisons and invalidation rules.
Measure both methods before you choose it. For packed pixels and palettes, read
the [CoCo 3 source reading](research/coco3-game-source.md#original-packed-pixel-adaptation),
which also records source hashes and reuse limits.

## Budget the storage for animation

**Published explanation.** Steven R. Polsz compares oversized BASIC arrays with
compact storage. [Polsz, PDF 118-119][polsz] Becky F. Matthews prepares two
PMODE pictures and shows them in turn. Her example copies the shared background
first. [Matthews, PDF 44, 46-47][matthews] BASIC formats are not assembly rules.

**Our adaptation.** Define the asset format before the drawing routine: width,
height, bits for each pixel, row padding, and any mask or header.
For whole-byte rows:

```text
row_bytes = ceil(width * bits_per_pixel / 8)
picture_bytes = row_bytes * height
```

A 13x8 one-bit picture uses 16 bytes, and its mask 16 more. Check the pixel
packing of the mode in its hardware reference. Budget every frame, mask, screen,
code, state and the stack.

When complete pictures cost too much memory, store geometry. Joseph Pendell
calculates rotated end points before the display loop. [Pendell, PDF 3][pendell]
Two one-byte coordinates need `2 * point_count * frame_count` bytes. Line
drawing still happens in each frame. We did not run his CoCo 3 listing.

An accumulating picture can keep its history in the screen. Richard Ramella's
*Flower Fantasy* adds circle segments without a clear and rejects the centre
pixel's colour. [Ramella, PDF 18][ramella] This removes a shape list, but also
undo. The [Undercolor research](research/undercolor-game.md) records its limits.

## Sources

- Tandy, *Color Computer Technical Reference Manual*, PDF 13 and 15 (printed 6
  and 8). Resource `coco1-technical`.
- Motorola, *MC6821 Peripheral Interface Adapter*, PDF 10, Figure 18.
- Motorola, *MC6847/MC6847Y Video Display Generator*, PDF 22. Resource `mc6847`.
- Motorola, *MC6883 Synchronous Address Multiplexer*, PDF 8. Its advance
  information, PDF 15.
- Tandy, *Color Computer 3 Service Manual*, PDF 11-18. Resource `coco3-service`.
- Laurence A. Tepolt, *Assembly Language Programming for the CoCo3* (1987),
  PDF 50. Resource `tepolt-coco3`.
- John Kowalski, *Gloom 3-D V1.2* (1996), embedded source line numbers.
- *The Rainbow*: Polsz, October 1986 (`rainbow-1986-10`). Matthews, October
  1987 (`rainbow-1987-10`). Pendell, October 1992 (`rainbow-1992-10`).
- Ramella, "Summer Frippery", *Undercolor* 1:11, June 30, 1985, printed 16.

The procedures, allocations and pseudocode are our original guidance. We did
not reproduce the historical listings.

[tandy-13]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%20Technical%20Reference%20Manual%20%28Tandy%29.pdf#page=13>
[tandy-15]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%20Technical%20Reference%20Manual%20%28Tandy%29.pdf#page=15>
[mc6821]: <https://sowerbutts.com/replica1-serial/6821.pdf#page=10>
[mc6847]: <https://colorcomputerarchive.com/repo/Documents/Datasheets/MC6847%20MOS%20Video%20Display%20Generator%20(Motorola).pdf#page=22>
[sam]: <https://colorcomputerarchive.com/repo/Documents/Datasheets/MC6883%20Synchronous%20Address%20Multiplexer%20%28Motorola%29.pdf#page=8>
[sam-advance]: <https://colorcomputerarchive.com/repo/Documents/Datasheets/MC6883%20Synchronous%20Address%20Multiplexer%20Advance%20Information%20%28Motorola%29.pdf#page=15>
[coco3-11]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%203%20Service%20Manual%20%28Tandy%29.pdf#page=11>
[coco3-13]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%203%20Service%20Manual%20%28Tandy%29.pdf#page=13>
[tepolt-50]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20%281987%29%20%28Laurence%20A%20Tepolt%29.pdf#page=50>
[gloom]: <https://colorcomputerarchive.com/repo/Programming/Source/Gloom3D/gloom.asm>
[gloom-readme]: <https://colorcomputerarchive.com/repo/Programming/Source/Gloom3D/readme.txt>
[polsz]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow,%20The%20(OCR)/The%20Rainbow%20Vol.%2006%20No.%2003%20-%20October%201986.pdf#page=118>
[matthews]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow,%20The%20(OCR)/The%20Rainbow%20Vol.%2007%20No.%2003%20-%20October%201987.pdf#page=44>
[pendell]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow,%20The%20(OCR)/The%20Rainbow%20Vol.%2012%20No.%2003%20-%20October%201992.pdf#page=3>
[ramella]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Undercolor/Undercolor%20v01n11%20%281985%29%28ColorPlus%20Inc%29.pdf#page=18>
