# Follow-up search for a legacy bitmap tile renderer

Read this when deciding whether another archive source closes the historical
CoCo 1/2 tile-rendering gap. This bounded pass does not close it. Three new
packages were inspected on 2026-11-14; none establishes the complete chain
`grid cell -> tile ID -> packed image -> bitmap destination` on CoCo 1/2.
This is a negative finding about these packages, not about the whole archive.
The subsequent Rat Maze reading below establishes a passage grid and procedural
wall drawing, but does not close the packed-bitmap tile-rendering gap.

The prior [tile research](tile-map-research.md),
[legacy research](legacy-tile-research.md) and
[tile guide](../guides/tile-maps.md) were read first. Droid War, Dunkey Munkey,
Sea Search, Barden, PacDude and Ice Hockey were not investigated again.
The existing original tile-room example remains separate implementation
evidence; it cannot establish a historical source's design or compatibility.

## Selection and stopping rule

The [source directory][directory] supplied three discovery leads. Their names
were not evidence of their implementation. The three-package budget includes
selection failures; rejected candidates were not replaced to extend the hunt.

| Package | Examined representation | Disposition |
| --- | --- | --- |
| Cubix | 6809 operating system | Discovery miss |
| Space Raiders | CoCo III object list | Wrong target and map format |
| Calixto Island | Background IDs and overlays | No tile-ID grid |

Only Calixto remained a plausible legacy graphics source after inspection.
Do not describe this as three verified CoCo 1/2 games. The general archive
index request timed out in the web tool. Direct HTTPS directory and ZIP
requests succeeded; there was no retry loop or archive-wide crawl.

## Citation convention

All source citations below count physical lines, including blank lines, after
CRLF and lone CR become LF. Paths are ZIP member names, except Space Raiders,
whose `.TXT` files are inside `SR3.DSK`. These are plain-text source readings,
not OCR or PDF citations. Named ranges were read directly. No complete-game
audit, build, execution, timing, framebuffer, visual or hardware test occurred.

## Cubix: reject the discovery assumption

Dave Dunfield's [Cubix package][cubix], `DOCS/READ.ME` lines 1-24, identifies
version 1.3 as a ROM-based disk operating system for the 6809, with a porting
workflow. `SRC/CUBIX_OS/CUBIX.ASM` lines 1-24 independently identifies the OS,
credits Dunfield, gives a 1983-1994 copyright range, and separates distribution
and demonstration memory configurations. The archive includes editors,
assemblers and language tools. It supplies no basis for the initial game
association. No tile technique is attributed to it and no OS call chain was
traced as if it were a game renderer.

`DOCS/READ.ME` also contains freeware/commercial-redistribution restrictions.
That is not an unrestricted code license. Nothing from the package is copied
into tracked source.

## Space Raiders: a formation is not a tile map

John Crawford's [Space Raiders package][raiders] contains `SR3.DSK`.
`SR3.TXT` lines 1-8 explicitly says CoCo III and records June 21, 1987 as
its last modification. Lines 57-89 set palette registers and a legacy-style
display path. A familiar bitmap stride cannot override that declared target
or prove that the whole program runs on CoCo 1/2.

The examined call chain and data explain why a rectangular formation is
insufficient evidence for a tile grid:

1. `SR3.TXT` lines 122-132 calls `INMAN`. Lines 657-736 initialize five groups
   of eight objects in `SMLOC`. Each eight-byte record has current coordinates,
   saved coordinates, a shape pointer and two state bytes. Positions advance
   by 12 horizontally; each group starts at a different vertical position.
2. `MAIN` and `PUTSHP`, lines 134-208, reach `PMAN`. `PMAN`, 738-759, walks
   records, skips an inactive object, selects its shape pointer or the frame
   18 bytes later, and passes that object's coordinates to `MASK`.
3. `SRFILES.TXT` lines 309-352, `MASK`, reads width and height, consumes packed
   shape bytes, combines shifted data with destination bytes through masks,
   and advances the destination by 32 down each column. After a column it
   restores the starting position and moves right by one byte. The source
   data is therefore column-major, not consecutive horizontal image rows.
4. `SR3.TXT` lines 1002-1011 contains the paired shape records. A width of two
   and height of eight gives 16 payload bytes plus the two-byte header,
   explaining the 18-byte alternate-frame offset. This is source arithmetic,
   not a measured rendering result.

`MVSM`, `SR3.TXT` 460-497, mutates object coordinates and animation state.
This is an object list arranged initially in rows, not cell IDs selecting
terrain from an atlas. `SR3.TXT` 1150-1152 includes `SRFILES`, `FIRESR3` and
`SRC3`; the separately present `SRF1.TXT` is not the included firing module.
Do not use that older-looking companion as evidence of the assembled path.
No reuse license or older CoCo 1/2 revision was established.

## Calixto Island: scene records and packed-byte production

The [Calixto Island package][calixto], `ADVENT.ASM` 358-379, credits Bob
Withers and Stephen O'Dea, with a 1981 Mark Data Products copyright notice.
`ADVENT.ASM` 1-9 defines `GSCRN` at `$0400`, eight overlay slots and 26 rooms.
Its initialization at 216-253 configures the legacy display path and clears
6,144 bytes. These are source facts, not a tested RAM minimum, ROM contract,
PAL/NTSC claim or model-by-model compatibility result.

The scene path was followed through its actual data and byte writer:

- `ADVENT01.ASM` 446-477, `VEC20`/`DRAWSC`, computes the room record offset
  as `(ROOM - 1) * (NOVLY + 1)`, reads its background ID, uses `SCRTAB` to
  select a stream, calls `SHOSC2`, then calls `SHOOBJ` on the remaining slots.
- `ADVENT03.ASM` 513-545 shows concrete room records. With `NOVLY = 8`, each
  contains one background ID and eight overlay slots, padded where needed.
  `SCRTAB`, 737-739, contains six background pointers. This is a room-to-scene
  lookup, not a two-dimensional terrain grid.
- `ADVENT.ASM` 408-452, `SHOSCR`/`SHOSC2`, produces consecutive bitmap bytes
  from literal runs, repeated-byte runs and a special alternating-row form.
  `SCREENS1.ASM` 1-12 provides all six short background streams.
- `ADVENT.ASM` 462-514, `SHOOBJ`, resolves overlay IDs through `SCROBJ` and
  also checks movable room objects. `SHOOVL`, 516-543, reads row, column and
  byte width, then places decoded bytes with a 32-byte destination stride.
- `ADVENT03.ASM` 743-753 documents that overlay header. `OVERLAY1.ASM` 4-6
  supplies a real record beginning at row 65, column 1, width seven bytes.
  `OBJBYT`, `ADVENT.ASM` 545-611, supplies the packed bytes, including the
  special descriptor. Neither the overlay header nor the byte writer reads
  a tile ID from a grid.

This independently examined package resembles the room/overlay architecture
already recorded for Sea Search. It does not become new tile-map evidence
merely because scenery repeats. No Calixto patch was examined, and no
patch-complete behavior or errata search is claimed.

### Useful narrow technique: compress alternating solid rows

Calixto's `SHOSC2` special descriptor starts with two zero bytes, followed by
run width, row count and two packed byte values. Lines 436-451 repeat the first
value across one run, exchange the values, and repeat until the count expires.
`SCREENS1.ASM` 11-12 uses width 32, count 90 and values `$66`/`$99`.
Our arithmetic gives 2,880 expanded bytes from a six-byte descriptor plus the
terminator. That calculation is not a compression benchmark or display test.
The bytes alternate between runs, not between adjacent bytes within a run.

For a builder, this can compact a repetitive rectangular background. It does
not encode arbitrary tile arrangements or collision properties. Separate the
decoded byte stream from placement: `SHOSC2` writes consecutively, whereas
`SHOOVL` imposes its own row stride. A decoder run length need not equal an
overlay's destination width.

The following is **original, untested pseudocode**, adapted from that narrow
operation. It is not a historical transcription or a CoCo initialization recipe.
Explicit bounds and rejection of zero dimensions are our additions.

```text
expand_alternating_runs(width, count, first, second, output_capacity):
    require 1 <= width <= 255 and 1 <= count <= 255
    require first and second are bytes
    require width * count <= output_capacity
    output = empty byte sequence
    for run in 0 .. count - 1:
        value = first if run is even else second
        append width copies of value to output
    return output
```

Proposed independent checks use width three, count three and values `$12` and
`$A7`: expect three `$12`, three `$A7`, then three `$12`, with no fourth run.
Reject zero width, zero count and capacity eight for that nine-byte result.
At placement, test a rectangle narrower than the framebuffer stride and guard
the untouched bytes on both sides. These checks were not run. Historical
zero-count wrap behavior is not adopted as a format feature.

The legacy routine has self-modifying fields and `OBJBYT` terminates by
discarding a return address (`ADVENT.ASM` 577-580). Its output bounds and
malformed-input handling were not established. A reusable decoder should
return explicit completion/error state rather than inherit that stack contract.

## Rat Maze: a passage grid with procedural drawing

Benjamin W. Brunotte's *Rat Maze*, [The Rainbow, May 1985][rat-may],
Vol. 4 No. 10, is now examined, including both complete listings and Figures
1-10. The [index][index], PDF 19 (reprinted July 1985 page 231), correctly
points to printed 105. In this issue PDF pages are two greater than printed
pages. The reading covered:

| Material | Printed pages | PDF pages |
| --- | --- | --- |
| Complete prose and Figures 1-10 | 105-109 | 107-111 |
| Listing 1, RAT MAZE, lines 10-1530 | 108-110, 112, 116 | 110-112, 114, 118 |
| Listing 2, MAZEBLDR, lines 10-1440 | 116, 118 | 118, 120 |

Full-page images were read in column order, including statements split across
pages. The opening illustration is artwork, not runtime evidence. The printed
check-value boxes were inspected but their checksums were not reproduced.
The companion disk was unnecessary to establish the representation and drawing
chain; none was downloaded or executed.

### Machine and representation

The article's badge specifies **16K ECB** (Extended Color BASIC), and the prose
identifies the Color Computer. This is legacy CoCo BASIC material, not a
CoCo 3-specific renderer. It does not name separate CoCo 1/2 models, ROM
revisions, or PAL/NTSC requirements. Those configurations were not tested.
The warning on printed 109/PDF 111 says large MAZEBLDR dimensions can take a
long time and can exhaust 16K memory; the badge is not a promise that every
accepted maze size fits.

RAT MAZE line 10 reserves graphics pages with `PCLEAR4`. Line 240 selects
`PMODE0,1` for the generation/title display; line 420 selects `PMODE4,1`
for play, followed by `SCREEN1,1` and colour selection. MAZEBLDR line 420
also selects `PMODE4,1`. These are BASIC graphics paths, not text or
semigraphics character placement. No assembly driver or packed-image atlas
appears in either listing. This reading establishes the commands, not a
hardware register recipe or measured display output.

The 12-by-9 playable maze occupies the interior of `MZ(13,10)`, a 14-by-11
BASIC numeric array including its border. These are numeric elements, not
proven one-byte storage. Printed 105-107/PDF 107-109 and RAT MAZE lines
70-96, 200, 300-330 establish the cell meanings:

- Open passages have weights west=1, north=2, east=4, south=8. A finished
  cell's value is their sum. For example, 9 opens west and south.
- Border cells contain 100. During generation, 0 means unassigned and -1
  marks a frontier. The first cell temporarily receives 16, removed after
  its first connection. Those states must not be decoded as passage masks.
- Opening an edge updates both cells with opposite passage weights.
  Generation grows through frontier cells; when locally blocked, it scans
  the array for unfinished cells and an assigned neighbor. The published
  routine uses arithmetic and branches, not bit-test instructions.

MAZEBLDR accepts widths 5-50 and heights 5-36. Its array includes the same
border, and its drawing scale is the smaller of `250 / width` and
`190 / height` (line 30, printed 116/PDF 118). Do not silently round that
expression or claim all maximum dimensions are usable on 16K.

### Complete drawing chain

For the first-person view, RAT MAZE line 500 clears the graphics screen,
sets `SQ=1`, and reads `MZ(RH,RV)` into `Z`. Lines 510-650 combine that
passage value with facing `DR` (west, north, east, south) to select one of
eight relative left/front/right wall-or-opening combinations at 700-770.
Those combinations call dispatchers 100-108; `SQ` selects geometry routines
20-58, which issue `LINE` segments or outlined rectangles. A front wall
sets `FL=1`. Lines 800-860 stop at that wall or at `SQ=4`, otherwise read
the next cell straight ahead and increase depth. This is
`cell passage mask + facing + depth -> line geometry -> BASIC graphics`.
It never selects packed tile artwork.

The prose at printed 108/PDF 110 describes the cutoff as three squares,
but the listing starts at `SQ=1`, draws before testing line 800, and supplies
four geometry groups. Our control-flow reading therefore gives the current
cell plus up to three ahead. This is a source discrepancy, not a runtime
measurement. Cheese uses filled rectangles selected by depth (60-66);
the distance display uses `DRAW` commands (900-921). Movement validation
reads the same cell value and direction (1020-1180), independently of the
picture. Turns and accepted moves return to the full-screen drawing path.

The overhead reveal at 1200-1250 draws the top and left outer boundaries
once, then reads every cell and draws its closed bottom and right edges.
Cell spacing is 20 coordinate units. Printed 108's description of line 1230
says right side only; the actual line 1230 on printed 112/PDF 114 draws the
bottom edge. Line 1240 draws the right edge. Reciprocal passages make this
single-owner treatment of shared edges sufficient, as the prose on printed
109/PDF 111 explains. MAZEBLDR uses this same overhead method with variable
spacing, and erases/redraws its player rectangle inside the cell
(lines 940-945, 1170-1290, printed 118/PDF 120).

### Useful technique: draw each shared wall once

For an overhead maze, store connectivity separately from geometry. Render
the north and west exterior edges once, then let each cell own its south
and east edges. This avoids duplicate shared-wall work and allows movement
and two different views to use the same topology. It requires reciprocal
passages; an inconsistent map could show a wall that movement treats as open.
It supplies walls and corridors, not textured terrain or arbitrary tile art.
No speed or memory saving was measured.

The following is **original, untested pseudocode**, not a transcription.
Separate generation states, explicit validation and bit tests are our design
choices. Coordinates increase east and south; drawing uses a caller-selected
origin and positive cell size. Support for a zero mask is an adaptation for
an isolated cell, not a claim about the generator's finished output.

```text
render_overhead(openings, columns, rows, origin, size):
    require positive columns, rows, size
    require exactly rows * columns integer masks in 0..15
    require no passage crosses the outer boundary
    require each east opening matches its neighbor's west opening
    require each south opening matches its neighbor's north opening
    draw north boundary and west boundary
    for each cell (column, row):
        mask = openings[row, column]
        rectangle = cell_rectangle(origin, column, row, size)
        if (mask AND 8) == 0:
            draw rectangle.south_edge
        if (mask AND 4) == 0:
            draw rectangle.east_edge
```

Proposed checks are independent edge expectations: a one-cell closed maze
has four edges; a two-cell horizontal corridor with masks `[4, 1]` has no
shared vertical wall and has a closed outer perimeter. Reject `[4, 0]` for
nonreciprocal connectivity, a west opening on the left boundary, and -1,
16 or 100 as generation states. Translate the same corridor to a nonzero
origin to check placement separately from topology. These checks have not
been executed; no historical code, emulator or hardware was run.

### Corrections boundary and disposition

The bounded check searched the existing index for the author, title and
MAZEBLDR, then visually checked its relevant entries on PDF 19, 22, 28 and
109. None attaches a correction to Rat Maze. The actual Corrections columns
in [June 1985][rat-june], printed 226/PDF 228, and [July 1985][rat-july],
printed 225/PDF 231, contain no Rat Maze correction. July does correct
Brunotte's separate Script printer program from May page 68; that is not a
maze patch. Exact-title/author archive web searches supplied no further
correction lead. This is a bounded negative finding, not a claim that no
later correction exists. No further issues were searched or downloaded.

**Disposition:** useful historical evidence for passage-mask topology,
procedural first-person walls, and overhead shared-edge rendering. It does
not qualify as the missing `grid cell -> tile ID -> packed image -> bitmap
destination` source. Calling its masks tile IDs would hide the useful part.

The concrete next decision is whether the intended game needs an untextured
maze. If yes, an original connectivity-and-edge prototype is justified by
this source. If it needs bitmap scenery, retain the existing original
[tile-room example](../examples/tile-room/README.md) as implementation evidence
and leave historical provenance unresolved. My recommendation is to stop this
source hunt here. No further candidate search or implementation is queued.

### Rat Maze reproduction record

All new downloads, text and page images are confined to ignored
`local/research/tile-source-followup/rat-maze/`. The May PDF has 278 pages,
26,331,460 bytes and SHA-256
`dc36fcbfbb3e651f4a4cea9ebd51da0e10b03a67e5ed252ecd5de812a05e4f36`.
Correction-check PDFs are identified below so a fresh checkout does not need
the ignored metadata file:

| Issue | PDF pages | Bytes | SHA-256 |
| --- | ---: | ---: | --- |
| [June 1985][rat-june] | 278 | 26972200 | `95b1d6e65a0e9938c31db9bd6e7ff497473bde66503e70e3f3550c3fdfabe978` |
| [July 1985][rat-july] | 282 | 27631178 | `dd665288d73b3bd595b33c057d2c3142298e56ee370e5ba3bff7c44eccd68854` |

The local `sources.json` repeats the three download identities.

Download the linked issue into that directory and verify its hash. For each
PDF page in the table above, use `pdftotext -f N -l N -layout` to locate text
and `pdftoppm -f N -l N -scale-to 2400 -png` to render that page, with all
outputs in the same ignored directory. This pass used Poppler text extraction
and `pypdfium2.PdfDocument(...)[N-1].render(scale=2).to_pil()` for images.
Read the image when OCR disagrees: the scan's zeros, variable names and
wrapped BASIC statements are often damaged in extracted text. Do not execute
the historical listings. No shared conversion checkpoints or manifests changed.

## Provenance and reproduction

Downloads, directory HTML, original members and normalized text remain under
ignored `local/research/tile-source-followup/`. No downloaded code or art is
tracked. `sources.json` records exact URLs, sizes and hashes. Retrieved ZIPs:

| Archive | Bytes | SHA-256 |
| --- | ---: | --- |
| [cubix.zip][cubix] | 363837 | `a1c39f4e3562797e53f8282db562b8de54a5946e57c6f7eca60543ea8b6c839a` |
| [SR3.zip][raiders] | 45426 | `0dcc49a4c659d5fd61739115c110b132b2c53a89bee66199a1d1c5ce939826be` |
| [calixto.zip][calixto] | 67402 | `ffe26efd81ebb87ff501032292d18b8f6c19d7513d740ca5220960bc83872971` |

For a fresh clone, download the linked ZIPs into that ignored directory, check
their hashes, and extract Cubix and Calixto as plain data. Decode text as
Latin-1, replace CRLF with LF, then replace lone CR with LF. Do not strip
blank lines or interpret embedded assembler directives. No archive program
needs to execute. No PDF conversion is needed for these sources.

Space Raiders needs disk-contained text extraction. The following original
reading utility preserves the extraction logic in Git. After placing `SR3.zip`
in the directory above, run it from the repository root. It handles this
specific flat 35-track image, not arbitrary disk formats. Its assertions check
image size, chain bounds, cycles and terminal lengths; they are extraction
sanity checks, not independent validation of the game or all disk formats.

```python
from pathlib import Path
from zipfile import ZipFile

root = Path("local/research/tile-source-followup")
with ZipFile(root / "SR3.zip") as archive:
    disk = archive.read("SR3.DSK")
assert len(disk) == 35 * 18 * 256
fat = disk[17 * 4608 + 256:17 * 4608 + 512]
directory = disk[17 * 4608 + 512:18 * 4608]
output = root / "text/SR3"
output.mkdir(parents=True, exist_ok=True)
for offset in range(0, len(directory), 32):
    entry = directory[offset:offset + 32]
    if entry[0] == 255:
        break
    if entry[0] == 0 or entry[8:11] != b"TXT":
        continue
    name = entry[:8].decode("ascii").rstrip() + ".TXT"
    granule = entry[13]
    parts, seen = [], set()
    while True:
        assert granule < 68 and granule not in seen
        seen.add(granule)
        track = granule // 2 + (granule // 2 >= 17)
        start = track * 4608 + (granule % 2) * 2304
        following = fat[granule]
        if following < 68:
            parts.append(disk[start:start + 2304])
            granule = following
            continue
        assert 0xC1 <= following <= 0xC9
        final_bytes = int.from_bytes(entry[14:16], "big")
        assert 0 < final_bytes <= 256
        length = (following - 0xC1) * 256 + final_bytes
        parts.append(disk[start:start + length])
        break
    raw = b"".join(parts)
    text = raw.decode("latin1").replace("\r\n", "\n").replace("\r", "\n")
    (output / name).write_text(text, encoding="utf-8")
```

The extraction produced five text files. Raw lengths were `SR3.TXT` 19,538,
`SRF1.TXT` 4,719, `SRC3.TXT` 4,296, `FIRESR3.TXT` 6,346 and `SRFILES.TXT`
8,786 bytes. The reading was selective as cited above. No runtime experiment
or test controls were removed or replaced by this documentation pass.

Validation: Markdown lint passes, and Ruff passes on the extracted Python
block. Running that tracked block reproduced all five normalized text files
byte-for-byte. The first comparison harness failed because executing the block
in its own namespace overwrote the harness's path variable; rerunning with an
isolated namespace fixed that harness error. It was not a disk extraction or
game failure. The alternating-run pseudocode remains unexecuted.

[directory]: https://colorcomputerarchive.com/repo/Programming/Source/
[cubix]: https://colorcomputerarchive.com/repo/Programming/Source/Cubix/cubix.zip
[raiders]: https://colorcomputerarchive.com/repo/Programming/Source/Space%20Raiders%20%28John%20Crawford%29/SR3.zip
[calixto]: https://colorcomputerarchive.com/repo/Programming/Source/Calixto%20Island/calixto.zip
[index]: https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow,%20The%20-%20Text%20Searchable%20Index/The%20Rainbow%20-%20Text%20Searchable%20Index.pdf

[rat-may]: https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow%2C%20The%20%28OCR%29/The%20Rainbow%20Vol.%2004%20No.%2010%20-%20May%201985.pdf
[rat-june]: https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow%2C%20The%20%28OCR%29/The%20Rainbow%20Vol.%2004%20No.%2011%20-%20June%201985.pdf
[rat-july]: https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow%2C%20The%20%28OCR%29/The%20Rainbow%20Vol.%2004%20No.%2012%20-%20July%201985.pdf
