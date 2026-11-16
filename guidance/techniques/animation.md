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

### Flip pages with the SAM

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

Extended BASIC turns on the field-sync IRQ at cold start, and its handler
reads `$FF02`. So clear `$FF03` bit 0 before you poll the flag. The
[page flip](../../examples/page-flip/README.md) README gives the evidence.

The example's check runs eight checkpoints on the CoCo 1, CoCo 2 and CoCo 3
targets. At each checkpoint it compares both screens and every rendered
sample.

On a CoCo 3 the same SAM writes flip the same screens in the VDG modes. In
those modes the SAM bits F6 to F0 give the physical address bits Y15 to Y9,
and `$FF9D` bits 7 to 5 give Y18 to Y16. [Tepolt, PDF 44][tepolt-44] BASIC
loads `$FF9D` with `$E0`. [Tepolt, PDF 56][tepolt-56]

The PIA interrupts stay on the CoCo 3. [Tepolt, PDF 49][tepolt-49] VSYNC is
still a PIA interrupt source. [Tandy CoCo 3, PDF 37][coco3-37] No source that
we read gives the timing of field sync on the CoCo 3. The FS wait works in
XRoar (measured). The XRoar model of that timing is an
[open question](#what-the-sources-do-not-settle).

### Flip pages in the GIME native modes

The native GIME display start is `$FF9D` x 2048 + `$FF9E` x 8, a physical
address. [Tandy CoCo 3, PDF 13][coco3-13] Bit 3 of `$FF92` enables the vertical
border (VBORD) IRQ source. [Tandy CoCo 3, PDF 11][coco3-11]
A read of `$FF92` clears a pending GIME IRQ. [Tepolt, PDF 50][tepolt-50]

VBORD is not the PIA field-sync flag. Do not use the SAM strobes for a native
display: in the native modes the SAM offset has no effect.
[Tepolt, PDF 39][tepolt-39] The `coco3` variant of the
[page flip](../../examples/page-flip/README.md) gives both screens the same
`$FF9E`, so only `$FF9D` changes. It writes `$FF9D` after a new VBORD and
waits for the next VBORD before it uses the old screen again.

The variant keeps the screens of the main build, CPU `$0400` and `$2400`.
Under BASIC's map they are at physical `$70400` and `$72400`, so `$FF9D` is
`$E0` or `$E4` and `$FF9E` is `$80`. A 128 KiB CoCo 3 does not use Y18 and
Y17, so the same values work at 128 and 512 KiB. [Tepolt, PDF 29][tepolt-29]

Its check runs eight checkpoints at 128 and 512 KiB. A wrong display base
passes the memory check and fails the rendered check.

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

**Open question: the timing of field sync on the CoCo 3.** Evidence kind:
the XRoar model only. No published source that we read gives this timing.
The *Color Computer 3 Service Manual* says only that VSYNC is still a PIA
interrupt source. [Tandy CoCo 3, PDF 37][coco3-37] We read the source of the
pinned XRoar 1.13:

- CoCo 1 and 2 (`src/mc6847/mc6847.h` lines 64-70, `src/mc6847/mc6847.c`
  lines 385-393): a frame has 262 lines. FS falls at line 230, the end of the
  active display. FS is low for 32 lines. The active display starts 70 lines
  after the fall.
- CoCo 3 (`src/tcc1014/tcc1014.c` lines 1192-1257, at 60 Hz in the CoCo
  modes): a frame has 263 lines. FS falls at the start of vertical sync,
  about 28 lines after the end of the active display. Thus it falls about 28
  lines later than on the VDG. FS is low for 4 lines. The active display
  starts about 43 lines after the fall.

A program that starts work at the fall of FS has less time before the active
display on a CoCo 3 in XRoar. Only a measurement on a physical CoCo 3 can
settle the real timing.

The `--video` check sees one frame: the second frame after each checkpoint.
A fault that shows only in later frames can pass it.

## Decide what to redraw

Start with a full redraw. It is the correctness baseline, and the examples use
it. Consider a selective redraw only when a small record describes all pixels of
a column or cell.

**Published explanation.** John Kowalski's *Gloom 3-D V1.2* (1996, CoCo 3)
compares colour and distance records for each column with the previous frame.
It updates only the changed columns. See `ENGINE`/`OUTRAN` 00360-01700 and
`CLOSAM`/`CLODIF` 01860-02300 in [the source][gloom]. `DRAW` (01720-01840)
exchanges the pointers of two 256-byte tables (`BAR1`/`BAR2`, 08080-08100).
Its README, lines 94-98, describes one screen and proposes two. [Readme][gloom-readme]

**Derived.** The tables hold 128 two-byte column records, not two screens, so
the exchange is not a page flip. A wall can change colour at the same height
(`CLODIF` 02160-02300). A farther wall exposes floor and ceiling, which
`FURSAM`/`FURDIF` (02720-03160) repaint. Geometry alone is not a full record.

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
Measure both methods. Test growth, shrinkage and colour-only changes.

Do not port Gloom unchanged. `SETUP` (03320-03860) changes the clock, vectors
and machine state, detects a 6309 and contains `LDMD`. `GOON` (02540-02620)
changes its own operand. The README names EDTASM (line 21) and puts data at
`$00000-$2FFFF` and `$60000-$63FFF` (lines 45-48, 60-66). `gloom.txt` lines
15-26 describe strictly 6809 code, unlike this listing. Its frame rate is the
author's report.

For packed CoCo 3 pixels, read the [colour guide](colour.md#keep-the-neighbour-pixel-and-the-palette-separate).

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
*Flower Fantasy* (16K Extended Color BASIC) adds circle segments without a
clear and rejects the centre pixel's colour. [Ramella, PDF 18][ramella] This
removes a shape list, but also undo. The centre test does not test the area of
the new shape, so it is not collision detection. Our adaptation chooses from
the remaining colours instead of a retry loop, and clips each shape.

Ramella's *Winky* draws a face once, then loops over the arcs of the eye (lines
670-760, PDF 6). Its prose line references do not always match the listing.
[Ramella, PDF 4-6][winky] Our adaptation restores a fixed rectangle before each
new state of the eye. That erases any object over the rectangle. These 1985
BASIC sources do not establish CoCo 3 support. Do not copy their POKEs, PMODE
changes or delays into assembly.

## Sources

- Tandy, *Color Computer Technical Reference Manual*, PDF 13 and 15 (printed 6
  and 8). Resource `coco1-technical`.
- Motorola, *MC6821 Peripheral Interface Adapter*, PDF 10, Figure 18.
- Motorola, *MC6847/MC6847Y Video Display Generator*, PDF 22. Resource `mc6847`.
- Motorola, *MC6883 Synchronous Address Multiplexer*, PDF 8. Its advance
  information, PDF 15.
- Tandy, *Color Computer 3 Service Manual*, PDF 11-18 and 37. Resource
  `coco3-service`.
- XRoar 1.13 source, the pinned emulator: `src/mc6847/mc6847.h`,
  `src/mc6847/mc6847.c` and `src/tcc1014/tcc1014.c`. A model of the
  hardware, not a published hardware source.
- Laurence A. Tepolt, *Assembly Language Programming for the CoCo3* (1987),
  PDF 29, 39, 44, 49, 50 and 56. Resource `tepolt-coco3`.
- John Kowalski, *Gloom 3-D V1.2* (1996), read in full, cited routines
  analysed. Its README (lines 10-16) calls it "Openware", not a licence.
  SHA-256: `gloom.asm`
  `dfbd0810d00b83952c3bd494a0425c79e7280e55c16f65ef0fa806b051375acb`,
  `readme.txt` `bd3fe192c8b3cff482b6fe23c96abb1d192940236ab8f532672469b41868e91e`,
  `gloom.txt` `5996cc6705c0e70bd5e4f44c0ee5c1473e1640059d733f42b850f3da76be6a47`.
- *The Rainbow*: Polsz, October 1986 (`rainbow-1986-10`). Matthews, October
  1987 (`rainbow-1987-10`). Pendell, October 1992 (`rainbow-1992-10`).
- Richard Ramella, *Undercolor* (ColorPlus Inc.), page images, no resource
  ID: "Another Fine Mess", 1:3, January 11, 1985, printed 2-4, 6, 23 / PDF 4-6,
  8, 25, SHA-256 `86b30ed5b747eac47ad21b9b28d5a241cee8807f7a06d6d14dfa436eb6c6ca96`.
  "Summer Frippery", 1:11, June 30, 1985, printed 16 / PDF 18, SHA-256
  `3120b8fa4fa96baba7a6337541ad93428d4b77c3dbdd7fde441f66b50b8edbb4`. See the
  [game-state guide](game-state.md#open-questions) for the correction search.

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
[coco3-37]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%203%20Service%20Manual%20%28Tandy%29.pdf#page=37>
[tepolt-29]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20%281987%29%20%28Laurence%20A%20Tepolt%29.pdf#page=29>
[tepolt-39]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20%281987%29%20%28Laurence%20A%20Tepolt%29.pdf#page=39>
[tepolt-44]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20%281987%29%20%28Laurence%20A%20Tepolt%29.pdf#page=44>
[tepolt-49]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20%281987%29%20%28Laurence%20A%20Tepolt%29.pdf#page=49>
[tepolt-50]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20%281987%29%20%28Laurence%20A%20Tepolt%29.pdf#page=50>
[tepolt-56]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20%281987%29%20%28Laurence%20A%20Tepolt%29.pdf#page=56>
[gloom]: <https://colorcomputerarchive.com/repo/Programming/Source/Gloom3D/gloom.asm>
[gloom-readme]: <https://colorcomputerarchive.com/repo/Programming/Source/Gloom3D/readme.txt>
[polsz]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow,%20The%20(OCR)/The%20Rainbow%20Vol.%2006%20No.%2003%20-%20October%201986.pdf#page=118>
[matthews]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow,%20The%20(OCR)/The%20Rainbow%20Vol.%2007%20No.%2003%20-%20October%201987.pdf#page=44>
[pendell]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow,%20The%20(OCR)/The%20Rainbow%20Vol.%2012%20No.%2003%20-%20October%201992.pdf#page=3>
[ramella]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Undercolor/Undercolor%20v01n11%20%281985%29%28ColorPlus%20Inc%29.pdf#page=18>
[winky]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Undercolor/Undercolor%20v01n03%20%281985%29%28ColorPlus%20Inc%29.pdf#page=4>
