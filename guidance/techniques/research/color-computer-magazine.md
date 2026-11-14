# Color Computer Magazine game-loop research

Read this for the source evidence behind [game-loop design](../game-loop.md).
This bounded pass examined four articles in four issues, including both parts
of Barden's animation series and a related published correction. It did not run
any historical program or implement an adaptation.

## Scope and promotion

The useful connection is control flow: when a program accepts a command, when
it prepares graphics, and when it commits to playing a sequence. Existing
[controls](../controls-and-collision.md),
[turn-state](../game-state.md) and
[animation](../animation.md) guides cover adjacent concerns. The new
[game-loop guide](../game-loop.md) adds an explicit contract for input
across preparation, playback and return to play, plus a bounded cooperative
sequence proposal. It does not supply a general arcade scheduler.

Promote that guide as examined-source guidance with untested original
pseudocode. Navigation and manifest integration are left to the parent task;
this pass owns neither file. No speed, portability or responsiveness claim
has been validated. These early issues supply original-CoCo evidence, not
balanced coverage of all three machines. Later publications remain necessary.

## Sources and reading coverage

All URLs below identify primary scans at Color Computer Archive. PDF positions
are one-based. Printed page offsets differ between issues; do not infer one
issue's offset from another. The IDs here are research-local, not manifest IDs.

- `ccm-field-honor`: Scott Norman (listing credits Scott L. Norman),
  "Field of Honor", March 1983, premiere issue. Printed 24–27; PDF 22–25.
  Prose and complete listing 10–2300 examined.
- `ccm-sorcerer`: Richard Ramella, "The Sorcerer's Puzzles", April 1983,
  Vol. 1 No. 2. Printed 32–35; PDF 34–37. All prose and three complete
  listings examined.
- `ccm-animation-1`: William Barden Jr., "Color Animation", Part I,
  May 1983, Vol. 1 No. 3. Printed 25–26, 28–31, 34; PDF 23–24, 26–29, 32.
  All prose, figures 1–8 and listings 1–2 examined.
- `ccm-animation-2`: William Barden Jr., "Color Animation, Part II",
  June 1983, Vol. 1 No. 4. Printed 32–35; PDF 34–37. All prose,
  memory-map figure and listings 1–3 examined.

The additional correction is Richard Ramella's "Sorcerer's Mistake", June
1983, printed 12, PDF 14, in INKEY$. Its entire letter and replacement lines
were examined. [Correction scan][correction]

Local files are in ignored `local/research/color-computer-magazine/`. The four
PDFs are named `8303.pdf` through `8306.pdf`; rendered pages use
`<issue>-<PDF-position>.png`. Downloaded scans, extracted text and page images
must remain outside Git. Archive availability is not a redistribution license.

| Local PDF | Archive URL | PDF pages | SHA-256 |
| --- | --- | --- | --- |
| `8303.pdf` | [March scan][march] | 64 | `311edc50d2a07df98dd9a4deedf5d2bd4e66cafe780f29c16c82cc454556ac8d` |
| `8304.pdf` | [April scan][april] | 68 | `d1f5b1a7bc12687f138c33abe4d0627e1dd07c0dc3ebae914bb18dfe02c57136` |
| `8305.pdf` | [May scan][may] | 80 | `af82f0ef4523f03d2e7876741e20e857f522547579ab717fff6c7d8639336759` |
| `8306.pdf` | [June scan][june] | 100 | `029cdc12dcb8fb92808c9b22a0c9c34db2c2a897cad058c2213bb1fda57139b3` |

## Field of Honor: preparation and playback are different phases

Norman describes a 32K Extended Color BASIC program with a 16K modification.
The main version uses three prepared PMODE 1 images across six graphics pages.
A text message stays visible while it constructs the images. Later bouts
against the same opponent reuse them. The smaller version reduces the sequence
to two images and removes the musical introduction. These are published
requirements and modifications, not our compatibility results.
[Printed 24–25, PDF 22–23][honor]

The listing makes the phases concrete. Lines 980–1050 collect strategies;
1140 calls the graphics routine. Line 230 skips rebuilding when `BN>1`.
Lines 590–600 wait for a charge command. Lines 640–750 cycle prepared pages
with changing delays and an interleaved PLAY command, then return. Outcome
calculation follows at 1190–1200. That playback path contains no INKEY$ call.
[Printed 26–27, PDF 24–25][honor-listing]

Our reading: this is a command followed by a noninteractive presentation,
not movement controlled during the animation. Reusing images saves repeated
preparation but ties their validity to the opponent and picture content.
A new game's cache must include every change that affects the picture.
The article's preparation-time estimate is not a benchmark for this project.

The prose explicitly adds defensive-choice validation and moves the bout-count
increment after it (1055 and 1057); the printed listing still increments at
1050 and lacks those added lines. Preserve the prose fix when studying the
listing. The scanned condition appears as `C<` without a readable lower-bound
operand, so this note does not claim an exact executable transcription.
The displayed menu has choices 1–5. The intent to validate before incrementing
is clear; a reproduction must reconcile the damaged expression.
[Printed 25, PDF 23; listing printed 27, PDF 25][honor-fix]

## The Sorcerer's Puzzles: waiting can still have presentation work

Color Stones polls INKEY$ at 340–350 until it recognizes a supported key,
updates cursor or stones at 360–390, and prints both rows at 400–410. No
accepted key means no redraw through that path. The move log belongs to the
stone-change routine, not cursor motion. [Printed 33, PDF 35][stones]

Red Rover instead reads a key at 210, prints a count, erases the cursor, runs
a delay and restores it at 230–270, then interprets the sampled key at
280–310. The route tests use screen points, and the score counts direction
changes at 650–670. Thus idle passes can animate the cursor without advancing
the route. Our deduction is that presentation work sits between sampling and
acting on the key. This is not a measured input-latency result.
[Printed 34, PDF 36][rover]

Firecracker polls within its four-pass loop at 390–400. Lines 450–500 process
an erase command and update sequence counters; 530–640 update the cursor,
blink a point with delays and redraw the number rows. Its end paths become
repeating effects. A future restart or cancel action would need an explicit
exit from those paths. [Printed 35, PDF 37][firecracker]

The April heading says 4K Color BASIC. Ramella's June correction explains
that Color Stones and Firecracker use MID$ assignment syntax requiring
Extended Color BASIC; he supplies replacements using string concatenation
for Color BASIC. The correction covers Color Stones lines 300, 360, 390,
490–500 and Firecracker line 460. Red Rover is not named in that correction.
Do not repeat the April compatibility label without the June qualification.
[June printed 12, PDF 14][correction]

## Color Animation: move construction outside repeated presentation

Part I builds a pose from reusable body, arm and leg descriptions. Five
unique poses produce eight positions in the repeated sequence. Listing 1
redraws and clears each time. Listing 2 constructs and paints each unique
pose once, captures rectangles, and cycles PUT calls over a fixed footprint.
Figures 2 and 8 show the motion sequence and enclosing rectangle.
[May printed 26, 28–31, 34; PDF 24, 26–29, 32][animation-one]

The fixed footprint explains the article's no-clear playback: each rectangle
contains the background as well as the figure. It is not a demonstration of
transparent drawing or restoration after translation. Prepared images consume
storage and preparation work even though playback avoids repeating DRAW and
PAINT. Neither listing polls controls during its repeating display loop.
That is appropriate evidence for a demo, not for a responsive game loop.
[May listing 2, printed 28–29, PDF 26–27; explanation printed 34, PDF 32][animation-list]

Part II replaces BASIC GET/PUT with assembly copy routines called through
BASIC USR functions. Its BASIC host still controls the eight-call sequence.
The article labels the example 16K Extended Color BASIC. Its memory diagram
reserves five buffers at 700-byte intervals beginning at $3000, and code at
$3FC0; the listing calls a ROM integer-conversion routine at $B3ED. These
addresses describe this historical example, not a portable allocation or ROM
interface. [June printed 32–35, PDF 34–37][animation-two]

Two limits matter before adapting it:

- The prose says 648 bytes for 36 by 76 two-bit elements, while its stated bit
  count is 5,184. Our arithmetic gives 5,472 bits, or 684 bytes. The assembly
  listing copies nine bytes per row over 76 rows, also 684 bytes. The 700-byte
  buffer spacing accommodates that payload. This is a source discrepancy, not
  a published correction or runtime finding. [Printed 33–34, PDF 35–36][copy]
- The prose calls the code relocatable, but the displayed routine retains
  absolute screen constants and a ROM call. Moving its code is not evidence
  that it works with another display layout, ROM revision or machine model.
  Reconcile those dependencies before reuse. [Same pages][copy]

Barden reports approximate rates and visible improvement in both parts;
June explicitly says the timing was not exact. No numeric rate is adopted
here as a measured result or target guarantee. The series compares prepared
copying with repeated construction; it does not measure controls, gameplay,
audio interference or a whole game frame budget.

May printed 34 labels its continuation as coming from page 32, while the
preceding prose ends on printed 31 with a direction to page 34. PDF 30–31
are advertisements. June's reference to the prior BASIC version as Listing 3
is resolved by its reprint on printed 35, PDF 37. These navigation details
are retained so a future reader does not mistake an advertisement for a
missing technical continuation.

## Correction search and reading limitations

The bounded check inspected April contents/editorial (PDF 4 and 6), May
contents/editorial (PDF 4), June contents/editorial (PDF 4 and 6), and June's
INKEY$ letters at printed 10 and 12 (PDF 12 and 14). June's editorial identifies
INKEY$ as a new department. The relevant result is Ramella's correction above.
No correction to Norman or Barden was found in these inspected pages. Later
letters, other departments and later issues were not searched exhaustively.
The in-article Norman fix was examined separately. This is not evidence that
no other errata exist.

`pdftotext -layout` on the March scan produced blank page text. That failed
extraction is not a negative topic-search result. All article pages and figures
listed above were read from rendered images. Listings were visually inspected,
not OCR-transcribed into runnable programs. A first image read encountered an
unfinished PNG; it was repeated successfully after rendering completed.
There is no Docling conversion-quality or manifest-coverage claim here.

To repeat the source inspection, download the linked PDFs into the ignored
folder, check their hashes, and render only the page ranges in the coverage
list. With existing Poppler tools, for example:

```sh
mkdir -p local/research/color-computer-magazine
archive='https://colorcomputerarchive.com/repo/Documents/Magazines'
issue='Color%20Computer%20Magazine%20-%208303%20-%20March%201983.pdf'
curl --fail --location "$archive/Color%20Computer%20Magazine/$issue" \
  --output local/research/color-computer-magazine/8303.pdf
shasum -a 256 local/research/color-computer-magazine/8303.pdf
pdfinfo local/research/color-computer-magazine/8303.pdf
pdftoppm -f 22 -l 25 -scale-to 2100 -png \
  local/research/color-computer-magazine/8303.pdf \
  local/research/color-computer-magazine/march-article
```

The source-reading procedure is retained here; no private experiment code is
needed because no runtime experiment was performed. No build, execution,
framebuffer, rendered-program, audible or physical-hardware result follows.
Scanned magazine illustrations are historical figures, not our display checks.

## Machine applicability and next evidence

CoCo 1 is the historical context of these early-1983 articles. CoCo 2 operation
is not established by these pages; CoCo 3 native graphics and GIME scheduling
are not covered. The phase and input policies in our guide can inform any of
the three, but each needs a separately checked adapter and memory budget.
Video standard, CPU clock and exact ROM revisions are unspecified in the
examined article contracts. Do not infer them from US publication addresses.

A small original implementation could check input during preparation, one-shot
transition consumption, animation completion exactly once, and return to play.
Test it against a deliberately blocking sequence and against invalid commands
that would otherwise increment the turn. The [guide](../game-loop.md)
specifies proposed outcomes. Those controls have not been run. Historical
reproduction, timing, brief presses between polls and hardware compatibility
remain open rather than silently passing through source inspection.

[march]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Color%20Computer%20Magazine/Color%20Computer%20Magazine%20-%208303%20-%20March%201983.pdf>
[april]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Color%20Computer%20Magazine/Color%20Computer%20Magazine%20-%208304%20-%20April%201983.pdf>
[may]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Color%20Computer%20Magazine/Color%20Computer%20Magazine%20-%208305%20-%20May%201983.pdf>
[june]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Color%20Computer%20Magazine/Color%20Computer%20Magazine%20-%208306%20-%20June%201983.pdf>
[honor]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Color%20Computer%20Magazine/Color%20Computer%20Magazine%20-%208303%20-%20March%201983.pdf#page=22>
[honor-listing]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Color%20Computer%20Magazine/Color%20Computer%20Magazine%20-%208303%20-%20March%201983.pdf#page=24>
[honor-fix]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Color%20Computer%20Magazine/Color%20Computer%20Magazine%20-%208303%20-%20March%201983.pdf#page=23>
[stones]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Color%20Computer%20Magazine/Color%20Computer%20Magazine%20-%208304%20-%20April%201983.pdf#page=35>
[rover]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Color%20Computer%20Magazine/Color%20Computer%20Magazine%20-%208304%20-%20April%201983.pdf#page=36>
[firecracker]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Color%20Computer%20Magazine/Color%20Computer%20Magazine%20-%208304%20-%20April%201983.pdf#page=37>
[correction]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Color%20Computer%20Magazine/Color%20Computer%20Magazine%20-%208306%20-%20June%201983.pdf#page=14>
[animation-one]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Color%20Computer%20Magazine/Color%20Computer%20Magazine%20-%208305%20-%20May%201983.pdf#page=24>
[animation-list]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Color%20Computer%20Magazine/Color%20Computer%20Magazine%20-%208305%20-%20May%201983.pdf#page=26>
[animation-two]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Color%20Computer%20Magazine/Color%20Computer%20Magazine%20-%208306%20-%20June%201983.pdf#page=34>
[copy]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Color%20Computer%20Magazine/Color%20Computer%20Magazine%20-%208306%20-%20June%201983.pdf#page=35>
