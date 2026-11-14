# Legacy CoCo maze and tile research

Read this note when considering Barden's February 1988 maze as a source for
CoCo 1/2 map rendering. It closes the unexamined magazine lead in
[tile-map research](tile-map-research.md). It does not repeat the PacDude or
Ice Hockey investigations.

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

The conditional fallback to another CoCo 1/2 lead was unnecessary because
this source is not CoCo 3-only. No additional game archive was downloaded.

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
