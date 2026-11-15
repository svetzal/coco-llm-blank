# Decide what to redraw

Read this when a game or demo repeatedly draws a mostly unchanged scene. Start
with a full redraw as the correctness baseline.

Consider a comparison of descriptions when a small record can explain all pixels
in a column or cell. Keep full redraw available for invalid state and large
changes.

This guide summarizes source reading of John Kowalski's *Gloom 3-D V1.2* (1996)
and Robert Gault's *Symmetry* (1993). Both are CoCo 3 sources. Our procedures
and pseudocode are original adaptations.

A [bounded experiment](validation/selective-redraw.md) checks retained
descriptions and full-region repainting. It uses two 640-byte RAM windows on
explicit 128/512 KiB CoCo 3 configurations. Selective and full redraw match an
independent pixel oracle at 12 checkpoints per build and target.

We did not build or run either historical program. Timing, rendered display,
physical hardware and CoCo 1/2 compatibility remain unverified.

This is an algorithm guide. Use the experiment's documented configuration for
its narrower result.

## Compare descriptions, not just positions

Gloom produces colour/distance records, compares them with the previous records,
and updates column spans. Same-colour wall growth draws edges. Shrinkage
restores exposed floor and ceiling.

A colour change takes a different path even when geometry is unchanged. See
these parts of [Gloom's source][gloom]:

- `ENGINE`/`OUTRAN` 00360–01700
- `DAGAIN`/`CLOSAM`/`CLODIF` 01860–02300
- `GENLIN`/`GENLI2` 02440–02520
- `FURSAM`/`FURDIF` 02720–03160

Its two description tables occupy 256 bytes each, 512 bytes together
(`BAR1`/`BAR2`, 08080–08100). They are not framebuffers. `DRAW` exchanges table
pointers (01720–01840).

The [README][gloom-readme], lines 94–98, explicitly describes one screen and
proposes two screens as future work.

For your renderer, define what makes a region's pixels different. Include
geometry, colour indices and any changing texture or background content.
Recompute from current world state, even when the camera has not moved.

A tile-cell description can include world-cell identity and content revision.
That is our adaptation, not a tile renderer found in Gloom.

## Retain what each framebuffer actually contains

The following procedure is our proposed starting point:

1. Mark every region invalid on allocation or first use. Zeroed records are not
   proof that existing pixels match them.

2. Associate records with the actual destination framebuffer. With alternating
   buffers, compare against that buffer's last contents, not the last frame
   presented on another buffer.

3. Redraw an invalid region completely. For a changed valid region, start with
   whole-region repainting. Add span differences only if measurements justify
   it.

4. Save a description only after its drawing finishes. Invalidate affected
   regions after external writes, overlays or changes missing from the record.
   Invalidate everything after you replace the framebuffer layout.

This original pseudocode uses non-overlapping columns. Each description defines
the complete column, including its background:

```text
initially: valid[buffer][column] = false for every buffer and column

for each column in destination:
    next = describe_column(current_world, camera, column)
    if not valid[destination][column]
       or next != rendered[destination][column]:
        paint_complete_column(destination, column, next)
        rendered[destination][column] = next
        valid[destination][column] = true
```

This deliberately starts simpler than Gloom's span updates. If a wall shrinks,
painting the complete column restores the revealed background. Drawing only the
new wall would leave old wall pixels behind.

For partial-byte writes, see the [packed-pixel adaptation][packed] in the
research note. It is derived from Symmetry's `HPOINT`/`HSET`, `SYM.ASM`
01140–01380.

## Example: a stationary camera facing a door

In an original corridor demo, a switch changes a closed door's colour. Its
projected bounds stay fixed, but its colour field changes. Therefore, repaint
its columns.

When the door opens, describe the newly visible world. Repaint those columns,
including floor and ceiling. If a HUD temporarily overwrites them, invalidate
them before you restore the scene.

A world change must also update any projection caches. Redraw comparison cannot
repair stale world data.

Do not confuse drawing colour with palette mapping. Symmetry's `COLOR`
(`SYM.ASM` 00940–00980) changes the foreground index used by later plotted
points. Its BASIC host selects display-specific palettes (`SYMMETRY.BAS` 70–110,
130–140).

This does not show palette-cycling animation or the recolouring of existing
pixels by a change of the drawing index.
Source: [Robert Gault, Symmetry archive][symmetry].

## Decide whether the bookkeeping pays

A full redraw avoids retained-state comparisons and is easy to reason about when
most of the scene changes. Selective redraw adds description storage per
framebuffer, comparison work and invalidation rules.

It may avoid pixel writes. That alone establishes no speed advantage. Fine span
updates add more branches and edge cases than whole-column repainting.

Before you adopt the adaptation, compare its framebuffer bytes against an
independent full redraw. Include these cases:

- first use
- unchanged frames
- colour-only and world-only changes
- growth
- shrinkage
- alternating buffers
- external writes

Measure both elapsed time and writes on a stated machine configuration before
you choose the more complicated path. The linked experiment completes bounded
RAM comparisons and write counts.

Elapsed-time comparisons and visible output remain unverified. Repeat the checks
for your own scene and configuration.

Read the [source research and provenance][research] for exact download hashes,
citation conventions, source limitations and reuse terms.

Assembly citations above use embedded source numbers, not editor line numbers.
README citations use normalized physical lines. No PDF pages apply.

Historical files remain under ignored `local/research/coco3-game-sources/`. This
guide reproduces no historical code or assets.

[gloom]: https://colorcomputerarchive.com/repo/Programming/Source/Gloom3D/gloom.asm
[gloom-readme]: https://colorcomputerarchive.com/repo/Programming/Source/Gloom3D/readme.txt
[symmetry]: https://colorcomputerarchive.com/repo/Programming/Source/Symmetry/Symmetry.zip
[research]: research/coco3-game-source.md
[packed]: research/coco3-game-source.md#original-packed-pixel-adaptation
