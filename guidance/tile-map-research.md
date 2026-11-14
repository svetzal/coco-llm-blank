# Tile-map rendering and collision research

Read this note for the source selection and limits behind
[Build a room from tiles](../guides/tile-maps.md). It records a source reading,
not a port or runtime result. The strongest examined source is
Brian O'Neill's *PacDude Monster Maze*. It contains both a map-driven renderer
and movement checks against that map. Its display machinery is CoCo 3-specific;
this pass did not establish a corresponding CoCo 1/2 implementation.

No code, artwork or historical listing is included in this note. Downloads and
reading derivatives are under ignored `local/research/tile-maps/`. The companion
guide explains the examined routines and proposes an original fixed-room
implementation. No shared reference index, manifest or converter was
changed.

## PacDude Monster Maze

The [archive source ZIP][pac] contains a directory named `PacDude3D`, despite
being served from the Monster Maze directory. The loader `PAC2.SRC`, numbered
lines 00040–00080, identifies PACDUDE2/PACDUDE-MONSTER MAZE and credits Brian
O'Neill, copyright 1992. Both main source files identify version 2.1A. Do not
rename the package based only on its internal directory name.

Citations below use the five-digit **source line numbers embedded in the
original files**, not editor line numbers. The files have CR line endings.
Local `pac-text/*.SRC.txt` derivatives change only line endings; the ZIP and its
original members are retained. `PAC2PT01.SRC` and `PAC2PT02.SRC` contain different
program sections with repeated definitions. Read the named file, not whichever
version a search returns first.

### Map and rendering evidence

| Source file and numbered lines | Finding from the complete routine |
| --- | --- |
| `PAC2PT01.SRC` 04430–04510 | `GRDBUF` is based at `$4000`; screen/object buffers and task constants are separate definitions. |
| `PAC2PT01.SRC` 16260–16910, `MAKMAZ` | Clears `$1900` map bytes, selects level data, copies 52 entries per row with an 80-byte destination stride, and then changes entries at `POWLOC` offsets. |
| `PAC2PT01.SRC` 17170–17240, `CNVRT2` | Computes `GRDBUF + row * 80 + column`. |
| `PAC2PT01.SRC` 16920–17160, `CNVRT1` | Converts grid position to a display destination, including work-page selection, horizontal origin and byte offset. This is separate from map indexing. |
| `PAC2PT01.SRC` 17250–18330, `BLOCK` | Uses the tile number to select a 128-byte block and copies eight rows of 16 bytes each, with a 256-byte destination row stride. |
| `PAC2PT01.SRC` 18340–18700, `FILSCN` | Builds the initial display through repeated `GRID` calls and changes screen-page state to populate both buffers. |
| `PAC2PT01.SRC` 18890–20280, `CENTMV` and `GRID` | Derives grid position from the centre coordinates, compares it with saved positions for the selected work page, and renders an entering row or column when the grid position changes. |

The map size calculation is our derivation: `$1900` is 6,400 bytes, enough for
80 rows of 80 one-byte entries. The level-copy loop starts at offset `$46E`
(row 14, column 14) and copies 52 rows of 52 entries into that cleared area.
This is a padded map, not a 52-byte rendering stride.

`GRID` is substantive incremental-rendering evidence. Its horizontal strip
contains 14 map entries; vertical processing uses the `HITOP` state to choose
its range. The routine includes horizontal wrapping and a mapped-page transition
while advancing vertically. It also handles special high-bit entries through
`POWTOP`/`POWBOT`. Those overlays are not ordinary opaque `BLOCK` copies. Their
complete drawing routines were not reviewed, so no overlay recipe follows here.

Do not infer an 8×8-pixel bitmap tile from the coordinate shifts. The collision
coordinates use eight logical units per cell, while `BLOCK` writes 16 bytes
across and eight display rows. A port must establish the relationship between
world coordinates, pixel packing and display coordinates. This reading records
byte operations without converting them into an unverified screen-mode recipe.

### Collision evidence

The complete `LEGAL` routine in `PAC2PT02.SRC`, numbered lines 19060–19420,
provides the missing link between the map and movement. Read it with `LEGTAB`
and `LEGTB2` at 02500–02810, the `LEGLOC` definition at 00270, and the player
caller `BEPAC` at 07790–08980.

Our algebraic description of the instructions is:

1. Locate the cell at `GRDBUF + 80 * floor(y / 8) + floor(x / 8)` for the
   program's valid, nonnegative coordinate range.
2. Keep the low five bits of that map entry and index the table selected by
   `LEGLOC`.
3. A zero table entry rejects the candidate position.
4. For a nonzero entry, compare `y mod 8` with `x mod 8`. When the table entry
   is `$FF`, compare against `7 - (x mod 8)` instead.
5. Equality returns the condition that the player caller accepts.

This is a path constraint within a tile, not a whole-cell Boolean wall test,
not a filled triangular slope test, and not collision against visible pixels.
It tests a candidate position rather than the full object's silhouette.
`BEPAC` checks a requested move, tries nearby alternatives in several branches,
and restores the old coordinates if none qualifies. Its offsets are small;
this is not evidence for arbitrary-speed swept collision.

The table is mutable. `BECAGE`, numbered lines 07380–07560, changes particular
`LEGTAB` entries, and the later control code clears those entries too
(13260–13280). Therefore collision behavior cannot be reconstructed from the
initial table alone. `VALID` at 19430–19710 performs a related table lookup for
an offset position, but does not perform `LEGAL`'s within-cell comparison.
Do not describe these routines as interchangeable.

Map state also changes when dots are collected. The player code at 08990–09980
locates map entries, modifies the pair representing a collected dot, and prepares
`REMDOT`. `REMOVE` at 19930–20380 updates the corresponding display bytes.
The interrupt path at 15950–16010 invokes that update. This links a persistent
map change to screen maintenance; it is not merely erasing a dot from the screen.

### Target and reuse limits

The loader and main initialization use CoCo 3 display and memory-mapping
addresses. The examined rendering path switches mappings and relies on a
256-byte display stride. Some routines patch their own operands. These facts
make it unsuitable as a drop-in CoCo 1/2 renderer or a ROM-resident example.
See `PAC2.SRC` 00110–01280, `PAC2PT01.SRC` 04530–04980 and `CNVRT1`/`GRID`.

The exact minimum RAM, complete memory map, ROM dependencies, interrupt safety,
assembler compatibility and behavior outside the intended coordinate range
remain unverified. No claim of 128K or 512K compatibility follows from this
reading. No binary was assembled, loaded or executed.

The copyright notices establish authorship, not permission to redistribute.
No reuse license was found in the ZIP member list or examined source headers.
Archive availability does not license its code or art for starter examples.

## Ice Hockey does not fill the tile-map gap

The [Ice Hockey source ZIP][ice] contains `HOCKEYSR.DSK`. The extracted `H.TXT`
header credits **Lou Fiorino**, copyright 1983 Intellectronics, Ltd. That is the
author credit to use, rather than inferring an author from another
Intellectronics game.

The disk has seven `.TXT` files. They were extracted locally by following the
RS-DOS directory and granule chains, without executing disk contents. Original
bytes and normalized text are retained under `ice-text/`; `ice-extraction.json`
records member hashes. Citations here count physical lines after CR-to-LF
normalization, including blank lines.

- `H.TXT`, lines 99–138, `RINK`, draws fixed rink bands and shapes into the
  screen/background buffers. It does not iterate a tile-ID map.
- `SK.TXT`, lines 50–63, tests proposed player coordinates against `XLF`, `XRT`,
  `YTOP` and `YBOT` before storing them. The second player's analogous path is
  in the same routine. These are coordinate limits, not tile lookups.
- `SUBS.TXT`, lines 1–31, `PUK`, compares puck coordinates with fixed rink and
  goal limits, then changes movement or scores.
- `GR.TXT`, lines 35–44, `COPYBF`, copies the persistent background to the
  display. Its pixel functions describe four pixels per byte.

`H.TXT`, `SK.TXT`, `SUBS.TXT` and `GR.TXT` were read in full. This is useful
corroboration for the separate background method already discussed in
[rendering sources](rendering-sources.md), but the examined scene construction
and movement code do not justify a tile-map guide. It is an original-era CoCo
source; model-by-model CoCo 1/2 compatibility was not established here. No reuse
license or runtime result was established.

## Community and magazine leads

Hugo Dufort's [2015 object-design article][dufort-tiles] explicitly distinguishes
opaque tiles, stationary grid-aligned animated objects, moving sprites and
restoration buffers. Its THING section describes restoring a stationary object
by drawing its underlying tile again. This is a useful, narrow algorithmic
source for tile restoration on his CoCo 3 project. It is not an assembly listing.

His [March 2017 collision update][dufort-collision] says background collision is
grid-based and uses five or six contact points, while acknowledging remaining
bugs. The whole article was read. It does not identify those points or provide
the test algorithm, so it cannot support a collision implementation. Neither
article establishes CoCo 1/2 behavior, and neither downloaded page supplies a
code/art reuse license.

Other search results were excluded or left unexamined:

- Allen Huffman's [Arduino Pac-Man dot discussion][arduino] is about Arduino
  TVout. Its reference to a prior CoCo game does not make its tile algorithm
  a CoCo implementation. Do not promote it on the site's CoCo affiliation.
- William Barden Jr.'s *An A "maze" ing adventure*,
  [*The Rainbow*, February 1988][rainbow], printed page 171 onward, is a
  completed follow-up. The [legacy maze reading](legacy-tile-research.md)
  examines the full article and listings. It establishes room-state and
  movement logic, but no bitmap tile renderer or background restoration.
- The [ugBASIC scrolling-tilemap example][ugbasic] explicitly excludes its
  `COCO` target in the shown procedure condition. A CoCo 3 compile command
  does not establish CoCo 1/2 support. Its backend implementation was not examined.
- Cocos2d, the COCO vision dataset, household tile calculators and tile-puzzle
  advertisements were excluded. Search vocabulary alone is not source evidence.

## Adaptation proposal, not a historical implementation

PacDude justifies separating map lookup, tile drawing and movement rules. For a
small original CoCo 1/2 example, start with a fixed room and an explicit table
of tile properties. Use original tile art and choose dimensions only after
checking the selected display mode and byte packing. Retain the map as the
source for redraws. A whole-cell solid/passable rule would be **our simpler
adaptation**, not PacDude's diagonal-path algorithm.

Keep world position, cell position and display byte address distinct. Define
whether movement tests an anchor point or an object's extent. Add bounds checks
before indexing; do not depend on historical caller constraints or map padding
without stating and proving them. Leave incremental scrolling and mapped-page
rendering for a later, separately measured example.

Proposed evidence for an implementation based on the companion guide:

1. Render a small asymmetric map with original tiles. Compare the real assembly's
   framebuffer bytes with independently calculated expected rows, including the
   last row and column. Confirm the result visually on the selected target.
2. Exercise movement into each wall direction, through an open passage, at a
   corner, and outside all four map bounds. Assert positions and guard bytes,
   not merely that a collision helper was called.
3. Change a collectible or door in map state, redraw, move an object over it,
   and restore the background. Verify the old tile does not return.
4. If implementing a PacDude-style path rule separately, enumerate all 64 local
   positions for each diagonal orientation and the blocked class. Test movement
   across cell boundaries and changes to collision properties.
5. If adding incremental rendering, compare its framebuffer with a full redraw
   after horizontal/vertical crossings, direction reversals, buffer switches
   and map changes. Test a camera jump explicitly; one-strip updates are not
   evidence for multi-cell jumps. Measure on each claimed target.

These are proposed tests, not completed checks. CoCo 1, CoCo 2 and CoCo 3 remain
separate target claims. The companion guide is a source-backed explanation, not
a completed example. Navigation integration remains with the parent task.

## Retrieval and conversion record

The guide pass reread the cited PacDude routines directly. It checked the ZIP
hash against `sources.json`, the three cited source-member hashes against
`members.json`, and each normalized derivative against its original CR-ended
file. All matched. These are provenance checks, not execution tests.

Retrieval date: 2026-11-14. The original research pass recorded one successful
PacDude directory request and one successful ZIP request, with no retry loop.
The earlier HTTP 429 did not recur. The guide pass used those local files.
`sources.json` records exact URLs and SHA-256 hashes; `members.json` records
extracted ZIP-member hashes. Source archives were read as data only.

| Download | SHA-256 |
| --- | --- |
| PacDude Monster Maze source ZIP | `14be444700af1a75feca5211c2da25ce9ccc4727ac6f88d3681f390409c3fed8` |
| Ice Hockey source ZIP | `749722d6c66d2b577225296fb9718d74b125e56caeddb8f110862f53d702ad6d` |

No PDF conversion pages are recommended from the examined sources: PacDude is
text assembly, Ice Hockey is a disk-contained source set, and Dufort's articles
are HTML. Do not send these through Docling. For Barden conversion pages,
use the completed [legacy maze reading](legacy-tile-research.md). The tokenized PacDude BASIC files were not decoded or
used as evidence. No source image was needed for the plain-text assembly paths.

[pac]: https://colorcomputerarchive.com/repo/Programming/Source/PacDude%20Monster%20Maze/PacDude%20Monster%20Maze%20source%20code%20(Brian%20O'Neill).zip
[ice]: https://colorcomputerarchive.com/repo/Programming/Source/Ice%20Hockey/Ice%20Hockey%20source%20code%20(Intellectronics).zip
[dufort-tiles]: https://coco3game.wordpress.com/2015/04/07/planning-for-the-road-ahead-of-palettes-and-graphical-objects/
[dufort-collision]: https://coco3game.wordpress.com/2017/03/05/feel-the-floor-kim-youre-not-a-ghost-anymore/
[arduino]: https://subethasoftware.com/2014/02/13/arduino-pac-man-part-5-dot-dilemma/
[rainbow]: https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow%2C%20The%20%28OCR%29/The%20Rainbow%20Vol.%2007%20No.%2007%20-%20February%201988.pdf
[ugbasic]: https://ugbasic.iwashere.eu/example/tileset_example_05
