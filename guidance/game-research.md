# Research for games and demos

Load this guide when choosing techniques or references for a game or demo.
Use [reference lookup](references.md) to obtain and inspect the selected pages.
This guide records a first research batch, not a complete survey or tested engine.

Stacey requested equal attention to CoCo 1, CoCo 2, and CoCo 3. Select by
reusable techniques rather than a preferred game genre. Assembly remains the
starter's implementation baseline. BASIC articles can explain useful ideas.
Their ROM calls, storage formats, and performance do not transfer automatically.

## Choose by the effect you want

| Need | Start with | Evidence and limits |
| --- | --- | --- |
| Small animated objects | Polsz, `rainbow-1986-10`, PDF 118–119 | Examined text and figure. Compact GET/PUT storage; BASIC-specific. |
| Alternate prepared frames | Matthews, `rainbow-1987-10`, PDF 44 and 46 | Examined explanation and listing. Hidden drawing screen versus visible screen. |
| Smooth horizontal scrolling on CoCo 3 | Tepolt, `tepolt-coco3`, PDF 59 | Examined page image. Pre-shifted buffers trade memory for motion granularity. |
| Banked assets with interrupts on CoCo 3 | Tepolt, `tepolt-coco3`, PDF 59–60 | Examined page images. Keep interrupt tables and handlers accessible. |
| Match CoCo 2 artifact colours | Tandy, `coco2-service`, PDF 31–33 | Examined hardware discussion. Specific NTSC models, not all CoCo 2 variants. |
| Choose CoCo 3 colours for a display | Tandy, `coco3-service`, PDF 17 | Examined palette tables. RGB and composite encodings differ; PAL caveat applies. |
| Find more magazine techniques | `rainbow-index` | Discovery only. Find the issue, then inspect the actual article and corrections. |

These are source-backed reading recommendations. None of the newly selected
techniques has been implemented or benchmarked in this research batch.

## CoCo 1 and CoCo 2 animation

### Compact object storage

Steven R. Polsz's **Optimum Animation**, The Rainbow, October 1986,
printed pages 116–117 (PDF 118–119), compares oversized BASIC arrays with
compact storage for an example object. It includes a pixel diagram and an
experiment that compares the stored values. [Archive issue][rainbow-1986-10].

Use it to investigate asset memory budgets and how pixel packing differs from
language-level array storage. It is particularly useful beside beginner books
that size arrays by picture dimensions. Do not treat its percentage saving as
a general compression result. Do not adopt the sizing rule without checking
rounding, mode, dimensions, and the actual GET/PUT implementation.

Scope: legacy PMODE and Extended Color BASIC. CoCo 1/2 are the first targets
for reproduction. CoCo 3 compatibility mode needs its own check. This is not
a native CoCo 3 graphics or hardware-sprite technique.

### Prepared frames and hidden drawing

Becky F. Matthews's **Electrifying Graphics Using PMODE Power**, The Rainbow,
October 1987, printed/PDF pages 44 and 46–47, explains two prepared pictures
and alternating displays. The examined explanation is on pages 44 and 46.
The remainder of the listing on page 47 still needs inspection.
[Archive issue][rainbow-1987-10].

The useful distinction is between the screen being drawn and the screen being
shown. Apply that idea to short animation cycles, title screens, and scene
transitions. This article shows fixed prepared frames. It does not
establish a general real-time renderer, vertical-sync discipline, or collision
system. Its BASIC delays are not an assembly timing contract.

Scope: the article labels its example 16K ECB. Recheck memory budgets for other
modes, larger assets, or more frames.

## CoCo 2 display differences

Tandy's **Color Computer 2 NTSC Service Manual**, models 26-3134 and 26-3136,
PDF/printed pages 31–33, explains video generation and artifact circuitry.
[Archive manual][coco2-service].

The discussion ties artifact appearance to the colour burst and its phase.
That makes it useful when a recreation has correct bitmap bytes but wrong
colours on the chosen display. Treat NTSC, PAL, RGB, and emulator display
settings as separate cases. This manual covers the named NTSC models. Do not
use it as evidence for every CoCo 2 board or VDG revision.

A later implementation check should use asymmetric pixel patterns and record
the display path. A framebuffer comparison alone cannot establish artifact
colour appearance.

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
- **Live And In Concert On CoCo's Stage**, Brian P. Roden, The Rainbow,
  April 1985, PDF/printed page 124: animation with cassette audio through the
  television. It is not evidence for CPU-generated background music.
  [Archive issue][rainbow-1985-04].
- **Screen Scrolling Made Easy**, Bill Bernico, The Rainbow, October 1987:
  printed page 26 is PDF page 25 in this scan. The examined article describes
  scrolling a completed picture off-screen. Keep it for transitions, not as
  evidence for a bidirectional scrolling game engine. [Archive issue][rainbow-1987-10].
- **MC6847 MOS Video Display Generator**, Motorola: downloaded, but technical
  pages have not been examined. Do not cite it yet for pixel order or timing.
  [Archive datasheet][mc6847].

The two books and three magazine issues inspected here do not represent the
whole archive. Other magazines and later community source releases remain
part of the research scope.

## Magazine discovery and corrections

[The Rainbow searchable index][rainbow-index] is a locator, not hardware
reference material. Its PDF page 56 points to John Blochowiak's **A Smooth
Operator**, January 1988, printed page 78, and a correction in April 1988,
printed page 14. The index describes 40-column scrolling. Neither article nor
correction has been examined yet. Do not label it a graphics scrolling engine.

Search titles, authors, and synonyms. A search for `sprite` alone misses useful
articles about `GET`, `PUT`, animation, and graphics storage. Distinguish product
reviews and advertisements from technical explanations and source listings.

Confirm the issue date on the scan. Confirm each PDF page against its printed
page. The October 1987 scan already shows why a single offset is unsafe.
Check corrections and continuation pages before relying on an article.

## Conversion evidence

Thirteen selected pages were processed through the starter's Docling pipeline.
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
[coco2-service]: https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%202%20NTSC%20Service%20Manual%20(26-3134%20&%2026-3136)%20(Tandy).pdf
[mc6847]: https://colorcomputerarchive.com/repo/Documents/Datasheets/MC6847%20MOS%20Video%20Display%20Generator%20(Motorola).pdf
[tepolt-coco3]: https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Programming%20for%20the%20CoCo3%20(1987)%20(Laurence%20A%20Tepolt).pdf
[rainbow-1987-10]: https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow,%20The%20(OCR)/The%20Rainbow%20Vol.%2007%20No.%2003%20-%20October%201987.pdf
[rainbow-1985-04]: https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow,%20The%20(OCR)/The%20Rainbow%20Vol.%2004%20No.%2009%20-%20April%201985.pdf
[rainbow-1986-10]: https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow,%20The%20(OCR)/The%20Rainbow%20Vol.%2006%20No.%2003%20-%20October%201986.pdf
