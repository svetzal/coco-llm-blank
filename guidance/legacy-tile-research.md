# Legacy CoCo maze and tile research

Read this note when choosing legacy CoCo map-rendering sources. It covers
Barden's February 1988 maze and a bounded follow-up of three game-source
archives. It supports [tile-map research](tile-map-research.md) without
repeating the PacDude or Ice Hockey investigations. The game-source pass finds
bitmap overlay placement, but does not close the CoCo 1/2 tile-ID map gap.

William Barden Jr.'s *An A 'maze' ing Adventure* is a useful source for a
room graph, direction-dependent views and movement permissions. It does not
supply bitmap tiles, a tile-copy loop or background restoration. The complete
article and both BASIC listings were read, including their page images.
No implementation, emulator execution, timing measurement or hardware test
was performed.

## Source and page mapping

The source is [The Rainbow, February 1988, OCR edition][feb], retrieved on
2026-11-14. The download succeeded through curl despite the earlier web-tool
size limit. It is 27,473,575 bytes. Its SHA-256 is
`7e870a622d5104fc4f1298f384a3163c0304f4ed8d97e809ade83efa5794ce2d`.

PDF pages are one-based and include the covers. These offsets were checked
against the printed page labels, not extrapolated from another issue.

| PDF pages | Printed pages | Complete relevant material |
| --- | --- | --- |
| 173-174 | 171-172 | Introduction, controls, arrays, Figures 1-5. |
| 176 | 174 | Room bits, Table 1, Figure 6, condensed drawing example. |
| 178-180 | 176-178 | Drawing, orientation, movement, generation and disk workflow; Figure 7. |
| 181 | 179 | Article conclusion and NEWMAZE lines 100-720. |
| 182 | 180 | NEWMAZE lines 730-1170; FINDMAZE lines 100-500. |
| 183 | 181 | FINDMAZE lines 510-840, through its end. |

PDF 175 and 177 are intervening advertisements. Both listings must be read
across their column and page breaks. Printed page 180 alone contains neither
complete program.

Copyrighted PDFs, extracted text, page images and evidence records remain
under ignored `local/research/legacy-tiles/`. `evidence.json` records source
URLs, hashes and reading scope; `derivative-hashes.json` records the local
derivatives. Existing index and April PDFs were read in place. No shared
manifest, index or conversion state was changed. No reuse license was found
in the examined article; archive availability does not establish one.

## Machine assumptions

PDF 173 explicitly labels the article **16K ECB**. PDF 174 explains Extended
Color BASIC arrays. NEWMAZE uses PMODE 4, SCREEN, LINE, CIRCLE and PAINT;
PDF 176's condensed example identifies a 256 by 192 display. The examined
listings do not require CoCo 3 graphics commands or memory mapping.

This is evidence for a legacy CoCo BASIC technique, rather than a CoCo 3-only
source. However, the printed 16K label is not a measured minimum for every
maze size. FINDMAZE accepts variable dimensions and allocates arrays; the
complete workflow saves and reloads a named disk file through channel 1
(PDF 180-183). Treat the supplied workflow as requiring disk BASIC/storage.
Do not promise that the suggested 5 by 5 by 5 maze fits a particular 16K
configuration without testing it. No ROM-version, PAL/NTSC, clock-rate or
model-by-model compatibility result was established.

The original Barden pass downloaded no additional game archive. The separate
three-candidate follow-up below investigates the bitmap-rendering gap directly.

## What the programs actually do

The world is `R(Z,X,Y)`, with Z for height, X for width and Y for depth.
The playable indices start at one even though BASIC allocates zero indices.
Each value represents openings, not a bitmap tile identifier. PDF 176,
Figure 6, assigns the six bits to up, down, behind, left, straight ahead and
right, with weights 32, 16, 8, 4, 2 and 1. Horizontal meanings use a fixed
north-facing reference. PDF 178's Figure 7 and conversion table explain how
the observer's orientation changes which opening appears on which wall.

NEWMAZE, PDF 181-182, provides the decisive rendering evidence:

- Lines 340-470 clear the graphics screen, draw its border, read the current
  room, draw a fixed perspective outline, and conditionally draw openings.
- Lines 710-1170 draw those shapes with LINE, CIRCLE and PAINT. There is no
  tile atlas, bitmap block transfer, saved rectangle or background buffer.
- Lines 480-590 accept a movement key, translate it according to orientation,
  and reject movement when the corresponding bit is absent from the room.
- Lines 600-690 update position and orientation, detect an exit, and return
  to the full room redraw for a move that remains inside the maze.

The screen is reconstructed from persistent room data after movement. That
is useful model-driven redraw evidence, but it is not restoration beneath a
moving sprite. The player changes rooms in discrete steps; there is no
pixel-level actor extent, wall intersection or swept collision algorithm.
The article's proposed monster and temporary wall marks on PDF 181 are future
embellishments, not implemented features.

FINDMAZE, PDF 182-183, constructs the room data separately. Lines 250-330
randomize openings and close the outside boundary. Lines 340-410 add the
matching opening to adjoining rooms so a doorway works in both directions.
Lines 550-740 attempt a random path, reject previously visited trial rooms,
open reciprocal doors along the path, record directions and stop at an exit.
Lines 770-840 save dimensions, room values and the route string. This is
graph generation and serialization, not tile rendering.

## Corrections and reading hazards

No specific published erratum was located. The [searchable Rainbow index][idx]
entries for this title and FINDMAZE/NEWMAZE carry no correction annotation
(PDF 53, 57, 62-63; later name indexes at 195 and 204). Targeted archive-domain
searches for the program names with correction/bug terms found no relevant
correction. Search results mentioning an April correction led to the actual
[April 1988 corrections][apr], PDF/printed pages 14 and 30. Both correction
blocks were read as text and images; neither corrects this maze article.
The SMOOTHY correction there belongs to another program. This bounded search
does not prove that no later erratum or Delphi correction exists.

Keep these source inconsistencies separate from published errata:

- PDF 178 refers to drawing code through line 1700; the complete NEWMAZE
  listing ends at 1170. Cite the actual listing ranges.
- PDF 179's prose says to AND X and A, while NEWMAZE line 590 tests C and A.
  C is the current room value. The same paragraph misprints the direction
  enumeration; PDF 178 and the listing establish zero through three.
- PDF 180 describes rejecting an early exit until about 30 percent of rooms
  have been used. In the listing, JE counts coordinate entries in triples
  (lines 490 and 700), yet line 630 compares JE with room count divided by
  three. Our reading therefore does not support the prose's percentage or
  its claim of roughly 38 rooms for a 5 by 5 by 5 maze. This is static analysis,
  not a reproduced runtime defect.

Other adaptation limits are visible in the listing. The visited-coordinate
array has a fixed dimension of 200, and rejected trial moves retry randomly
without a visible backtracking or exhaustion branch. A reusable generator
needs its own capacity and termination argument. Do not claim the historical
generator handles arbitrary dimensions or always completes.

The OCR repeatedly damages zeroes, punctuation and comparison operators.
For example, PDF 176's image says 256 by 192 where extracted text damages the
number. Figures and all listing pages were checked visually; the text
derivatives are navigation aids, not executable transcriptions.

## Practical guide implications

Retain this as supporting evidence for a room-map guide: store world state
separately, derive the view from it, and use the same opening rules for
movement. A test of reciprocal doorways should cover travel out and back,
all four headings, vertical movement and the exit boundary. Those are
proposed checks for a future original implementation, not completed tests.

Do not use this article to fill the CoCo 1/2 tile-rendering or restoration
gap. A fixed two-dimensional tile room with original art would still be our
adaptation and would need independent byte-packing, rendering and restoration
evidence. The title's word "maze" was a search lead, not proof of those methods.

If the parent chooses to add selective Docling conversion, the candidate
ranges are PDF **173-174, 176, 178-183**. For a minimal rendering/movement
study, use **176, 178-179, 181-182**, with 173 for the target label. Add
180 and 183 only when examining generation and storage. Preserve page images
with conversion because the dense listings and perspective diagrams carry
information that OCR loses. No conversion of the entire issue is warranted.

[feb]: https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow%2C%20The%20%28OCR%29/The%20Rainbow%20Vol.%2007%20No.%2007%20-%20February%201988.pdf
[idx]: https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow,%20The%20-%20Text%20Searchable%20Index/The%20Rainbow%20-%20Text%20Searchable%20Index.pdf
[apr]: https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow,%20The%20(OCR)/The%20Rainbow%20Vol.%2007%20No.%2009%20-%20April%201988.pdf

## Three game-source candidates

This follow-up read actual assembly routines from three archives on
2026-11-14. The selection was bounded before inspection: Droid War for its
small repeated graphics, Dunkey Munkey for repeated platform scenery, and
Sea Quest for room graphics. Directory names were discovery hints only.
No Hot CoCo or Undercolor survey was repeated.

| Candidate | Result for bitmap tiles and maps |
| --- | --- |
| [Droid War][droid-src] | Rejected: repeated semigraphics shapes, not a bitmap tile-ID map. |
| [Dunkey Munkey][dunkey-src] | Rejected for packed tile copying: placement records repeat shapes through per-pixel writes. Useful scene-description evidence. |
| [Sea Quest / Sea Search][sea-src] | Partial: compressed bitmap overlays with row-stride writes and room records. Rejected as a regular tile-ID grid renderer. |

These citations use **physical lines after CRLF and CR normalization to LF**,
including blank lines. They are source-file citations, not PDF pages. No OCR,
page-image interpretation or Docling conversion was needed. Only the named
routines and supporting data were examined, not every game path or asset.
No assembly, emulator run, framebuffer comparison, timing, rendered-output
check or physical-machine test was performed.

### Droid War: copying does not establish bitmap tiles

`DroidWar.asm` lines 22-73 clear the display, explicitly label their mode as
SemiGraphics 24, repeat a two-byte-wide droid pattern with a 32-byte stride,
and draw fixed barriers. Lines 271-285 and 304-318 copy the ship patterns
from `SHIPR`/`SHIPL` for nine rows. The source tables are at 572-604.
Those are real copy loops, but their stored values and declared display mode
belong to semigraphics. The inspected renderer does not fetch a tile identifier
from a world grid. `LBCHK`, lines 533-551, reads the display byte to detect a
barrier, rather than consulting such a grid.

The archive directory calls this Public Domain; the examined source has no
attribution or explicit grant establishing who released it. Do not infer an
author or a code-reuse license from that directory label. No accompanying
magazine provenance or CoCo model/RAM compatibility result was established.

### Dunkey Munkey: repeated shapes, pixel by pixel

The archive title says Cercomp, while `KONG.TXT` lines 1-6 credit Harvey
Brofman and Intellectronics, dated June 24, 1982. Preserve both facts rather
than rewriting the source credit. `KONG.TXT` 446-447 includes `GRAPH2` and
`SOUNDS`; the additional `GRAPH3.TXT` is not the graphics module selected
there. Reading the wrong module would weaken the call-chain evidence.

The actual scene construction is compact and data-driven:

- `SCREN2.TXT` 674-735, `SETSC2`, reads position/count records from `ZIGURT`
  and repeats `GIRDER` through `BSHAPE`, advancing horizontal position by five.
  It then places rivets, ladders and other shapes before `COPYBF`.
- `SCREN3.TXT` 683-753, `SETSC3`, similarly consumes `ELRAMP` records,
  repeats girders, places ladders and scenery, and copies the background.
- `KONG.TXT` 450-480 contains those placement records. These are runs and
  coordinates, not a rectangular array of cell identifiers.
- `KONG.TXT` 484-491 defines the girder as width/height, four pointers and
  character-coded pixel values. `GRAPH2.TXT` 139-180 selects a pointer from
  horizontal alignment, maps each source value through `COLORS`, and calls
  `SETX` once per pixel. Its next source row moves the destination up by 32.
  `SETX`, 83-99, masks and replaces the selected pixel within a byte.

This supports repeating a reusable visual shape from compact placement data.
It does not support describing `BSHAPE` as a packed-byte tile blitter. The
source's background/display addresses are in `KONG.TXT` 98-99; the graphics
setup is in `GRAPH2.TXT` 5-30. These are legacy graphics paths, not CoCo 3
mapped-page rendering. Exact RAM, ROM and model compatibility remain untested.
The separate background-restoration study remains in
[rendering sources](rendering-sources.md).

A reading hazard matters even without porting: `GRAPH2.TXT` 34-59 uses `BLE`
after incrementing the pointer and comparing it with the buffer end in clear
and copy loops. Static tracing indicates one extra two-byte iteration at the
nominal end. This is a source-level bounds concern, not a reproduced crash or
published erratum. Use explicit exclusive bounds in an original implementation.

### Sea Quest: room composition and compressed bitmap rectangles

The downloaded `seasrch.zip` is under Sea Quest, but `ADVENT.ASM` 1-9 says
version 2.1 renamed the game Sea Search and records a version 2.2 gameplay fix.
Lines 360-379 credit Stephen and Kathy O'Dea, Bob and Dollie Withers, with a
1983 copyright notice for Bob Withers / Stephen O'Dea and reserved rights.
No redistribution license was found in the examined headers.

`ADVENT.ASM` 12-19 defines the graphics base and room constants; 215-247
contains the legacy display setup and 6,144-byte clear. This is relevant
legacy CoCo source evidence, not a measured CoCo 1/2 configuration claim.
No new register-setting recipe or minimum-RAM claim follows from this pass.

The complete examined rendering chain separates scene selection and drawing:

1. `ADVENT01.ASM` 380-405, `VEC20` (`DRAWSC`), indexes `SCRIND` by room,
   selects a background through `SCRTAB`, calls `SHOSC2`, then `SHOOBJ`.
   `ADVENT03.ASM` 538-554 shows the first room records; 853-856 gives the
   background pointer table. A room record is one background ID plus eight
   overlay slots, not a grid row.
2. `ADVENT.ASM` 409-431, `SHOSCR`/`SHOSC2`, expands a compressed stream into
   successive screen bytes. A nonzero control byte below `$FF` introduces
   literal bytes; zero introduces a repeat count and value; `$FF` ends the
   stream. `SCREENS1.ASM` 1-49 supplies concrete background records.
3. `ADVENT.ASM` 441-493, `SHOOBJ`, follows the fixed overlay slots, then
   checks room objects against `MOVOBJ` and selects additional overlays.
4. `ADVENT.ASM` 495-556, `SHOOVL`/`OBJBYT`, reads an overlay's row, column
   and byte width, decodes its bytes, and advances destination rows by 32.
   `ADVENT03.ASM` 862-866 documents that header and terminator;
   `OVERLAY1.ASM` 1-3 supplies an actual header and start of encoded data.

Our algebraic reading of `SHOOVL` gives the first destination as
`GSCRN + (row - 1) * 32 + floor((column - 1) / 4)` for valid positive input.
It writes full destination bytes with `STA`, without a read/modify/write mask.
Thus an overlay column does not imply arbitrary sub-byte positioning or
transparency. This is bitmap rectangle placement with decompression, not a
plain atlas-copy loop, scrolling map, or tile-based collision algorithm.

`OBJBYT` ends an overlay by removing its own return address and returning
through `SHOOVL`'s saved registers (554-556). Do not transplant that stack
convention into a general decoder. Source/destination bounds and malformed
stream rejection were not established. The archive also lists `patch.zip`;
it was not downloaded or examined, so this pass does not claim patch-complete
Sea Search behavior or an errata search.

### Practical adaptation: separate placement from byte production

For a fixed scene, Sea Search demonstrates a useful separation: room data
selects pictures, a decoder produces packed bytes, and placement determines
where each output row goes. Dunkey Munkey demonstrates a different compact
representation: runs of repeated shapes. Choose the scene representation
according to the world being built; neither becomes a collision grid merely
because it contains reusable graphics.

The following is **original, untested pseudocode**, distilled from Sea Search's
row placement. It deliberately assumes already-decoded, byte-aligned opaque
art and uses explicit dimensions. It is not a transcription, decoder, CoCo
initialization routine or evidence that a tile-map implementation was run.
`stride`, pixel packing and the available display interval must first be
verified for the chosen machine and mode.

```text
require width_bytes > 0 and height_rows > 0
require 0 <= left_byte and left_byte + width_bytes <= stride
require 0 <= top_row and top_row + height_rows <= screen_rows
require length(picture) == width_bytes * height_rows
for row in 0 .. height_rows - 1:
    source = row * width_bytes
    destination = (top_row + row) * stride + left_byte
    screen[destination : destination + width_bytes] =
        picture[source : source + width_bytes]
```

This can place a tile after some separate map lookup supplies its picture and
position. That map lookup is our proposed extension, not evidence from these
three candidates. Keeping art uncompressed makes byte addressing direct;
compression trades stored bytes for decoding work. Neither space savings nor
speed was measured. Opaque byte writes replace everything in their rectangle;
use another method when the artwork needs transparency or partial-byte edges.

Before claiming an implementation, test an asymmetric picture at every edge,
multiple rows, zero/oversized dimensions, and guards around the display.
Compare bytes outside the rectangle as well as inside it. For a future map,
add separate tests for tile selection and changed map state after redraw.
These are proposed checks only. The legacy tile-ID map source gap remains open;
this bounded pass does not establish that no such source exists in the archive.

### Game-source provenance

All three ZIPs, member files, normalized text and directory HTML are retained
under ignored `local/research/legacy-tiles-game-sources/`. `sources.json`
records URLs, retrieval date, sizes and SHA-256 hashes for ZIPs and members;
`reading.json` records citation ranges and normalized-text hashes. Downloads
were treated as data. No archive build script or game binary was executed.
No shared manifest, index, build output or conversion state was changed.

- DroidWar.zip: 6,253 bytes; SHA-256
  `2ffe587ea286622612f75ce520a0be63aa18e156b7c584a7b8a0da88bb661557`.
- Dunkey Munkey source: 72,655 bytes; SHA-256
  `f2dd97ac73813e9191e5f396eb24474fa95ec1c3d5cfd6230b77002aea2f06ac`.
- seasrch.zip: 49,602 bytes; SHA-256
  `1e16c925a231e51fbdc686b5f6a8172a9c0b964da3ae32a8b115d9e179e7b80f`.

[droid-src]: https://colorcomputerarchive.com/repo/Programming/Source/Droid%20War%20(Public%20Domain)/DroidWar.zip
[dunkey-src]: https://colorcomputerarchive.com/repo/Programming/Source/Dunkey%20Monkey/Dunkey%20Munkey%20Source%20(Harvey%20Brofman)%20(Cercomp).zip
[sea-src]: https://colorcomputerarchive.com/repo/Programming/Source/Sea%20Quest/seasrch.zip
