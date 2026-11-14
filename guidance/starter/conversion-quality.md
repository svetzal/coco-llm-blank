# Choose reference text or images

Read this when a reference search reaches assembly code, a numeric table,
a diagram, or a magazine with several columns. Start with
[reference lookup](references.md) for acquisition and page navigation.
Use OCR to find a passage. Use the image to establish exact syntax, row
membership, bit labels, circuit connections, and reading order.

## Decide before copying

- Prose: search Markdown, then inspect the page when sentences jump, start
  mid-word, or cross article boundaries. A fluent sentence can still combine
  different columns.
- Tables: open the full page. Check the header hierarchy, row boundaries,
  footnotes, and which labels span several rows before taking values.
- Assembly or BASIC: read the image at useful magnification. Check punctuation,
  zero versus letter O, operands, line continuations, and listing order.
  Assemble or run an independently checked adaptation before calling it tested.
- Diagrams: open the linked figure and its full page. The caption is searchable;
  the wires, arrows, and labels might exist only in the PNG.
- An unclear original: retain the uncertainty. OCR correction cannot repair a
  missing symbol in the printed source. Consult another primary passage before
  implementing the dependent behavior.

These are workflow recommendations derived from the observations below, not
claims made by the historical authors. No historical program was executed in
this check, and no hardware behavior was measured.

## Six-page inspection

Checked on 2026-11-14 using actual selected-page Docling conversion, copied
source PDFs, and an isolated output store. All six source pages were rendered
separately with PDFium and visually inspected against exported images and
Markdown. All five exported figure crops were also inspected.

The sample covers a CoCo 1 manual, a CoCo 2 manual, a CoCo 3 manual, a graphics
instruction table, and two Matthews magazine pages. It is deliberately difficult,
not random or balanced by machine. It cannot estimate book-wide accuracy or
certify CoCo 1/2/3 compatibility of the historical examples.

### Assembly graphics, PDF 108, printed 99

Source [A], Table 5-2. Markdown moves the last store from the first 6R colour
set into the next colour-set row. It also merges the 3R and 2R colour labels and
instruction groups. The zero in one hexadecimal operand becomes letter O.
The full-page export retains the table boundaries; no figure crop is emitted.

Open the full page even when the instruction appears in search results. Read
each colour-set block as a unit. The first load's missing immediate-marker
appearance is present in the source image too; do not classify that as an OCR
loss or silently repair it from memory. This page alone is not a complete
machine initialization procedure.

### CoCo 1 technical manual, PDF 31, printed 24

Source [B], Table 1. The three leftmost SAM headers are visibly V2, V1, V0.
Markdown changes the first to a square-root-like symbol and drops the other
two labels. The next group is PIA bits, followed by a separate data-bit group.
The full-page export keeps these distinctions; no separate figure is emitted.

Search the mode name, then read the image header and the desired row together.
Keep the X/N legend with the table. Do not infer that unlabeled Markdown
columns are extra PIA bits, or that a blank header means a don't-care value.

### CoCo 2 NTSC service manual, PDF/printed 33

Source [C], Figure 4-8. The figure crop retains the circuit, including the
input labels, connection dots, component labels, and Phase A output. It omits
the caption and explanatory paragraphs, which remain on the full page and
in Markdown. The circuit itself is not transcribed as searchable text.

Use the crop for connections and the full page for the two prose columns.
Read the left column before the right. A search that finds the caption but no
component value is not evidence that the value is absent from the source.
This check covers the manual's named NTSC models, not every CoCo 2 board.

### CoCo 3 service manual, PDF/printed 17

Source [D], Color Palette. The source image has separate White and Black
entries. Markdown merges their labels in the first row and leaves the next
row label blank. Zero-valued bit suffixes become letter O in several headers.
The full-page export is readable; no figure crop is emitted.

Use the image to associate each colour with its RGB and composite columns.
Keep the initialization list and the PAL qualification in view. The conversion
log contains an empty-OCR warning before successful output; the final image
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
content. Use their visible captions, not their filenames, when citing them.

### Matthews, October 1987 Rainbow, PDF/printed 46

Source [E], article continuation and ENERGY listing. Markdown interleaves
three prose columns and rearranges code from the two listing columns. It
misreads slashed zeros, breaks keywords across lines, and loses part of the
long DRAW string on line 210. Sorting the extracted line numbers cannot
restore the missing characters or fix wrapped statements.

Read the prose left to right by column, then the listing down its left column
before its right column. The sole figure crop is the small check-value box,
not the program. Use the full-page PNG for code. This sample ends at line 420;
it is not the whole listing. Consult the article continuation identified in
[the animation guide](../techniques/animation.md) before adapting the program.
Page 47 was not reconverted or visually assessed in this six-page check.

## Coverage and conversion state

The run used profile format 3, Docling 2.150.0, docling-core 2.107.0, and
RapidOCR 3.10.0, with full-page English OCR, table recognition, and 2x image
rendering. All six conversions completed. Eleven PNGs were exported: six full
pages and five crops. All eleven files matched their checkpoint SHA-256 values.
No selected page was marked sparse, despite the errors above. These counts
measure completion and artifact integrity, not recognition accuracy.

At selection time, the shared Matthews extraction record listed only page 47
under format 3. Pages 44 and 46 existed under format 2. This is a profile
coverage mismatch, not evidence that those pages are absent from the magazine.
The fresh format-3 conversions here still have reading-order and listing errors.
They do not establish an improvement over format 2. Shared checkpoints and
indexes were left untouched.

For any resource, read `extraction.json` before searching. Follow its
`checkpoints` path and `completed_pages`; do not combine arbitrary checkpoint
folders. A missing page requires selected-page conversion. A missing search
hit on a completed page requires image inspection before ruling out content.

The local evidence is under `local/research/conversion-quality/`:
`selection.json` records source URLs, hashes, selected pages and previous
extraction records; each resource directory contains its source copy, Markdown,
extraction record, page JSON and PNGs. `checks.json` records image integrity and
raster comparisons; `conversion.log` retains warnings; `converter.sha256`
identifies the converter file used. Source renders and exports have equal
sizes but are not pixel-identical. No pixel difference threshold or OCR score
was used to infer correctness.

## Reproduce without changing shared checkpoints

Run from the repository root with the existing project environment and the
five source PDFs already downloaded. The code below is original inspection
orchestration, not copied book code. It uses the production converter directly,
requests exactly six pages, and creates a new isolated directory on each run.
It does not run setup, rewrite the local index, or convert a whole book.

```sh
uv run --no-sync python - <<'PY'
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path('scripts').resolve()))
from references import DoclingGateway, Resource, convert, digest

selected = {
    'assembly-graphics': [108],
    'coco1-technical': [31],
    'coco2-service': [33],
    'coco3-service': [17],
    'rainbow-1987-10': [44, 46],
}
parent = Path('local/research/conversion-quality')
parent.mkdir(parents=True, exist_ok=True)
root = Path(tempfile.mkdtemp(prefix='repeat-', dir=parent))
gateway = DoclingGateway()
for record in json.loads(Path('resources.json').read_text()):
    if record['id'] not in selected:
        continue
    resource = Resource(**record)
    source = Path('local/references') / resource.id / 'source.pdf'
    assert digest(source) == resource.sha256
    output = root / resource.id
    output.mkdir()
    shutil.copyfile(source, output / 'source.pdf')
    for page in selected[resource.id]:
        print(convert(resource, output, (page, page), documents=gateway))
print(root)
PY
```

For an independent raster view, render the copied PDF with
`pypdfium2.PdfDocument`, select `document[page - 1]`, and save
`render(scale=2).to_pil()` under that same isolated directory. Open the PNG
with an image-viewing tool; do not infer diagram content by inspecting bytes.
Compare the requested passage with the full-page export and any linked crops.
Expected failure controls are the displaced instruction on A/108, missing SAM
headers on B/31, merged colour labels on D/17, and column interleaving on E/46.
An inspection method that accepts those Markdown passages without an image
check is insufficient for exact transcription.

## Source identities

PDF page citations above identify the inspected passages. Archive links and
SHA-256 values below identify the exact downloaded editions. Hashes were
verified locally before copying. Copyrighted pages and extracted content stay
in ignored local storage.

- [A] Assembly Language Graphics for the TRS-80 Color Computer
  (Don Inman, Kurt Inman with Dymax), [archive PDF](<https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Graphics%20for%20the%20TRS-80%20Color%20Computer%20%28Don%20Inman%2C%20Kurt%20Inman%20with%20Dymax%29.pdf>).
  SHA-256: `c1259497b7d1505e6908fd3c8a250d47e0c4b549140e308bdc6bf8e345b6ce01`.

- [B] [Color Computer Technical Reference Manual (Tandy)](<https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%20Technical%20Reference%20Manual%20%28Tandy%29.pdf>).
  SHA-256: `8c4ed0c6de6e54f941932999d6750202f75102bff061f215b2dd3f757067cc64`.

- [C] [Color Computer 2 NTSC Service Manual (26-3134 & 26-3136) (Tandy)](<https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%202%20NTSC%20Service%20Manual%20(26-3134%20&%2026-3136)%20(Tandy).pdf>).
  SHA-256: `7210e7a0da2b5211bc95a5833759a15fb575a5cc5787a0d9cbfa3c09b1622447`.

- [D] [Color Computer 3 Service Manual (Tandy)](<https://colorcomputerarchive.com/repo/Documents/Manuals/Hardware/Color%20Computer%203%20Service%20Manual%20(Tandy).pdf>).
  SHA-256: `5c4c82d1b825daacf861be097d93d0a0eff78fbdf394234d4adb06df0cfd3c29`.

- [E] [The Rainbow Vol. 07 No. 03 - October 1987](<https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow,%20The%20(OCR)/The%20Rainbow%20Vol.%2007%20No.%2003%20-%20October%201987.pdf>).
  SHA-256: `d41c55e0cdcadb693513a44af247ba725e93155f19c7e91ca957c8aa6118a029`.
