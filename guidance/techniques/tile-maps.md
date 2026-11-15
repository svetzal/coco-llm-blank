# Build a room from tiles

Read this when a game has repeated scenery or items that change one cell of a
room. Store the room as tile numbers. Let each number select a picture and,
through a separate table, a movement rule.

We measured the method on CoCo 1 and CoCo 2 in RG6, in the
[tile-room example](../../examples/tile-room/README.md). The main historical
source, Brian O'Neill's *PacDude Monster Maze*, is a CoCo 3 program. We read
it but did not run it. Its drawing path does not transfer to CoCo 1/2.

Each claim below has one of these labels:

- **Published:** what a cited source does, from our reading of it.
- **Adaptation:** our design, which the example uses.
- **Derived:** our arithmetic from cited values. We did not run it.
- **Measured:** a result of `coco.py check`, which you can run again.
- **Proposal:** our design, which nothing tests.

## Keep three kinds of position separate

A map cell, an actor position and a display address are different values.

| Quantity | PacDude | What it tells you |
| --- | --- | --- |
| Map row and column | One-byte entries, 80 bytes between row starts | Which scenery is here |
| Logical actor position | Eight coordinate units for each cell, in `LEGAL` | Where the actor can go in the cell |
| Display destination | `BLOCK` writes eight rows of 16 bytes | Where to copy the tile picture |

**Published.** The values come from `PAC2PT01.SRC` (`CNVRT2` 17170–17240,
`BLOCK` 17250–18330) and `PAC2PT02.SRC` (`LEGAL` 19060–19420). Line numbers
are the five-digit numbers in the source files. Eight units do not prove an
8×8-pixel tile. Do not derive a CoCo 1/2 mode from these values. Use the
[graphics checks](../starter/development.md#graphics-before-code).

## Store the room apart from its picture

**Published.** PacDude puts `GRDBUF` at `$4000` (`PAC2PT01.SRC`
04430–04510). `MAKMAZ` (16260–16910) clears `$1900` bytes. It copies 52
entries for each row from `GRDBUF + $46E`, with 80 bytes between rows.
`CNVRT2` calculates `GRDBUF + row × 80 + column`.

**Derived.** `$1900` is 80 rows of 80 entries. The level is a 52×52 area from
row 14, column 14 (`$446E`). A stride of 52 reads wrong entries after one row.

For your map, write down the width, the height, the entry size and the row
stride. Padding does not replace a bounds check of each row and column.

## Turn a tile number into drawing work

**Published.** `CNVRT1` (16920–17160) calculates a display destination from
the grid position, the horizontal origin and the work page. `BLOCK` selects
the picture at `tile number × 128` in the active mapping. It copies eight rows
of 16 bytes, with 256 bytes between destination rows.

**Adaptation.** Keep four steps apart:

1. Read the tile number from the map.
2. Find the picture of that tile through a table.
3. Calculate the display destination of the cell.
4. Copy each picture row with the row stride of the screen.

Tile-room uses one-byte map entries with an 8-byte row stride. Its scenery IDs
are floor 0, wall 1, collectible 2 and exit 3. The actor picture is ID 4 and is
never in the map. A table of four bytes gives the movement rule of each scenery
ID. Each picture is eight rows of one byte.

**Derived.** In RG6, cell column `c`, row `r` starts at `$0400 + r × 256 + c`.
Picture rows are 32 bytes apart. The lower-right cell starts at `$0907`. The
[example README](../../examples/tile-room/README.md#source-facts-and-provenance)
cites the RG6 facts.

**Proposal.** For wider tiles, copy `tile_row_bytes` for each picture row.
A tile that starts inside a byte needs masks, so start with byte-aligned tiles.

## Redraw from the map

**Published.** `FILSCN` (`PAC2PT01.SRC` 18340–18700) fills both buffers
with repeated `GRID` calls. `CENTMV` and `GRID` (18890–20280) compare the grid
position with the saved position of the work page. After a change, they draw
the strip of 14 entries that comes into view. Entries with bit 7 set go
through `POWTOP` or `POWBOT`, which we did not read.

**Published.** When the player takes a dot, the player code (08990–09980)
changes a pair of map entries. Then `REMOVE` (19930–20380), called from the
interrupt path (15950–16010), changes the display bytes. The map change keeps
the dot gone.

**Adaptation.** Tile-room redraws the full screen from the current map at
each move, then draws the actor. No saved background can bring back a
collected item. This does more work than a redraw of changed cells only. It
does not wait for vertical blanking, and we did not measure its time. The map
is 48 bytes and the five pictures are 40 bytes.

**Proposal.** After the full redraw works, redraw only the cells that changed
or that an actor covered. Restore them from the map before you draw actors.
For a scroller, key each screen cell with its world cell and a revision of its
content. Then a camera move and a door change each cause a redraw. Gloom's
column records suggested this key
([animation guide](animation.md#decide-what-to-redraw)).

## Decide which positions permit movement

**Published.** `LEGAL` takes the candidate `XPOS` and `YPOS`. For nonnegative
coordinates, our reading of its instructions is:

```text
column = floor(x / 8)
row = floor(y / 8)
local_x = x mod 8
local_y = y mod 8
rule = table at LEGLOC, indexed by (map[row × 80 + column] AND $1F)
```

A zero rule rejects the position. The rule `$FF` accepts only
`local_y = 7 - local_x`. Other rules accept only `local_y = local_x`. In the
same file, `LEGLOC` is at 00270, and `LEGTAB` and `LEGTB2` are at
02500–02810. This is a diagonal path through each cell, not a wall test.

`BEPAC` (07790–08980) tries the requested move and some near alternatives.
If none passes, it restores the old coordinates. `BECAGE` (07380–07560) and
control code (13260–13280) change `LEGTAB` entries during play. `VALID`
(19430–19710) omits the test in the cell, so it is not a copy of `LEGAL`.

**Adaptation.** Tile-room moves one cell at a time. It rejects a move off the
map before it calculates an address. Then the rule of the tile accepts or
rejects the move. A collectible becomes floor in the map when the actor moves onto it.
Do not treat tile number zero as passable by default.

**Proposal.** For smooth movement, define the collision shape of the actor
first. Test every cell that it covers. For a move that can cross a cell, test
the path or use short substeps.

## What the tile-room example checks

**Measured.** `uv run python scripts/coco.py check examples/tile-room` runs
41 scripted moves on CoCo 1 and CoCo 2. Both are NTSC, 32 KiB, normal-clock,
non-T1 configurations of the pinned instrumented XRoar. At each of the 42
frames, the check compares these items with `expected.py`:

- all 6,144 screen bytes and every map byte
- four guard bytes, the actor position, the accept flag and the script step
- all 98,304 samples of the rendered 512×192 frame

The moves hit all four edges and walls from four sides. They collect the
item, leave, return and cross the exit. `expected.py` walks the room from text
drawings and does not read the assembly, the PNG or RAM. Integration tests in
`scripts/coco_spec.py` change one pixel, write past the screen, remove the
actor picture and convert 16×16 pictures. Each one must fail.

The check does not show a television, a physical CoCo or keyboard input. It
does not measure timing or cover PAL, T1 VDGs or the CoCo 3.

## What other sources show

We read the cited parts of these sources. We ran none of them.

| Source | What it shows for tiles |
| --- | --- |
| William Barden Jr., "An A 'maze' ing Adventure", *The Rainbow* 7:7, February 1988, PDF 173–183 (printed 171–181) | A room graph for 16K ECB (PDF 173). Each room value holds six opening bits (Figure 6, PDF 176). NEWMAZE redraws the full view from room data with LINE, CIRCLE and PAINT. It checks each move against the same bits (lines 340–690, PDF 181–182). FINDMAZE opens each door from both sides (lines 340–410, PDF 182). No bitmap tiles. |
| Benjamin W. Brunotte, "Rat Maze", *The Rainbow* 4:10, May 1985, PDF 107–120 (printed 105–118) | A 16K ECB passage grid: west 1, north 2, east 4, south 8, border 100 (PDF 107–109). The overhead view draws the outer top and left edges once, then the south and east edges of each cell (Listing 1, lines 1200–1250). Movement reads the same values (lines 1020–1180). No tile pictures. |
| Bob Withers, Stephen O'Dea and others, *Sea Search* (`ADVENT01.ASM` 380–405, `ADVENT.ASM` 409–556) and *Calixto Island* (`ADVENT01.ASM` 446–477, `ADVENT.ASM` 408–543) | A room record holds one background ID and eight overlay slots. A decoder writes the background bytes. Each overlay has a row, a column and a byte width. It is written with a 32-byte stride and whole-byte stores. Not a tile grid. |
| Harvey Brofman, *Dunkey Munkey*, `SCREN2.TXT` 674–735, `GRAPH2.TXT` 83–180 | Placement records repeat a girder shape pixel by pixel. Not a packed tile copy. Our reading of the clear and copy loops (`GRAPH2.TXT` 34–59): they do one more two-byte step at the buffer end. Use exclusive bounds. |
| Lou Fiorino, *Ice Hockey* (`SK.TXT` 50–63). *Droid War* (`DroidWar.asm` 22–73, 533–551). John Crawford, *Space Raiders* (`SR3.TXT` 1–8, 657–759) | Coordinate limits, semigraphics shapes and a CoCo 3 object list. None reads a tile map. |
| Hugo Dufort, [coco3game blog, April 2015][dufort] | On his CoCo 3 project, restore a stationary object by drawing its underlying tile again. An article, not a listing. |

**Derived.** Prose and listings disagree. Barden's PDF 179 says to AND X and
A, but line 590 tests C and A. His PDF 180 says that the program refuses an
exit until it has used about 30 percent of the rooms. Lines 490, 630 and 700
do not support that. Rat Maze's printed 108 says that line 1230 draws the
right side, but it draws the bottom edge (PDF 114).

We found no correction in the `rainbow-index` entries (PDF 19, 22, 28, 53,
57, 62–63, 109, 195 and 204), `rainbow-1988-04` (PDF 14 and 30), or the June
and July 1985 corrections (PDF 228 and 231).

**Proposal.** For a maze without textures, Rat Maze's shared-edge drawing
fits. Store reciprocal openings, then let each cell draw its south and east
walls. Refuse a map whose two sides of one opening disagree.

## Open questions

**We stopped the historical tile-ID hunt.** We looked for a CoCo 1/2 program
that goes from grid cell to tile ID to packed picture to bitmap address.
PacDude has that chain, but on the CoCo 3. The other sources above, and Cubix,
do not have it. This finding is about those sources only, not the archive.

Reopen the hunt only when both of these are true:

- A builder needs something that the tile-room method does not give.
- A credit, listing or index entry shows that a named CoCo 1/2 program or
  article draws bitmap tiles from a map.

A title or a directory name is not a lead. Read only the cited routines of
that lead.

Nothing tests dirty-cell redraw, strip scrolling, two buffers, smooth
movement, PacDude's diagonal rule, overlays or transparent tiles. For each,
compare the result with a full redraw from the map. Include crossings,
reversals, map changes and camera jumps of more than one cell.

## Sources

- Brian O'Neill, *PacDude Monster Maze* 2.1A, 1992, source ZIP
  ([archive][pac]), SHA-256
  `14be444700af1a75feca5211c2da25ce9ccc4727ac6f88d3681f390409c3fed8`.
  `PAC2.SRC` 00040–00080 names the game and author. The loader (`PAC2.SRC`
  00110–01280) and the setup (`PAC2PT01.SRC` 04530–04980) use the CoCo 3
  display and mapping. Some routines change their own operands.
- *The Rainbow* February 1988 ([archive][feb]), SHA-256
  `7e870a622d5104fc4f1298f384a3163c0304f4ed8d97e809ade83efa5794ce2d`.
- *The Rainbow* May 1985 ([archive][may]), SHA-256
  `dc36fcbfbb3e651f4a4cea9ebd51da0e10b03a67e5ed252ecd5de812a05e4f36`.

Neither issue is in `resources.json`, so they have no resource ID. We read
the page images of both articles and their complete listings. Ignored
`local/research/` keeps the other ZIP hashes in `tile-maps/`,
`legacy-tiles-game-sources/` and `tile-source-followup/`. We found no reuse
licence in these sources. The example uses original code and art.

[pac]: https://colorcomputerarchive.com/repo/Programming/Source/PacDude%20Monster%20Maze/PacDude%20Monster%20Maze%20source%20code%20(Brian%20O'Neill).zip
[feb]: https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow%2C%20The%20%28OCR%29/The%20Rainbow%20Vol.%2007%20No.%2007%20-%20February%201988.pdf
[may]: https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow%2C%20The%20%28OCR%29/The%20Rainbow%20Vol.%2004%20No.%2010%20-%20May%201985.pdf
[dufort]: https://coco3game.wordpress.com/2015/04/07/planning-for-the-road-ahead-of-palettes-and-graphical-objects/
