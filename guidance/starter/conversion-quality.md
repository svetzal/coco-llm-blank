# Choose reference text or images

Read this when a reference search reaches one of these:

- assembly code
- a numeric table
- a diagram
- a magazine with several columns

Start with [reference lookup](references.md) for acquisition and page
navigation. Use OCR to find a passage. Use the image to establish exact
syntax, row membership, bit labels, circuit connections, and reading order.

## Decide before copying

- Prose: search Markdown. Then inspect the page when sentences jump, start
  mid-word, or cross article boundaries. A fluent sentence can still combine
  different columns.
- Tables: open the full page. Before you take values, check the header
  hierarchy, row boundaries, footnotes, and which labels span several rows.
- Assembly or BASIC: read the image at useful magnification. Check punctuation,
  zero versus letter O, operands, line continuations, and listing order.
  Assemble or run an independently checked adaptation before you call it tested.
- Diagrams: open the linked figure and its full page. The caption is searchable.
  The wires, arrows, and labels might exist only in the PNG.
- An unclear original: retain the uncertainty. OCR correction cannot repair a
  missing symbol in the printed source. Consult another primary passage before
  you implement the dependent behavior.

These are workflow recommendations derived from the observations below. They
are not claims made by the historical authors. This check ran no
historical program and measured no hardware behavior.

## Six-page inspection

Checked on 2026-11-14 with Docling 2.150.0 and RapidOCR 3.10.0. We compared
a separate PDFium render of each source page with the exported images and
Markdown.

The sample covers:

- a CoCo 1 manual
- a CoCo 2 manual
- a CoCo 3 manual
- a graphics instruction table
- two Matthews magazine pages

The sample is deliberately difficult, not random or balanced by machine. It
cannot estimate book-wide accuracy. It cannot certify CoCo 1/2/3 compatibility
of the historical examples.

### Assembly graphics, PDF 108, printed 99

Source [A], Table 5-2. Markdown moves the last store from the first 6R colour
set into the next colour-set row. It also merges the 3R and 2R colour labels and
instruction groups. The zero in one hexadecimal operand becomes letter O.
The full-page export retains the table boundaries. The conversion emits no
figure crop.

Open the full page even when the instruction appears in search results. Read
each colour-set block as a unit. In the source image too, the first load
appears to lack its immediate marker. Do not classify that as an OCR loss.
Do not silently repair it from memory. This page alone is not a complete
procedure for machine initialization.

### CoCo 1 technical manual, PDF 31, printed 24

Source [B], Table 1. The three leftmost SAM headers are visibly V2, V1, V0.
Markdown changes the first to a square-root-like symbol and drops the other
two labels. The next group is PIA bits, followed by a separate data-bit group.
The full-page export keeps these distinctions. The conversion emits no
separate figure.

Search the mode name. Then read the image header and the desired row together.
Keep the X/N legend with the table. Do not infer that unlabeled Markdown
columns are extra PIA bits. Do not infer that a blank header means a
don't-care value.

### CoCo 2 NTSC service manual, PDF/printed 33

Source [C], Figure 4-8. The figure crop retains the circuit, including the
input labels, connection dots, component labels, and Phase A output. It omits
the caption and explanatory paragraphs, which remain on the full page and
in Markdown. The conversion does not transcribe the circuit itself as
searchable text.

Use the crop for connections and the full page for the two prose columns.
Read the left column before the right. A search that finds the caption but no
component value is not evidence that the value is absent from the source.
This check covers the manual's named NTSC models, not every CoCo 2 board.

### CoCo 3 service manual, PDF/printed 17

Source [D], Color Palette. The source image has separate White and Black
entries. Markdown merges their labels in the first row and leaves the next
row label blank. Zero-valued bit suffixes become letter O in several headers.
The full-page export is readable. The conversion emits no figure crop.

Use the image to associate each colour with its RGB and composite columns.
Keep the initialization list and the PAL qualification in view. The conversion
log contains an empty-OCR warning before successful output. The final image
has content. Neither a warning alone nor eventual success establishes accuracy.
The page's printed values have not been validated electrically or in an emulator.

### Matthews, October 1987 Rainbow, PDF/printed 44

Source [E], opening page of *Electrifying Graphics Using PMODE Power*.
Markdown begins with the right-column continuation before the opening prose
at bottom left. The split word connecting those columns remains separated.
The heading also gains a stray character.

Read the full-page image for article order. The exported crop named
`figure-001` is the publication badge, `figure-002` contains printed Figure 2,
and `figure-003` contains printed Figure 1. Crop sequence is not printed figure
numbering. The two illustration crops also include fragments of neighboring
content. Use their visible captions, not their filenames, when you cite them.

### Matthews, October 1987 Rainbow, PDF/printed 46

Source [E], article continuation and ENERGY listing. Markdown interleaves
three prose columns and rearranges code from the two listing columns. It
misreads slashed zeros, breaks keywords across lines, and loses part of the
long DRAW string on line 210. Sorting the extracted line numbers cannot
restore the missing characters or fix wrapped statements.

Read the prose left to right by column. Then read the listing down its left
column before its right column. The sole figure crop is the small check-value
box, not the program. Use the full-page PNG for code.

This sample ends at line 420. It is not the whole listing. Before you adapt
the program, consult the article continuation identified in
[the animation guide](../techniques/animation.md).
This six-page check did not reconvert or visually assess page 47.

## Read the extraction record first

For any resource, read `extraction.json` before you search. Use its
`checkpoints` path and `completed_pages`. Do not combine arbitrary checkpoint
folders. A missing page needs selected-page conversion. A missing search
hit on a completed page needs image inspection before you rule out content.

The conversion marked none of the six pages as sparse, despite the errors
above. A completed conversion and valid image checksums measure completion,
not recognition accuracy.

## Sources

The letters above identify these resources. `resources.json` gives the URL
and the checksum of each one.

- [A] `assembly-graphics`: Don Inman, Kurt Inman with Dymax, *Assembly
  Language Graphics for the TRS-80 Color Computer*.
- [B] `coco1-technical`: Tandy, *Color Computer Technical Reference Manual*.
- [C] `coco2-service`: Tandy, *Color Computer 2 NTSC Service Manual (26-3134
  & 26-3136)*.
- [D] `coco3-service`: Tandy, *Color Computer 3 Service Manual*.
- [E] `rainbow-1987-10`: *The Rainbow*, Vol. 7 No. 3, October 1987.
