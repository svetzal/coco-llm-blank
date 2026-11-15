# Research for games and demos

Start with the [technique guides](../README.md) when building a game or demo.
Read these research notes for source selection, exclusions, and open questions.
Use [reference lookup](../../starter/references.md) to obtain and inspect the selected pages.
This guide records selected research batches, not a complete survey or tested engine.

Stacey requested equal attention to CoCo 1, CoCo 2, and CoCo 3. Select by
reusable techniques rather than a preferred game genre. Assembly remains the
starter's implementation baseline. BASIC articles can explain useful ideas.
Their ROM calls, storage formats, and performance do not transfer automatically.

## Choose by the effect you want

| Need | Start with | Evidence and limits |
| --- | --- | --- |
| Animate objects or alternate prepared frames | [Animation guide](../animation.md) | Polsz and Matthews examined; original page-flip examples checked on CoCo 1/2 and CoCo 3. |
| Smooth horizontal scrolling on CoCo 3 | Tepolt, `tepolt-coco3`, PDF 59 | Examined page image. Pre-shifted buffers trade memory for motion granularity. |
| Banked assets with interrupts on CoCo 3 | Tepolt, `tepolt-coco3`, PDF 59–60 | Examined page images. Keep interrupt tables and handlers accessible. |
| Match CoCo 2 artifact colours | [Colour guide](../colour.md#coco-2-artifact-colours); Tandy, `coco2-service`, PDF 31–33 | Examined hardware discussion. Specific NTSC models, not all CoCo 2 variants. |
| Choose CoCo 3 colours for a display | Tandy, `coco3-service`, PDF 17 | Examined palette tables. RGB and composite encodings differ; PAL caveat applies. |
| Sound alongside animation and controls | [Sound guide](../sound.md) | Examined hardware for all three models; sound-slots on CoCo 1/2 and timer-sound on CoCo 3 checked with mixer output. |
| Keep map state separate from actors | [Tile-map guide](../tile-maps.md) and [tile-room result](../../../examples/tile-room/README.md#evidence-and-limits) | Original CoCo 1/2 implementation, 42 checkpoints per defined target; historical tile-ID source gap remains. |
| Redraw only changed regions | [Animation guide](../animation.md#decide-what-to-redraw), [CoCo 3 source reading](coco3-game-source.md) | Gloom and Symmetry examined; one RAM-only lab result. |
| Combine held controls and collision rules | [Controls and collision](../controls-and-collision.md), [Hot CoCo reading](hot-coco-game.md) | Examined articles and manuals; keyboard-controls example checked on CoCo 1/2. No general collision engine. |
| Schedule turns and menu transitions | [Game state](../game-state.md), [Undercolor reading](undercolor-game.md) | Source-backed proposals; target adapters and runtime checks remain open. |
| Accumulate a picture without storing every shape | [Animation guide](../animation.md#budget-the-storage-for-animation) | Undercolor source examined; adaptation untested. |
| Find legacy bitmap composition sources | [Expanded legacy reading](legacy-tile.md#three-game-source-candidates) | Selected Droid War, Dunkey Munkey and Sea Quest paths examined; no historical program run or tile-ID map established. |
| Decide whether OCR is usable | [Conversion-quality inspection](../../starter/conversion-quality.md) | Six selected pages and eleven exported images checked; no book-wide accuracy claim. |
| Find more magazine techniques | `rainbow-index` | Discovery only. Find the issue, then inspect the actual article and corrections. |

These are source-backed reading recommendations. Historical programs remain
examined, not reproduced. Original rendering and sound examples now provide
bounded evidence. The technique guides and the
[validation follow-up](#implementation-and-validation-follow-up) summarize it.

## CoCo 3 graphics and memory

### Scrolling and memory tradeoffs

Laurence A. Tepolt's **Assembly Language Programming for the CoCo3** is an
addendum to his earlier assembly book. Its introduction and contents were
inspected on PDF pages 5 and 7. Its advanced graphics discussion on PDF 59
explains pre-shifted buffers combined with horizontal and vertical display
offsets. [Archive book][tepolt-coco3].

Use it for scrolling playfields and smooth movement across a larger image.
Budget the buffers before promising resolution, colour count, and speed.
The same page discusses colour blending; treat that appearance as dependent
on the display, not as extra independent palette entries.

PDF 60 explains why interrupt tables and handlers must remain accessible when
memory mappings change. Consult it before combining banked assets, screen
buffers, and interrupt-driven audio. This is guidance to investigate, not a
verified interrupt implementation.

### Palette and display path

Tandy's **Color Computer 3 Service Manual**, PDF/printed page 17, separates
RGB palette bit meanings from composite meanings. It also gives a PAL caveat.
The neighbouring control-register pages 16 and 18 were converted for context;
conversion alone does not mean their tables have been checked.
[Archive manual][coco3-service].

Use this source before choosing colours for artwork, palette animation, or
fades. Record the intended display path with the assets. Check the relevant
video and memory registers in the manual before using values from a tutorial.

## Useful exclusions and narrower uses

Do not mistake a promising title for evidence of the needed technique.
These sources were downloaded and sampled but are not manifest additions:

- **Color Computer Graphics**, Ron Clark, PDF 86–93: accessible BASIC movement
  and GET/PUT explanation. Useful optional introduction; lower priority for an
  assembly starter. Its array-sizing explanation should be compared with Polsz's
  article before using it for memory budgets. [Archive book][clark-graphics].
- **Screen Scrolling Made Easy**, Bill Bernico, The Rainbow, October 1987:
  printed page 26 is PDF page 25 in this scan. The examined article describes
  scrolling a completed picture off-screen. Keep it for transitions, not as
  evidence for a bidirectional scrolling game engine. [Archive issue][rainbow-1987-10].
- **MC6847 MOS Video Display Generator**, Motorola: technical pages now examined
  in the focused follow-up below. Promote its chip-level facts only within
  the named MC6847/MC6847Y scope. [Archive datasheet][mc6847].

The sampled books and magazine issues do not represent the whole archive. Other
magazines and later community source releases remain
part of the research scope.

## Magazine discovery and corrections

[The Rainbow searchable index][rainbow-index] is a locator, not hardware
reference material. Its PDF page 56 points to John Blochowiak's **A Smooth
Operator**, January 1988, printed page 78, and a correction in April 1988,
printed page 14. Both are now examined as page images, including the listing's
continuation. The January article occupies printed 78 and 80 / PDF 80 and 82.
The April correction is printed/PDF 14. Do not label it a graphics scrolling engine.

Blochowiak's SMOOTHY changes the 128K CoCo 3's 40-column text scrolling.
It applies to BASIC output such as `LIST`, `DIR`, and `PRINT`.
The article contrasts an eight-pixel character-row jump with one-pixel steps.
It names the scan-line offset and screen-start registers as the mechanism.
This is a useful source for text transitions or a scrolling credits proposal.
It does not establish scrolling terrain, sprites, or a bitmap camera.
Resource `rainbow-1988-01`. [January article][rainbow-1988-01].

The April notice reports that the original fails on 512K CoCo 3 machines.
It changes the value 25 to 217 in BASIC line 170, and 24 to 216 in line 220.
Both lines occur on January printed 80 / PDF 82.
Treat memory configuration as part of this example's requirements.
No version has been reproduced here. The [scrolling guide](../scrolling.md#understand-the-512k-correction)
now cross-checks the display-address fields against Tandy PDF 13 and Tepolt
PDF 29, 33, and 58. The corrected high-address bytes add `$60000`.
Those upper bits alias on 128K but select different RAM on 512K.
This is a sourced explanation, not a runtime or firmware-compatibility result.
Resource `rainbow-1988-04`. [April correction][rainbow-1988-04].

Search titles, authors, and synonyms. A search for `sprite` alone misses useful
articles about `GET`, `PUT`, animation, and graphics storage. Distinguish product
reviews and advertisements from technical explanations and source listings.

Confirm the issue date on the scan. Confirm each PDF page against its printed
page. The October 1987 scan already shows why a single offset is unsafe.
Check corrections and continuation pages before relying on an article.

## VDG source follow-up

Motorola's **MC6847/MC6847Y Video Display Generator**, 1984 DS9823-R1,
printed/PDF 1–23, was examined as page images. The archive filename omits the
MC6847Y name, but the document explicitly covers both non-interlaced and
interlaced versions. It is not the separate MC6847T1 datasheet.
Resource `mc6847`. [Archive datasheet][mc6847].

Useful passages for an agent:

- PDF 12 explains display-address progression from left to right and top to bottom.
- PDF 19, Table 3, maps RG6 screen positions `L7` through `L0` left to right.
  PDF 21, Figure 22, supplies the corresponding `D7` through `D0` byte layout.
  This resolves the chip's bit order, not every board's wiring or emulator output.
- PDF 8 and 13 define the field-sync interval and its relation to active display.
  PDF 11 separates the 192 active lines from borders and retrace.
- PDF 22 distinguishes the generic non-SAM system from the MC6883 system.
  A generic blanking-time memory-access restriction is not a CoCo programming rule.

PDF 20 contains an apparent typo: the RG6 paragraph opens with 256×193,
while its heading, following dimensions, and tables on PDF 14, 18, and 19
consistently specify 256×192. The guide uses the consistent table evidence.
No board timing, physical display, or PAL/GIME compatibility test was performed.
The [colour guide](../colour.md) now routes pixel-order and timing questions
to these passages rather than treating the datasheet as unread.

### Converted coverage for this source pass

The local `mc6847` conversion covers PDF 19–22. Original page images, examined
separately, support the reading of PDF 1–23. A later agent must convert other
cited pages before relying on local Markdown coverage.

The exported full-page images for PDF 19, 21, and 22 were checked against the
source. PDF 19 retains the sideways table, but its OCR merges columns and
misreads bit labels. PDF 21 retains the diagrams as images; its table headers
also contain OCR errors. Read the images for bit positions and signal labels.
These pages were not flagged as sparse, which shows that coverage is not accuracy.

The January issue conversion covers PDF 80 and 82. Both full-page PNGs were
checked. PDF 80 mixes the neighbouring COLORMIX listing into SMOOTHY's text;
PDF 82 reorders DATA lines and separates the listing's columns.
The April issue conversion covers PDF 14. Its exported full-page image was
checked; the correction's line numbers and replacement values match the OCR.
This is a targeted check, not a claim that the whole page's OCR is accurate.

## Rendering and collision pass

The [moving-object guide](../moving-objects.md) turns this pass into
practical advice. The [animation
guide](../animation.md#budget-the-storage-for-animation)
now also covers precomputed coordinates. These are examined sources with
proposed adaptations, not newly reproduced programs.

### Rectangle erasure and placement bounds

Don Inman, Kurt Inman with Dymax, **Assembly Language Graphics for the TRS-80
Color Computer**, chapter 7, printed 151–156 / PDF 159–164, develops a
joystick-controlled shape. The page images show a two-byte by six-row copy,
a matching rectangle clear, and placement clamps. This is a concrete assembly
source for object storage and placement. It is not a background-restoring renderer.
[Archive book][assembly-graphics].

Printed 157–158 / PDF 165–166 introduce interrupts. Printed 163 / PDF 171
shows part of the timed-pylon example. These sampled pages do not establish
that the whole timed program was examined. Printed 168–169 / PDF 176–177 ask
readers to extend the program to two saucers and investigate overlap.
The exercise does not supply an overlap-safe implementation.

Our guide derives the erase limitation from the listing and proposes restoration
and redraw designs. Subsequent original full-redraw examples have bounded
framebuffer evidence, summarized below; save/restore and speed claims remain
unverified.
The book's ROM joystick calls remain version-dependent implementation details.
We did not promote them as a general input API.

### Screen values as collision state

Kenneth Reighard Jr., **The Universal Pick-Up**, *The Rainbow*, October 1992,
cover/PDF 1 and printed/PDF 10, presents *Interplanetary Trash Collector*.
The contents calls it **Inter-Planetary Trash**. The listing is `IPTRASH`.
We examined the introduction, continuation, and complete listing on page 10.
Resource `rainbow-1992-10`. [Archive issue][rainbow-1992-10].

Lines 145–220 draw the old point, read input, advance the position, check bounds,
and dispatch on `PPOINT`. This connects pixel values with game rules.
The guide explains the consequences as our inference from that listing.
It does not claim hardware collision detection or a general sprite system.

The article labels CoCo 3/32K Extended and supplies CoCo 1/2 changes.
It distinguishes RGB and composite settings and explicitly uses the faster clock.
These author-provided options remain untested here. A normal-clock assembly
port needs its own budget and machine contract.

### Other leads and correction limits

- *Undercolor* volume 1 number 1, December 10, 1984: downloaded 28 pages;
  inspected cover and contents, PDF 1–3. The contents offered no direct
  rendering or collision article for that pass. Later [Undercolor research](undercolor-game.md)
  examines four selected articles in other issues; the initial contents sample
  alone remains discovery evidence. [Archive][undercolor-01]
- *Color Computer Magazine*: mapped the archive directory, but selected no
  article in this pass. Directory discovery is not publication coverage.
- Search results for **Graphic Master** in *Hot CoCo* were advertisements and
  a product review. They do not establish its rendering algorithm.
- COMPUTE! results for GET/PUT and XOR concerned IBM BASIC; collision-register
  results concerned Atari. Archive location alone does not make them CoCo evidence.
- This pass supplied neither a sourced tile engine nor a tested mask routine.
  The follow-up below records subsequent tile reading and masking validation.

The Rainbow index PDF 87 locates the October 1992 articles. Its introduction
warns about the final issues' OCR. Targeted title/author correction searches
found no matching correction, but we have not read all later issues.
Errata coverage remains incomplete. Do not describe either program as corrected
or verified merely because its listing was examined.

### Downloads and conversion

The October 1992 issue has 24 PDF pages. Its URL and SHA-256 are pinned in
`resources.json`. The book was already in the manifest. Downloads, extracted
text, and page images remain ignored under `local/`.

Docling converted magazine PDF 3 and 10 with no sparse-page warnings.
Both exported full-page images were checked against direct PDF rendering.
The prose is useful for search, but the page-3 listing is badly garbled and
page 10 merges listing lines. Do not assemble or port that OCR.
Conversion warnings are not a code-correctness detector.

Graphics-book PDF 159–164 also converted, with no sparse-page warnings.
The placement and erase explanations are searchable, but the assembly listing
still corrupts operands. Use the directly examined page images for code details.

## Implementation and validation follow-up

The [moving-object example](../../../examples/moving-objects/README.md) checks
13 frames on each defined CoCo 1/2 configuration. The subsequent
[masked-object example](../../../examples/masked-objects/README.md) checks 12 scenes
on each explicit NTSC, 32 KiB, normal-clock, non-T1 CoCo 1 and CoCo 2 target.
Its independent per-pixel oracle checks transparency, opaque black, draw order,
removal and changed scenery against all framebuffer bytes and guards.
This is original bounded full redraw, not a reproduction of a magazine renderer,
a collision system, clipping or evidence for all CoCo 2 revisions.

The [tile-map guide](../tile-maps.md) documents examined PacDude CoCo 3
map addressing, tile copying and movement rules. The
[legacy tile reading](legacy-tile.md) completes Barden's February 1988
article and both BASIC listings (PDF 173–174, 176, 178–183). Its room graph and
perspective redraw do not supply bitmap tiles or sprite restoration. Reading
is complete for these selected passages. Expanded reading of Droid War,
Dunkey Munkey and Sea Quest adds narrower shape and bitmap-composition findings,
but the historical CoCo 1/2 tile-ID map-renderer source gap remains open.
None of these historical programs was run.

The original [tile-room example](../../../examples/tile-room/README.md#evidence-and-limits)
now checks 42 checkpoints on each explicit NTSC, 32 KiB, normal-clock, non-T1
CoCo 1/2 target. It verifies persistent collection after departure and return,
blocked movement, state, map bytes, framebuffer and guards. The runner enforces
NTSC and excludes user configuration. This is an original full-redraw
implementation, not a historical reproduction or evidence for selective redraw,
physical controls, visible appearance, timing or physical hardware.

The [plan](../../../PLAN.md) retains the remaining source survey and validation scope,
including broader magazine and errata reading, CoCo 1/2 bitmap tile sources,
selected original reproductions, and display/audio/hardware limits.

## Conversion evidence

The later [six-page inspection](../../starter/conversion-quality.md) compares selected
assembly/listing pages, tables and diagrams with source renders and all eleven
exported images. It records specific OCR failures and when to read the image.
Its isolated conversions leave shared indexes and checkpoints unchanged;
Matthews pages 44/46 are not thereby added to shared active Markdown coverage.
These selected checks do not establish whole-book accuracy.

In the first batch, thirteen selected pages were processed through the starter's
Docling pipeline.
The first conversion of CoCo 3 service-manual pages 16–18 produced empty OCR.
The exported page-17 PNG was also blank, although direct PDFium rendering worked.

The converter now compares low-contrast pages with a direct PDFium render.
If the original contains visible detail, it retries OCR, layout, and image
extraction through Docling's PDFium backend. The repaired page-17 image was
visually checked against the original. Its palette text and tables are now
searchable, but OCR still merges the white and black row labels.

Rerun the affected range to replace the old output:

```sh
uv run python scripts/setup.py --resource coco3-service --pages 16:18
```

Conversion profile 3 creates fresh checkpoints. It preserves PDF page numbers
and leaves old checkpoints on disk without using them in the new index.
This check catches the observed nearly blank rendering failure. It does not
prove every image, table, or character is correct.

Tepolt's PDF 59 contains damaged OCR sentences even though the page was not
flagged as sparse. The original page image was checked for the scrolling
recommendation. Treat sparse flags as warnings, not as a complete quality test.
Magazine samples retain useful text, but their column order and listings still
need visual checks. These samples do not establish whole-document OCR quality.

## Obtain only the pages needed

List available sources with `uv run python scripts/setup.py --list`.
Use your project's existing target. For example, in a CoCo 3 project:

```sh
uv run python scripts/setup.py --target coco3 \
  --resource tepolt-coco3 --pages 59:60
```

For the compact storage article in a CoCo 2 project:

```sh
uv run python scripts/setup.py --target coco2 \
  --resource rainbow-1986-10 --pages 118:119
```

Use explicit `--resource` and `--pages` selections. The manifest includes full
issues, but setup without selections converts all resources. Do not start
that large conversion merely to find one technique.

Read the page text, then open its linked full-page PNG for tables and code.
Magazine OCR can mix columns, adverts, and listings. Never copy OCR code into
an implementation without checking it against the page image.

The repository contains descriptions, links, and checksums only. Downloaded
PDFs, extracted text, and images stay under ignored `local/`.

[rainbow-index]: https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow,%20The%20-%20Text%20Searchable%20Index/The%20Rainbow%20-%20Text%20Searchable%20Index.pdf
[clark-graphics]: https://colorcomputerarchive.com/repo/Documents/Books/Color%20Computer%20Graphics%20(Ron%20Clark).pdf
[coco3-service]: https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%203%20Service%20Manual%20(Tandy).pdf
[mc6847]: https://colorcomputerarchive.com/repo/Documents/Datasheets/MC6847%20MOS%20Video%20Display%20Generator%20(Motorola).pdf
[tepolt-coco3]: https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20(1987)%20(Laurence%20A%20Tepolt).pdf
[rainbow-1987-10]: https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow,%20The%20(OCR)/The%20Rainbow%20Vol.%2007%20No.%2003%20-%20October%201987.pdf

[assembly-graphics]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Graphics%20for%20the%20TRS-80%20Color%20Computer%20%28Don%20Inman%2C%20Kurt%20Inman%20with%20Dymax%29.pdf>

[rainbow-1992-10]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow,%20The%20(OCR)/The%20Rainbow%20Vol.%2012%20No.%2003%20-%20October%201992.pdf>

[undercolor-01]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Undercolor/Undercolor%20v01n01%20%281984%29%28ColorPlus%20Inc%29.pdf>

[rainbow-1988-01]: https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow,%20The%20(OCR)/The%20Rainbow%20Vol.%2007%20No.%2006%20-%20January%201988.pdf#page=80
[rainbow-1988-04]: https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow,%20The%20(OCR)/The%20Rainbow%20Vol.%2007%20No.%2009%20-%20April%201988.pdf#page=14
