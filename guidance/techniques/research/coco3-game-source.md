# CoCo 3 demos: update less memory and separate colour from geometry

Read this when designing a CoCo 3 renderer that changes only part of a scene,
or a pattern demo with packed pixels and selectable display palettes. Two
archive sources earned detailed reading: John Kowalski's **Gloom 3-D V1.2**
and Robert Gault's **Symmetry**. Both offer useful memory-update techniques
beyond the previously examined PacDude and SMOOTHY.

This is a source-backed design guide, not a tested port. No historical binary
was assembled, loaded or executed. There are no runtime, timing, framebuffer,
visual or physical-hardware results. The pseudocode below is our original,
untested adaptation. It contains no historical code or artwork.

Gloom changes the view by projecting a map into wall columns. Symmetry plots
a pattern on a fixed screen. Their useful contribution to a scrolling project
is narrower. Keep records of the rendered state and invalidate them on
purpose. Keep the packed neighbour pixels when you update memory. The
[scrolling guide](../scrolling.md) covers hardware scrolling. The
[tile-map guide](../tile-maps.md) covers tiles.

## Evidence and citation convention

Downloads are pinned below and retained under ignored
`local/research/coco3-game-sources/`. The archive files are data only.
Citations for `gloom.asm` and `SYM.ASM` use the **embedded five-digit source
numbers**, not editor line numbers. Citations for `SYMMETRY.BAS` use BASIC line
numbers. Gloom prose citations count physical lines after CR/CRLF-to-LF
normalization, including blank lines. No PDF was used, so PDF page numbers do
not apply. These plain-text listings required no OCR or image interpretation.

The complete downloaded `gloom.asm`, `readme.txt`, `gloom.txt`, `SYM.ASM` and
`SYMMETRY.BAS` were read. Detailed analysis was limited to the routines cited
below; reading the remaining code does not establish a complete correctness
review. Unexamined GLOOM2 files in the archive are a different candidate, not
evidence about this version.

## Gloom: compare a compact description before touching the screen

[Gloom's source][gloom-asm] identifies John Kowalski (Sock Master), 1996,
V1.2, for the 6809 CoCo 3 (`gloom.asm` 00020–00060). Its [README][gloom-readme]
lines 73–90 describes a pipeline: scan the map, produce drawing records, compare
old and new records, then update screen differences. The source exposes that
comparison rather than leaving it as a performance claim.

### What the renderer actually retains

| File, routine and numbered lines | Direct source evidence |
| --- | --- |
| `gloom.asm`, `ENGINE` through `OUTRAN`, 00360–01700 | Scans successive directions and writes a colour byte plus distance byte for each resulting wall column. |
| `gloom.asm`, `DRAW`, 01720–01840 | Selects the graphics mapping, loads the new and old record pointers, then exchanges their stored roles for the next pass. |
| `gloom.asm`, `DAGAIN` through `SKIPPO`, 01860–02420 | Compares old/new distances and colours, processes columns 0–127, and restores the normal mapping on return. |
| `gloom.asm`, `CLOSAM`, 02000–02140; `GENLIN`/`GENLI2`, 02440–02520 | Same-colour nearer-wall path draws edge spans whose length is the distance difference. A zero span returns without writing. |
| `gloom.asm`, `CLODIF`, 02160–02300 | Changed-colour nearer-wall path writes the new wall span rather than only its edges. |
| `gloom.asm`, `FURSAM`, 02720–02900 | Same-colour farther-wall path restores newly exposed floor and ceiling spans. |
| `gloom.asm`, `FURDIF`, 02920–03160 | Changed-colour farther-wall path restores floor, draws the wall and restores ceiling. |
| `gloom.asm`, `GOON`, 02540–02620, with `GFYX` at 00320 | Writes a vertical span by modifying the address operand in its own instruction. |
| `gloom.asm`, `BAR1`/`BAR2`, 08080–08100 | Reserves two 256-byte description tables. |

**Our derivation:** 128 columns × two bytes gives 256 bytes per description,
512 bytes for the pair. These are not two framebuffers. The README explicitly
says it currently draws one screen and proposes two screens as future work
(lines 94–98). Do not describe the table-pointer exchange as display-page
flipping.

The code's special cases explain why comparing only geometry is insufficient.
A wall can retain its height while changing colour. Conversely, a wall that
shrinks exposes floor and ceiling; painting only the new wall leaves stale
pixels. These are deductions from the cited branch paths, not measured bugs.

### An original adaptation for a simpler column renderer

For an original demo, retain a description of the pixels last rendered into
**each actual framebuffer**. Use explicit validity state for the first frame.
The following proposal uses half-open vertical intervals and deliberately
avoids the historical distance encoding and self-modifying instructions:

```text
for each screen column:
    next = project_world_column(camera, world, column)
    old = rendered_description[framebuffer][column]
    if old is invalid:
        paint_whole_column(next)
    else:
        cuts = sorted_unique(0, height,
                             old.wall_top, old.wall_bottom,
                             next.wall_top, next.wall_bottom)
        for each consecutive interval [a, b) in cuts:
            if colour_in(old, a) != colour_in(next, a):
                paint_column_interval(column, a, b, colour_in(next, a))
    rendered_description[framebuffer][column] = next
```

Require `0 <= wall_top <= wall_bottom <= height`. A description includes wall,
ceiling and floor colours, so a colour change can invalidate a span even if
its boundaries stay fixed. This interval algorithm is our explanation of a
generalized approach, not a transcription of Gloom's assembly.

It trades description memory and comparison work for potentially fewer pixel
writes. It is not guaranteed faster. A full redraw can be simpler when most
columns change. Dynamic sprites, texture changes, background effects and
external writes invalidate the premise that the description still matches
the framebuffer. Either include those changes in the description, restore the
background first, or invalidate the affected region.

### Memory and execution assumptions that must not disappear in a port

The README's map representation has two bytes per cell: wall/distance metadata
and colour (lines 45–48). Its acceleration metadata permits skipping open space
(lines 84–85; `ENGINE` 01120–01360). A changing map therefore needs an explicit
policy for those skip values. Our inference is that adding a wall without
repairing stale open-space metadata can make a scanner skip new geometry.
The README's suggestion about erasing a wall (102–106) is not proof that all
map edits preserve acceleration correctness. The map editor was not inspected.

The README places the map at `$60000–$63FFF` and the expanded radar table at
`$00000–$2FFFF` (45–48, 60–66). `RLOOP` at 04400–04660 generates the second
half of the radar data. These source facts rule out treating the small code
listing as the total memory requirement. No minimum-RAM compatibility was
established here.

`SETUP` (03320–03860) changes clock-related and machine state, installs vectors,
sets DP, detects a 6309 and contains `LDMD`. `DRAW` changes memory mapping and
`GOON` patches its own operand. A port must account for writable code, stack,
interrupts, mapping and assembler dialect. The README names EDTASM (line 21).
Do not assume the starter's `lwasm --6809` command accepts this file unchanged.

There is a version-context discrepancy worth preserving. [gloom.txt][gloom-text]
lines 15–26 describes strictly 6809 code and a 96K radar table; the examined
V1.2 listing has a conditional 6309-native path and expands the table, as above.
The prose's frame-rate statement at lines 18–21 is the author's report, not a
measurement from this work, and is not a benchmark for the examined source.
The prose also acknowledges walking through walls (10–13). Do not infer a
complete collision system from a rendered maze.

## Symmetry: preserve the adjacent pixel and choose a display palette

The [Symmetry archive][symmetry] contains `SYM.ASM`, `SYMMETRY.BAS` and
`Sym.bin`. `SYM.ASM` 00100 credits Robert Gault, 1993. The assembly's drawing
loop and its BASIC host together explain the visible-colour contract.

| File, routine and numbered lines | Direct source evidence |
| --- | --- |
| `SYMMETRY.BAS`, 70–110 and 130–140 | Asks RGB/composite, selects one of two 16-entry tables, enters `HSCREEN2`, and assigns the palette entries. |
| `SYM.ASM`, `MLOOP`/`M2`, 00400–00620 | Changes the drawing colour on a countdown, changes coordinates and plots symmetric points. |
| `SYM.ASM`, `COLOR`, 00940–00980; `HFCOLR`, 00180 | Selects an index 1–15 and stores it at the foreground-colour location `$FE0A`. It does not write a hardware palette register. |
| `SYM.ASM`, `POINT`, 01020–01100 | Plots four sign combinations. The caller swaps coordinates for another call. |
| `SYM.ASM`, `HPOINT`/`HSET`, 01140–01380 | Converts centre-relative coordinates, calculates a byte address with a 160-byte row stride, preserves the other nibble and inserts the selected colour. |
| `SYM.ASM`, `CLRSCR`/`CLOOP`, 00870–00920; constants 00130–00150 | Clears words from `$2000` through `$97FF`, using the declared screen limits. |

The distinction matters for effects. The BASIC host sets colour mappings;
assembly then draws with those indices. Changing the drawing index affects
newly plotted points. This is not a palette-cycling animation that recolours
all existing pixels. The two display tables are evidence of display-specific
choices by the author, not proof of perceptual equivalence on every RGB or
composite display.

### Original packed-pixel adaptation

The following pseudocode expresses the nibble-preservation idea in our own
form. It assumes the same high-nibble-even, low-nibble-odd packing that
`HPOINT` explicitly uses. Verify the selected hardware mode before applying it
to another framebuffer. This is not a portable register setup.

```text
require 0 <= x < width and 0 <= y < height
require 0 <= colour_index < 16
address = framebuffer_start + y * row_stride + floor(x / 2)
shift = 4 if x is even else 0
mask = 15 << shift
memory[address] = (memory[address] AND (255 XOR mask))
                  OR (colour_index << shift)
```

A single-pixel change must keep its neighbour pixel.

Keep palette choice outside geometry generation. Define art in colour indices,
then choose a display-specific mapping at setup. A later palette-animation
experiment could alter that mapping, but this source supplies neither a
cycling schedule nor evidence of tear-free palette updates.

### Host dependencies and reuse limits

The assembly is not self-contained. `START` and `EXIT` call hard-coded ROM
entry points through `TASK1`/`TASK0` (`SYM.ASM` 00190–00200, 00290, 00800–00810).
`RAND` uses BASIC random state (00120, 01460–01590). The BASIC host seeds that
state and supplies the walk/countdown parameters (lines 30–60). It also selects
the screen and palette before `EXEC` (100–120). The ROM entry-point meanings
are the source's comments; this pass did not independently validate them.

There is a packaging mismatch: BASIC line 20 loads `SYM6809`, while the ZIP
member is `Sym.bin`. Do not advertise the downloaded bundle as ready to run.
Minimum RAM, ROM revision, assembler compatibility, cleanup behaviour and
emulator/display behaviour remain untested. The proposed bounded pixel routine
above does not claim the original program validates arbitrary coordinates.

## Provenance, permissions and reproducibility

Gloom's copyright notice remains in its header. Its README lines 10–16 calls
the project "Openware", invites programmers to expand it, and requests that
revisions return to the archive. This is an author-stated invitation, not a
standard SPDX license or a blanket licensing claim for every archive asset.
This note reproduces none of its code or assets.

Symmetry's complete ZIP member list has no license file, and neither examined
text member supplies reuse terms. Authorship and public download availability
do not establish redistribution permission. Keep the original files ignored;
use original code and art for a starter implementation.

Retrieved 2026-11-14. `sources.json` records the exact URLs and SHA-256 hashes;
`members.json` records all three Symmetry member hashes. Normalized text changes
line endings only, using Latin-1 decoding to preserve byte values. Recreate
citations from the embedded line numbers rather than renumbering the listings.

| Download | SHA-256 |
| --- | --- |
| [gloom.asm][gloom-asm] | `dfbd0810d00b83952c3bd494a0425c79e7280e55c16f65ef0fa806b051375acb` |
| [Gloom readme.txt][gloom-readme] | `bd3fe192c8b3cff482b6fe23c96abb1d192940236ab8f532672469b41868e91e` |
| [gloom.txt][gloom-text] | `5996cc6705c0e70bd5e4f44c0ee5c1473e1640059d733f42b850f3da76be6a47` |
| [Symmetry.zip][symmetry] | `dafe532a230b2595fc40b67bdc34aa263e22f372620167abc7ac9f523786131f` |

## Evidence required before calling an adaptation working

These are proposed checks, not completed experiments:

1. Compare column-difference drawing against an independently generated full
   image. Include unchanged columns, growth, shrinkage, colour-only changes,
   empty/full-height walls and the first frame. A deliberately stale initial
   description should fail unless validity is tracked.
2. Alternate two framebuffers and alter the world between frames. Verify each
   buffer's description matches its own pixels. Add an external pixel change
   to demonstrate why invalidation is required.
3. For packed pixels, start with distinct neighbour nibbles, update each parity
   and check that only the intended nibble changes. Check all edges and reject
   out-of-bounds input without changing guard bytes.
4. Establish the chosen CoCo 3 RAM, ROM, CPU, clock, display and video-standard
   contract before execution. Check hardware facts in the cited technical
   references, then test assembly, loading, framebuffer bytes and visible
   output separately. Measure write counts and elapsed time before claiming
   the extra comparison work improves performance.

[gloom-asm]: https://colorcomputerarchive.com/repo/Programming/Source/Gloom3D/gloom.asm
[gloom-readme]: https://colorcomputerarchive.com/repo/Programming/Source/Gloom3D/readme.txt
[gloom-text]: https://colorcomputerarchive.com/repo/Programming/Source/Gloom3D/gloom.txt
[symmetry]: https://colorcomputerarchive.com/repo/Programming/Source/Symmetry/Symmetry.zip
