# Hot CoCo game techniques

Read this for the sources behind the Hot CoCo citations, and for foreground
occlusion in a small game. This bounded survey read three complete original
articles in *Hot CoCo*, October 1983, Vol. 1 No. 5. We copied no historical
listing into the project and ran none.

The [controls guide](../controls-and-collision.md) now holds what the
keyboard and *Attacker* articles established. This note keeps the reading
coverage, the correction search and the *Knight Rider* foreground fill
failure. None establishes a tested engine or a portable hardware setup.

## Sources and reading coverage

All October page numbers below are both printed and one-based PDF positions
in [the archive OCR edition][october]. Other scans can have different offsets.
These are research-local identifiers, not additions to `resources.json`.

- `hot-coco-games-knight`: LeRoy W. Gross, "Knight Rider," pages 72, 73,
  76. Read prose, three screen photographs, and the complete "Riding Knight"
  listing through line 620.
- `hot-coco-games-attacker`: Matt Togliatti, "Attacker," pages 82, 84, 86,
  88, 89. Read rules, variable table, program breakdown, sector diagram, and
  the complete listing through line 1080.
- `hot-coco-games-keyboard`: Larry Landwehr, "Read the Keyboard in Assembly,"
  pages 106, 108. Read prose, matrix table, and the complete assembly listing.

Each selected page was inspected as a full-page image as well as through the
archive's extracted text. Intervening advertisements are not continuations.
The page images correct OCR errors such as `0` becoming `9` in line numbers.
Use the images to review numeric details below.

Local evidence is under ignored `local/research/hot-coco-games/`:

- `1983-10.pdf`, `1983-10.txt`, and `1983-10-pN.png` for selected pages.
- `1983-11.pdf`, `1983-11.txt`, and `1983-11-p10.png` / `-p12.png`
  for the bounded correction check.
- `1986-02.pdf` and `1986-02.txt` for candidate screening only.

SHA-256 of the downloaded PDFs:

```text
1983-10.pdf
76218e4e0bc98ca0545ef3db34ce89bfb080998d7e89370f3ced483a2909e7a4
1983-11.pdf
861263acedfce43cde78fb36d531fc717208d11c362081c7501634e37e971fde
1986-02.pdf
a65461f29c5f2311a14cddce2ac18f9fe1d42e0a71ab02f2ace9e358bc2a671a
```

Text extraction used the installed `pdftotext -layout`. Selected October pages
were rendered with the existing project Python and `pypdfium2`, scale 1.5.
November feedback pages used scale 1.4. This was local research extraction,
not a change to the project's conversion pipeline or manifest.

## Animation: repaint foreground coverage before showing a frame

Gross's *Knight Rider* is labelled 16K Extended Color BASIC. It draws scenery,
the moving rider, and foreground scenery in an intentional order. The three
photographs on page 73 illustrate passing behind a tree, in front of another,
and into a doorway. Lines 210 and 400 select and clear alternate drawing
screens. The author tells readers to delete lines 215 and 405 to stop showing
the frames while they are under construction; the later display statements
then reveal the completed frames. [October, 72–73, 76][knight]

The useful failure case is on page 76. Gross explains that simply painting the
foreground foliage green can leave the rider showing through: if the fill
finds green at its starting area, it can skip the intended repaint. His listing
first fills the foliage with an intermediate colour, then fills it green.
This is a specific flood-fill workaround, not a general transparency mask.

### Original adaptation: explicit coverage for foreground layers

For an assembly renderer, prefer precomputed coverage or opaque spans for a
foreground tree rather than relying on a flood fill's seed colour:

```text
back = acquire_hidden_frame()
clear_or_rebuild_background(back, world)
draw_rear_scenery(back, world)
draw_actors(back, actors)
for foreground in world.foreground_layers:
    overwrite_covered_pixels(back, foreground.coverage, foreground.colours)
present_completed_frame(back)
```

This is our design proposal. The coverage data, synchronization contract, and
renderer do not come from Gross's listing. A hidden buffer does not by itself
prove tear-free presentation. Explicit coverage consumes asset memory; a full
scene rebuild consumes drawing time. Repainting only dirty areas needs its own
rules for all intersecting layers.

Test a foreground object whose final colour already equals the background,
with a differently coloured actor behind it. Compare both overlap and later
separation. Removing the foreground pass should expose the actor as a failure
control. Change the foreground while the actor overlaps it to check stale
background handling. Inspect the rendered display separately from framebuffer
bytes. No runtime or visual experiment was performed here.

## Selection, exclusions, and bounded correction search

The October contents page led to the three selected articles. "Speedy Assembly
Graphics" was screened at its opening page but not selected: generic pixel
primitives were less useful here than a complete game with collision rules.
"Animate" / "Juggling Judy" was screened as a character-animation lead; its
basic pose cycling did not justify another full reading in this pass.
Neither is cited as implementation evidence.

Dick Myers's "Cartooning and Animation," February 1986, was screened through
its contents entry and opening text, not read completely. The beginner drawing
and animation overview was not promoted. The already-covered Sound/Speech
cartridge material and commercial game advertisements were excluded.
[February archive][february]

The correction search was bounded as follows, on 2026-11-14:

- Searched the November 1983 issue's extracted text for the three titles,
  author surnames, `correction`, `errata`, and `oops`. No relevant correction
  was identified. OCR can miss matches.
- Read November's complete Feedback section as images, printed 8 and 10,
  PDF 10 and 12. It contains corrections to other articles, but none for the
  three selected articles. [November archive][november]
- Searched the web for `"Hot CoCo" "Knight Rider" correction`,
  `"Hot CoCo" "Landwehr" correction`, and
  `"Hot CoCo" "Attacker" correction`, then archive-restricted searches for
  Knight Rider corrections, the keyboard article with `233`, and Attacker
  with Togliatti and `error`. No relevant erratum was found; the keyboard
  search returned the original inconsistent passage.

This does not establish that no later correction exists. The M-key discrepancy
and matrix-size statement remain unresolved against an independent hardware
source. *Attacker* also says "right" twice in its horizontal-control prose on
page 82; lines 100–110 on page 86 are the precise source for its threshold
behaviour. Preserve that discrepancy when describing the original controls.

## Target and evidence limits

These 1983 articles concern the original CoCo generation. CoCo 1 is the natural
first reproduction target. CoCo 2 requires its own firmware, keyboard, display,
and timing checks; the articles do not establish all board revisions. CoCo 3
legacy modes require separate checks, and native CoCo 3 graphics are outside
this evidence. Conceptual pseudocode can inform all three without claiming
binary compatibility.

Completed evidence is source reading and image inspection only. There is no
assembly, emulator execution, framebuffer, rendered-display, audio, timing, or
physical-machine result. The pseudocode and acceptance cases above are original
untested proposals. The [moving-object](../moving-objects.md) and
[animation](../animation.md) guides hold the related checked work.

[october]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Hot%20Coco%20%28OCR%29/HotCoCo-1983-10.pdf>
[knight]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Hot%20Coco%20%28OCR%29/HotCoCo-1983-10.pdf#page=72>
[november]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Hot%20Coco%20%28OCR%29/HotCoCo-1983-11.pdf#page=10>
[february]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Hot%20Coco%20%28OCR%29/HotCoCo-1986-02.pdf#page=58>
