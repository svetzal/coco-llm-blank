# Build a room from tiles

Use a tile map when your game has repeated scenery, passages, walls, or objects
that change a small part of the room. Store the room as tile numbers. Let those
numbers select both the scenery to draw and the movement rules to apply.

Brian O'Neill's *PacDude Monster Maze* supplies the examined example. Its
renderer and movement routines share a map, but use separate address and rule
calculations. This guide explains that separation, then proposes a smaller
original game design.

**Evidence:** PacDude source reading only; that historical program was not run.
A separate original [tile-room example](../examples/tile-room/README.md) checks
a bounded adaptation on defined CoCo 1/2 configurations. The examined historical
renderer targets CoCo 3; its compatibility does not follow from our example.

## Keep three kinds of position separate

A cell is one entry in the map. A logical position locates an actor within the
world. A display address locates bytes that draw part of that world.

| Quantity | PacDude example | What it answers |
| --- | --- | --- |
| Map row and column | One-byte entries, 80 bytes between row starts | Which scenery entry is here? |
| Logical actor position | Eight coordinate units per cell in `LEGAL` | Where can the actor move within this cell? |
| Display destination | `BLOCK` writes eight rows, 16 bytes per row | Where must the tile image be copied? |

These numbers describe different layouts. Eight logical units do not prove an
8×8-pixel tile. Sixteen copied bytes do not establish the pixel width without
the display encoding. Do not derive a CoCo 1/2 graphics mode from these values.

The source basis is `PAC2PT01.SRC`, `CNVRT2` 17170–17240 and `BLOCK`
17250–18330, plus `PAC2PT02.SRC`, `LEGAL` 19060–19420. All line references in
this guide use the five-digit numbers inside the original source, not editor
line numbers. The [source and reading record](#source-and-reading-record)
identifies the exact package.

## Store a room independently of its picture

PacDude defines `GRDBUF` at `$4000` (`PAC2PT01.SRC` 04430–04510).
`MAKMAZ`, 16260–16910, clears `$1900` bytes before it copies the level data.
It starts the destination at `GRDBUF + $46E`, copies 52 entries per row, and
advances the destination by 80 bytes between rows.

Our arithmetic gives 6,400 cleared bytes, or 80 rows of 80 one-byte entries.
The first copied entry is at row 14, column 14, with zero-based coordinates.
The loop copies 52 rows. Thus the level occupies a central 52×52 area inside
a padded map. The row stride remains 80, even inside that smaller area.
`MAKMAZ` also adjusts entries at offsets from `POWLOC` before returning.

`CNVRT2`, 17170–17240, calculates this map address:

```text
map address = GRDBUF + row × 80 + column
```

For example, row 14, column 14 gives `$4000 + 1134 = $446E`.
The next row at the same column is `$44BE`, 80 bytes later.
Using 52 as the stride would read the wrong entries after the first row.
These are calculated examples, not runtime observations.

For your own map, write down the width, height, entry size, and row stride.
A tightly packed map with one-byte entries can use its width as the stride.
Padding is optional. It does not replace a check that each requested row and
column is within the allocated map.

## Turn a tile number into drawing work

PacDude keeps map addressing separate from display addressing.
`CNVRT1` in `PAC2PT01.SRC`, 16920–17160, selects a mapped display page and
calculates a destination using the grid position, horizontal origin, and work
page. `CNVRT2` calculates the map address instead.

`BLOCK`, 17250–18330, selects tile data at an offset of `tile number × 128`
in the active source mapping. It copies eight rows of 16 bytes each.
It advances the destination by 256 bytes between rows. That is 128 bytes of
tile data, spread over eight destination rows rather than one contiguous span.

This gives a useful implementation boundary for an original game:

1. Read the tile number from the map.
2. Find that tile's image in your original artwork.
3. Calculate the display destination for the cell.
4. Copy each image row using the display's row stride.

For a proposed byte-aligned tile format, define `tile_row_bytes`, `tile_height`,
and `screen_row_bytes` from the selected mode. A compact image then needs
`tile_row_bytes × tile_height` bytes. Image row `r` starts at
`image_base + r × tile_row_bytes`; its destination starts at
`destination + r × screen_row_bytes`.

That formula is our proposed layout, not a transcription of PacDude.
Choose the actual pixel dimensions and encoding only after the
[graphics checks](../guidance/development.md#graphics-before-code).
A tile that starts partway through a byte needs additional packing or masking.
Start with byte-aligned tiles to keep the first renderer small.

## Redraw changes without losing the map

PacDude first builds its display through repeated `GRID` calls.
`FILSCN`, `PAC2PT01.SRC` 18340–18700, changes the screen-page state to populate
both buffers. This matters because an update to one buffer does not update
the other.

For subsequent drawing, `CENTMV` and `GRID`, 18890–20280, derive grid positions
from the centre coordinates. They compare these with saved positions for the
selected work page. A changed row or column causes an entering strip to be
drawn. The horizontal strip contains 14 map entries. Vertical processing uses
`HITOP` to choose its range.

`GRID` also handles horizontal wrapping and a mapped-page transition during
vertical drawing. Entries with the high bit set take special paths through
`POWTOP` or `POWBOT`. Those complete overlay routines were not examined for this
guide. The plain `BLOCK` copy is not an explanation of every visible tile.

For a first game, use a fixed room and redraw the complete background.
Treat this as our simpler adaptation. Once that works, redraw only cells whose
contents changed or whose pictures were covered by an actor. Restore those
cells from the current map before drawing actors again. See
[moving objects](moving-objects.md) for the related background problem.

A collectible must change map state as well as its picture. PacDude's player
code, `PAC2PT02.SRC` 08990–09980, changes a pair of map entries when collecting
a dot and prepares `REMDOT`. The interrupt path at 15950–16010 calls `REMOVE`,
19930–20380, to update display bytes. Erasing only the display would leave the
old map entries available for a later redraw.

In your adaptation, replace a collected item with its floor tile in the map.
Redraw that cell. Then move the player away and back. The item must remain gone.
If you later use two buffers, update each buffer before it becomes visible.

## Decide which positions permit movement

PacDude's movement test is more specific than a wall/passable lookup.
`LEGAL`, `PAC2PT02.SRC` 19060–19420, uses the candidate `XPOS` and `YPOS`.
For its intended nonnegative coordinate range, our reading gives:

```text
column = floor(x / 8)
row = floor(y / 8)
local_x = x mod 8
local_y = y mod 8
class = map[row × 80 + column] AND $1F
rule = table selected by LEGLOC, indexed by class
```

`LEGLOC` is defined at 00270. `LEGTAB` and `LEGTB2`, 02500–02810, provide the
rule bytes. `LEGAL` rejects zero. For `$FF`, it accepts only
`local_y = 7 - local_x`. For other nonzero values, it accepts only
`local_y = local_x`. The caller accepts equality through the condition flags.

For example, local position `(2, 2)` passes the latter rule. Position `(2, 5)`
passes the `$FF` rule. A zero rule rejects both. These examples follow from
the instructions; they are not tests we ran.

This constrains a point to a diagonal path through a logical cell. It does not
test a filled triangular area, the visible pixels, or the actor's full extent.
`BEPAC`, 07790–08980, tries the requested move and nearby alternatives in several
branches. If none qualifies, it restores the previous coordinates.
These small offsets do not establish safe movement at arbitrary speeds.

The rules can change. `BECAGE`, 07380–07560, writes particular `LEGTAB` entries;
control code at 13260–13280 clears those entries too. Initial table values alone
cannot describe every game state. `VALID`, 19430–19710, performs a related
lookup for an offset position but omits the within-cell comparison. Do not
replace `LEGAL` with `VALID` and assume the movement remains equivalent.

## Build a smaller original game

The following is **our original adaptation**, not PacDude's implementation.
The [tile-room example](../examples/tile-room/README.md) checks scripted
cell movement, walls, collection and return on defined NTSC, 32 KiB, non-T1
CoCo 1/2 configurations. Each target passes 42 complete framebuffer/map
checkpoints with guards and negative controls. It has no keyboard or victory
system. Visual appearance, smooth movement and physical hardware remain untested.
Start with a single room, original tiles, and one actor that occupies one cell.
Use cell-by-cell movement first. This avoids needing a pixel-sized collision
shape before the map and input loop work.

1. Define a small, asymmetric room with floor, wall, collectible, and exit tiles.
2. Define each tile's image and movement property separately.
3. Place the actor in a passable cell.
4. Draw every map cell, then draw the actor.
5. Convert an input direction into a candidate row and column.
6. Reject candidates outside the map before calculating an address.
7. Reject candidates whose tile property blocks movement.
8. Accept the remaining candidate as the actor's new cell.
9. Apply collection or exit rules to the accepted cell.
10. Redraw the background and actor from the resulting state.

Reject a left move at column zero before subtracting from an unsigned column.
Apply the same rule at the top edge. Check the right and bottom limits before
reading their candidates. This makes the boundary rule explicit instead of
relying on padding or accidental integer wrap.

Use a distinct property for movement rather than treating tile number zero as
inherently passable. Two pictures can share a movement rule. A door can change
its picture and rule together. The map remains the source for later redraws.

If you add smooth movement, define the actor's collision shape first.
An anchor-point test permits different movement from a rectangle test.
For a rectangle, test all map cells its proposed extent overlaps.
For moves that can cross a cell, test the intervening path or use bounded
substeps. Endpoint-only checks can skip a wall. These are proposed design
requirements, not behavior established by PacDude's small-step caller.

Leave scrolling until the fixed room works. Before adopting strip updates,
compare them with a complete redraw. A camera jump can reveal several rows or
columns; a routine that draws one strip does not prove that case works.

## Prove the adaptation on its selected target

These checks are proposals. None is a completed result for this guide.
Use the actual assembly and framebuffer where the renderer's behavior matters.

- Draw an asymmetric map with distinctive edge tiles. Compare framebuffer bytes
  with independently calculated rows, including the final row and column.
- Test movement in all four directions into walls, through passages, and beyond
  each map edge. Check actor positions and guard bytes around allocated buffers.
- Collect an item, leave its cell, and redraw the room. Check that the item stays
  absent from the map and display. Repeat for an opened door.
- If adding PacDude-style constraints, test all 64 local positions for each
  diagonal rule and the blocked rule. Include cell crossings and rule changes.
- If adding scrolling or two buffers, compare incremental output with full
  redraws after crossings, reversals, buffer changes, map edits, and camera jumps.
- Inspect the display and input on the declared emulator target. Measure timing
  there before claiming that an update method is fast enough.

Record build, emulator, visual, and physical-machine evidence separately.
A CoCo 3 source reading does not prove a CoCo 1 or CoCo 2 adaptation works.

## Source and reading record

The [PacDude Monster Maze source ZIP][pac] contains a `PacDude3D` directory.
The loader `PAC2.SRC`, 00040–00080, names PACDUDE2/PACDUDE-MONSTER MAZE and
credits Brian O'Neill, copyright 1992. Both main source headers name version
2.1A. Use the named source file and embedded line numbers for every citation.

The loader, `PAC2.SRC` 00110–01280, and main initialization,
`PAC2PT01.SRC` 04530–04980, use the CoCo 3 display and mapping machinery.
The examined drawing path depends on that machinery. Some routines also modify
their own instruction operands. This is not a drop-in CoCo 1/2 renderer or a
ROM-resident example.

Minimum RAM, complete memory allocation, ROM dependencies, interrupt safety,
and assembler compatibility remain unverified. We make no 128K or 512K
compatibility claim. No runtime results or measured performance follow from
this source reading.

The [research note](../guidance/tile-map-research.md) retains provenance,
alternative sources, and unresolved questions. Downloads and normalized text
remain under ignored `local/research/tile-maps/`; the archive and member hashes
are in `sources.json` and `members.json`. The cited passages were read directly.
No copyright listing or artwork is reproduced here. No reuse license was found
in the examined headers or archive member list. Obtain permission before using
that code or artwork in a distributable game.

[pac]: https://colorcomputerarchive.com/repo/Programming/Source/PacDude%20Monster%20Maze/PacDude%20Monster%20Maze%20source%20code%20(Brian%20O'Neill).zip
