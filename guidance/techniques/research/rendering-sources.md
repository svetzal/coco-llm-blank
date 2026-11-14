# Rendering sources examined

Use this note to find direct evidence for background restoration, transparent
objects and collision shapes. Start with the
[moving-object guide](../moving-objects.md) for the current implementation
baseline. The sources below extend the research. Neither historical program was
built or run during this reading.

Two sources earned detailed reading. Dunkey Munkey exposes a working game's
background model in assembly source. GrafExpress explains a different
restoration
method and separates an object's visible shape from its collision shape. Neither
reading establishes a reusable, tested assembly implementation of masked sprites
for this starter. No masked-object guide is published on that basis yet.

## Dunkey Munkey: restore from a persistent background

[Download the source ZIP from the archive][dunkey]. The archive filename credits
Harvey Brofman and Cercomp. The source header instead credits Harvey Brofman and
Intellectronics, dated June 24, 1982. Keep that distinction when citing it; the
archive label does not establish the original publisher.

The ZIP contains a disk image and a `DunkeyMunkey_Source` directory. The
following
references are to text files in that directory. Line numbers count every line,
including blank lines, from one. Routine names remain useful if a reader changes
line endings or formatting.

| Question | Direct evidence | What the code establishes |
| --- | --- | --- |
| Where does the background live? | `KONG.TXT`, lines 98–99, `SCRSTA` and `BACGRN` | Separate display and background buffers, each 6,144 bytes apart. The two buffers alone cost 12,288 bytes. |
| How is the whole scene restored? | `GRAPH2.TXT`, lines 50–59, `COPYBF` | Copies the background buffer into the display buffer. |
| How is an old object removed? | `GRAPH2.TXT`, lines 314–345, `ERASE` | Copies a rectangular byte region from the background buffer to the corresponding display region. It does not fill the region with a flat colour. |
| How is movement drawn? | `GRAPH2.TXT`, lines 194–282, `MOVE` | Uses `ERASE` and `SHAPE`; some movement paths restore an exposed strip instead of the whole old object. |
| What happens when scenery changes? | `SCREN2.TXT`, lines 308–316 | Removes a rivet from game state, changes the background with `ERASEB`, then restores the display region with `ERASE`. |
| How is new scenery installed? | `SCREN2.TXT`, lines 334–355 | Changes the background with `ERASEB` and `BSHAPE`, then copies it to the display. |

The important distinction is between a persistent background and a snapshot
captured just before an object is drawn. This game restores from the former.
Removing scenery must therefore change that background too, or a later restore
can bring the old scenery back. That consequence is our explanation of the
listed code paths, not a quotation from an accompanying article.

This source does **not** establish transparent objects. `SHAPE` and `BSHAPE`
(`GRAPH2.TXT`, lines 139–174) choose the destination buffer and insert each
shape
pixel. The examined loop has no transparent-colour skip. `SETX`, lines 83–106,
masks a packed pixel within a byte; that operation alone is not an object
transparency mask. Do not label this an AND/OR masked-sprite renderer.

The examined source uses 32-byte rows and two-bit pixel operations. Do not
transplant
its pixel code into the starter's two-colour screen without changing the
packing.
The dated source does not establish CoCo 2 or CoCo 3 compatibility. No complete
RAM, ROM, video-mode or assembler-compatibility assessment was made. The
archive's
assembly syntax also differs from the starter's LWTOOLS examples.

### Adaptation to investigate

An original starter example could keep a separate background and restore old
object regions from it. That is a design proposal, not a tested port. Before
calling it correct, verify clipped rectangles, byte alignment, overlapping
objects, scenery changes beneath an object, and the RAM cost on each target.
Restoring one old object can also erase another currently drawn object. The
source excerpts do not prove that arbitrary object overlap is handled safely.

## GrafExpress: save regions before drawing objects

[Read GrafExpress 2.0 by Sundog Systems][grafexpress], copyright 1991. This is a
programming-system manual, not the source listing of its sprite engine. The
examined scan has 53 PDF pages. Printed page 1 is PDF page 6.

Its graphics systems, GE16 and GE256, have different pixel packing and display
requirements. Printed page 2 (PDF 7) describes GE16's 16-colour graphics and
limits
GE256's display method to composite monitors or colour televisions. Do not infer
an ordinary 256-colour hardware mode or apply these routines to the CoCo 1/2
baseline. The techniques below concern software object management, not a
portable
register setup.

### The restoration sequence is explicit

Printed page 22 (PDF 27), under the explanation of nonsticky sprites, gives the
sequence:

1. Save the screen regions that the next sprites will cover.
2. Draw all the sprites.
3. Display the completed screen.
4. Restore the previously displayed screen from its saved regions.

The last step uses a different set of saved regions from those belonging to the
newly displayed screen. The manual describes two sets of restoration buffers.
It also explains the extra memory and copying cost. This is direct algorithmic
evidence for saving the background before drawing any sprites in a frame.

A useful original adaptation would track saved regions separately for each
screen
buffer. Reusing the newest saved regions to repair the previous screen would mix
two different frames. That error case is our inference from the documented
sequence. No starter implementation or timing measurement currently proves this
adaptation.

### Appearance, collision shape and frame state are separate

The manual provides several contracts worth retaining in a game design:

| Contract | Printed page / PDF page | Practical consequence |
| --- | --- | --- |
| Transparent pixels and solid pixels describe different properties. | 3 / 8 | A visible silhouette need not define the entire collision shape. |
| A transparency colour makes matching pixels both transparent and nonsolid. | 15 / 20 | This particular picture operation ties the two properties together. It is not a universal rule for engines. |
| A rectangle picture is transparent but solid. The manual suggests it for collision against scenery drawn separately. | 16 / 21 | Walls can have collision geometry without an extra visible sprite. |
| Sprite changes affect collision checks immediately, but reach the display only at `SHOW` or the switch command. | 17 / 22 | Collision code must say whether it tests the upcoming state or the currently displayed frame. |
| Disabled sprites and nonsolid pixels do not participate in `HIT`. | 17 / 22 | Visibility and collision participation need explicit rules. |
| GE16 sprite x positions round down to an even pixel. | 18 / 23 | Do not promise arbitrary single-pixel horizontal movement from this engine's contract. |

Printed page 15 (PDF 20) also warns that initial picture definitions empty the
sprite buffers. Define pictures before using sprites. Its doubled storage cost
for transparent pictures is an engine-specific statement, not a memory estimate
for a new mask format. The manual does not expose the assembly mask operation on
these pages.

These findings justify design guidance about restoration and collision state.
They do not yet justify a recipe for mask generation, pixel-perfect collision,
a tile collision map, or a particular assembly blend loop.

## Reading record and limits

For Dunkey Munkey, the rendering routines in `GRAPH2.TXT` were read together
with
the memory definitions in `KONG.TXT` and the cited scenery callers in
`SCREN2.TXT`.
This was a focused source reading, not a review of every game routine. The
bundled
disk was not executed. No errata were located or runtime correctness asserted.

For GrafExpress, the cover, copyright page, addendum, contents, conceptual
section,
picture and sprite commands, and the restoration discussion were inspected as
rendered page images. In particular, PDF pages 7–8, 20–23 and 26–27 support the
findings above. PDF 27 is essential; the earlier introduction's speed claims are
not a substitute for its algorithm description. The bundled front addendum was
read, but no correction to these sprite contracts was found there. This is not
proof that no later errata exist.

No runtime, visual, physical-hardware or performance validation was done. The
existing opaque moving-object example does not validate either historical
restoration method.

### Leads not promoted

- Hot CoCo Graphic Master advertisements and product-review search matches did
  not establish a rendering algorithm. They were not used as technical evidence.
- A Dragon User sprite article lead was not promoted to a CoCo recipe. The full
  article and its machine assumptions remain unexamined.
- The archive's Ice Hockey source directory is a possible follow-up. Its ZIP was
  not downloaded or reviewed, so no technique is attributed to it here.
- The Pac Dude Monster Maze source directory returned an HTTP 429 response.
  Its contents were not inspected.
- General search matches for Cocos2d, the COCO vision dataset and non-CoCo
  TRS-80
  graphics hardware were excluded as different systems.

No directly examined tile-map or tile-collision implementation resulted from
this pass. Magazine coverage remains incomplete; a search match is not a
completed
source reading. These two sources add useful detail without filling that gap.

## Retrieval and reference coverage

The ignored directory `local/research/masked-tiles/` holds the downloaded PDF,
source ZIP, extracted source text, rendered pages and `sources.json` with exact
URLs and SHA-256 hashes. No source listings or page images are included in
tracked
files.

| Source | SHA-256 |
| --- | --- |
| GrafExpress PDF | `d6c569ab8c846167f28622e3e86b8a46d64770a9b600f5346af3631943189034` |
| Dunkey Munkey ZIP | `f2dd97ac73813e9191e5f396eb24474fa95ec1c3d5cfd6230b77002aea2f06ac` |

GrafExpress is checksum-pinned in the manifest as `grafexpress`. Selected local
conversion covers PDF pages 7–8, 20–23 and 26–27. Keep PDF 4 with the original
download for its copyright and software-distribution terms. The conversion
preserves the main restoration sequence on PDF 27, but damages
some sync prose there, the final sprite sentence on PDF 7, the scenery hint on
PDF 21, and command symbols on PDF 22. Check the rendered originals for those
passages and all uncertain command syntax. Do not package its engine as starter
code: the examined license
does not grant unrestricted redistribution with users' programs.

Dunkey Munkey is a source-ZIP candidate, not a PDF conversion candidate. A
future
local-source download path would need to preserve member paths and offer direct
text search. Do not put it through the PDF conversion pipeline or copy its code
into an example. No redistribution license was found in the examined source.

[dunkey]: https://colorcomputerarchive.com/repo/Programming/Source/Dunkey%20Monkey/Dunkey%20Munkey%20Source%20(Harvey%20Brofman)%20(Cercomp).zip
[grafexpress]: https://colorcomputerarchive.com/repo/Documents/Manuals/Programming/GrafExpress%202.0%20(Sundog%20Systems).pdf
