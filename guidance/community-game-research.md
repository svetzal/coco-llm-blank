# Later community sources for asset preparation

Read this when tracing the evidence behind [asset preparation](../guides/assets.md).
This bounded pass examines two articles in the July and October 2006 issues
of *CoCoNutz! E-Zine*. Both are CoCo 3 sources. They do not close the CoCo 1/2
historical tile-renderer gap or establish a compressed asset format.

## Provenance and reading scope

These are direct archive citations, with no manifest resource IDs. PDF pages
are one-based. The examined article pages have no separate printed page labels.
Files and page images are under ignored `local/research/community-game/`.
No historical program was assembled, executed or redistributed.

| Local source | Edition and exact archive URL | PDF pages | SHA-256 |
| --- | --- | --- | --- |
| `july-2006.pdf` | [CoCoNutz! volume 2, issue 2, July 2006][july] | 39 total | `fbacbeee8205063bf49dc52f4468c4e808c124b0ba4d2f9caa498485b25a7a7d` |
| `october-2006.pdf` | [CoCoNutz! volume 2, issue 3, October 2006][october] | 48 total | `6027e4d0708d62442c2e9e83e9f49ec66f6dba6fe53a90142586f181e3cf0c0c` |
| `march-2006.pdf` | [CoCoNutz! volume 2, issue 1, March 2006][march] | 36 total | `d69a8b7d65ebfd38b072436d3431decb7327f035bf11dd64c6c82505c1b98bc7` |

Read the complete Barizo article and listing on July PDF 12–19, ending at BASIC
line 10000. Read the complete Gault article and listing on October PDF 38–46,
ending at `END EXEC`, before the unrelated Graph article. This is source
reading, not a complete correctness review. Text came from `pdftotext -layout`.
July PDF 12, 13, 16–18 and October PDF 38–42, 45, 46 were also inspected as
rendered images. No Docling conversion coverage is claimed.

## Generate and capture a reusable picture set

Diego Barizo's "Mine Sweeper! The Mission" identifies CoCo 3 and an RGB palette
(July PDF 12). The asset path is BASIC, not an assembly format. Minimum RAM,
ROM revision, video standard and physical display results are unspecified.

The relevant complete routines are:

- Initialization, lines 4000–4240 (PDF 16–17), creates map and flag arrays.
- Graphics setup, 4500–4960 (PDF 17–18), draws pictures, allocates buffers,
  captures them with HGET, creates digit drawing strings and clears the canvas.
- Map presentation, 5000–5070 (PDF 18), selects buffers from map values.
- Main loop, 200–360 (PDF 13–14), saves a cursor-sized background in buffer 7,
  draws buffer 6 and restores buffer 7 before moving again.
- Introduction, 7000–7260 (PDF 18–19), consumes text DATA before palette DATA.

This separates preparation from repeated drawing. The source does not define
the bytes inside HGET buffers. Its buffer allocations are not a packed-assembly
size formula. Digit drawing strings are geometry descriptions, not animation
frames or evidence of compression performance.

### Corrections and limits that affect adaptation

The PDF images confirm these differences; they are not extraction guesses:

1. PDF 12 says map numbers match buffer numbers. Line 5050 (PDF 18) actually
   uses `M(X,Y)+1`. An assembly port needs an explicit ID mapping.
2. PDF 13 describes the padded matrix as 24×14; the declaration at line 4070
   (PDF 16) is `DIM M(25,14),F(25,14)`. These are BASIC bounds, not a proposed
   assembly allocation. Visible cells are selected by loops 2–24 and 2–13.
3. The prose's coordinate adjustment describes the cursor anchor. Line 5050
   uses different offsets for terrain rectangles. Do not reuse one transform
   for every asset just because the grid is shared.
4. PDF 12 describes hiding preparation with a single-colour palette. The
   listing sets entries 1–15 at line 4010, then loads only entries 1–10 at
   line 65. This is not evidence that every palette entry is restored.
5. Skipping the introduction still consumes DATA to its sentinel at line 7160.
   A naive early exit changes where palette loading begins. The guide proposes
   independent sections instead of preserving that coupling.

PDF 13 acknowledges revisions made during the author's review but supplies no
separate patch list. The next issue's extracted text was searched for
`mine`, `HGET`, `HBUFF`, `sprite` and `correc`; no follow-up correction to this
article was identified. This is a bounded search, not an errata clearance.

## Keep bulk storage separate from the access window

Robert Gault's "Special Backup Utility for a Coco3 Using Full 512K RAM"
(October PDF 38–46) requires a 512K CoCo 3 and Disk BASIC facilities. It is a
disk copier, selected for its explained MMU use, not a game asset loader.
The author distinguishes physical-drive and emulator disk-command choices on
PDF 38 and 45. Neither choice was run here.

`MMU` (PDF 41) writes the selected block to `$FFA2` and establishes a pointer
at `$4000`; its comment names the `$4000–$5FFF` window. `RDWRDK` (PDF 44–46)
uses the window for sector transfers and changes the block between tracks.
`COLD` (PDF 40–41) restores a particular BASIC mapping, not an arbitrary
caller's prior mapping. `EXEC` (PDF 42–43) includes a memory-alias probe.

The deduction is narrow: a CPU pointer into such a window is meaningful only
with its mapping. A game's asset descriptor therefore needs storage identity
as well as an offset. This is our adaptation; the source supplies no frame
scheduler, interrupt-safe game cache or measured asset-loading latency.

The author's source uses local labels that he says need adjustment for Disk
EDTASM (PDF 39). The rendered PDF itself wraps some `FCC` comment text and
`TRACK`'s comment onto new lines (PDF 42, 45). Extracted text is not an
assembly-ready file. No separate erratum was found within the examined article;
later issues and the author's other releases were not searched for its errata.

## Bounded search and rejected leads

The pass stopped after three issue downloads and the two complete readings.

- [CoCoNutz directory][directory]. Inspected issue inventory; selected July for
  the game and October for continuation/correction search.

- March 2006 issue. Searched extracted text for graphics, sprites, compression,
  mines and corrections. Matches mostly reviews and other utilities; not
  selected for a complete asset passage.

- July software lists. NIB Compressor and graphics tools are names, not format
  descriptions. Rejected as implementation evidence. No tool packages
  downloaded.

- October Mandelbrot article. A graphics-generation lead, not selected for
  complete reading; no claims drawn from it.

- [Programming/Source directory][source-directory]. Web fetch timed out; a
  bounded curl retry retrieved the directory only. No source tree downloaded.
  Existing Gloom/Symmetry research made another broad source pass unnecessary.

- Search result for Tim Kientzle's November 1990 Rainbow RLE article. Promising
  compression follow-up, outside this later-community selection. Not downloaded
  or examined; no codec rules taken from the search excerpt.

- Search result for Summer 2021 CoCo~123 80-column starter. A video
  announcement rather than the tutorial itself. Rejected as hardware evidence;
  video not examined.

## Rights and verification boundary

Gault's listing displays copyright 1990, 2006 (PDF 40). No explicit code or
art redistribution license was identified in either selected article. The
archive's availability and newsletter publication do not grant one. Retain
PDFs, extracted listings, screenshots and any future companion downloads only
in ignored local storage; use original art and code for experiments.

There are no measured runtime results or failed runtime controls in this pass.
The failed fetch and source discrepancies above remain recorded. The guide's
negative cases are proposed checks, not passing tests. No compressed format,
frame-table timing, firmware compatibility or physical-machine result follows
from these readings.

To repeat the reading, download the exact URLs above to the local filenames,
check SHA-256 and page count, then use these commands from the repository root:

```sh
shasum -a 256 local/research/community-game/*.pdf
pdfinfo local/research/community-game/july-2006.pdf
pdftotext -layout local/research/community-game/july-2006.pdf \
  local/research/community-game/july-2006.txt
pdftoppm -f 17 -l 18 -scale-to 1400 -png \
  local/research/community-game/july-2006.pdf \
  local/research/community-game/july
```

Repeat for October, inspecting the cited pages. These are source-inspection
commands, not experiment logic. No untracked executable experiment was created.

[july]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Coco%20Nutz%21%20Newsletter/Coco%20Nutz%21%20Vol%202%20Issue%202%2C%20July%202006.pdf>
[october]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Coco%20Nutz%21%20Newsletter/Coco%20Nutz%21%20Vol%202%20Issue%203%2C%20October%202006.pdf>
[march]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Coco%20Nutz%21%20Newsletter/Coco%20Nutz%21%20Vol%202%20Issue%201%2C%20March%202006.pdf>
[directory]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Coco%20Nutz%21%20Newsletter/>
[source-directory]: <https://colorcomputerarchive.com/repo/Programming/Source/>
