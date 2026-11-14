# Hot CoCo game techniques

Read this when choosing collision probes, keyboard controls, or foreground
occlusion for a small game. This bounded survey read three complete original
articles in *Hot CoCo*, October 1983, Vol. 1 No. 5. It adds practical proposals
for the parent to promote into the existing technique guides. No historical
listing was transcribed into the project or executed.

The useful additions are sparse collision probes with explicit blind spots,
a warning about whole-byte keyboard comparisons, and a concrete foreground
fill failure. None establishes a tested engine or a portable hardware setup.

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

## Collision: sparse probes buy simplicity, not complete coverage

Togliatti's *Attacker* is labelled 16K Extended Color BASIC. The listing uses
PMODE 3 for drawing and pixel tests, with a PMODE 4 display selection during
setup. It also writes clock-control addresses. Treat that as the article's
configuration, not a recommendation or a normal-clock performance result.
[October, 82, 86][attacker]

### What the published program does

The listing on page 86 has these useful boundaries:

- Lines 100–110 sample both joystick axes and update position using threshold
  bands. Horizontal movement remains forward even in the slow band.
- Line 140 erases the old ship rectangle, draws the new ship, and reads fire.
- Line 150 samples four points around the ship. A screen value above 5 sends
  control to the player's destruction routine.
- Lines 170–270 handle shooting. They use enemy positions to choose a target
  rather than scanning every pixel of a drawn shot.

The continuation on page 88 adds a different collision contract. Lines 530–550
move enemy projectiles, test a screen point, and then compare projectile
coordinates with an expanded rectangle around the player. Lines 650–660 also
combine a screen test with player bounds for another weapon. Thus this game
mixes screen-based scenery tests with coordinate-based object tests.
[October, 86, 88][attacker-code]

The sector diagram and drawing routines matter to interpreting those tests.
This is a deliberately coloured environment, not a general rule that certain
colours mean solid terrain in every game. The author restricts changes to the
ship's shape to a 10-by-13 boundary and reports little spare memory on a 16K
machine. That is the author's reported budget, not our measurement.
[October, 84, 89][attacker-sectors]

### Original adaptation: define probes as part of the collision shape

For a small ship in broad tunnels, a short probe list can make a first
implementation understandable. Keep the list separate from artwork so that
its limitations can be reviewed. The following is original pseudocode,
inspired by Togliatti's point tests, not a port of his program:

```text
# Configuration uses collision-space units, not BASIC array dimensions.
# probe_offsets must cover the boundaries relevant to this game's obstacles.
function hits_scenery(position, probe_offsets, scenery):
    for offset in probe_offsets:
        point = position + offset
        if outside_world(point):
            return true
        if scenery.is_solid(point):
            return true
    return false

function try_move(ship, displacement, scenery):
    # Enumerate adjacent positions, including the destination, in order.
    # The stepping rule must match the collision grid's units.
    candidate = ship.position
    for next_position in adjacent_steps(ship.position, displacement):
        if hits_scenery(next_position, ship.probes, scenery):
            return candidate
        candidate = next_position
    return candidate
```

Substeps and a separate `scenery` query are our additions. They are not claims
about *Attacker*. A framebuffer implementation of `is_solid` couples collision
to drawing order and colour. An independent occupancy representation costs
storage and requires scenery edits to update both representations.

Substeps address crossing an obstacle between updates. They do not repair a
probe layout that leaves gaps across the ship's width or height. For narrow
obstacles, test all relevant edge cells or use an explicit geometric collision
shape instead. Define whether touching counts as a collision before coding.

Before adopting this proposal, require these independent cases:

1. A clear tunnel accepts the full movement; a wall stops movement before entry.
2. A one-cell obstacle between two probes exposes the sparse method's blind spot.
3. A displacement that crosses a thin wall fails without substeps and stops with
   correctly chosen substeps.
4. Changing a decorative colour leaves collision unchanged if an independent
   map was chosen. A framebuffer design must document the opposite coupling.
5. Enlarging the art without changing the probes demonstrates the mismatch.

No such experiment was run here. Cost grows with probe count and substep count;
there is no measured frame-rate or cycle claim.

## Controls: sample held state before applying action policy

Landwehr explains why a standalone assembly program should not assume that
BASIC's keyboard state is still being refreshed. His example writes a column
selection to `$FF02`, reads `$FF00`, then compares the complete returned byte
with `$F7` for left, right, or space. The left branch is checked first and
returns to the scanning loop after filling the screen. This is a small input
demonstration, not a simultaneous-action controller.
[October, 106, 108][keyboard]

Two source discrepancies must travel with this citation:

- Page 106's M-key prose says column value 233. Its printed table places M
  under 223, not 233. The page image confirms that this is not merely OCR.
- Page 108 calls the matrix eight rows by eight columns; page 106's table shows
  seven labelled row values. Do not use this article alone to establish the
  hardware matrix dimensions.

Our inference from the listing is narrower than a hardware compatibility claim:
a whole-byte equality test can reject an intended key when another input bit
changes. Reading and recording all required keys before choosing actions also
avoids the demonstration's early-branch priority. Verify the machine's PIA
configuration, row masks, shared input bits, and permissible key combinations
in its hardware reference before implementing a scanner.

### Original adaptation: separate held movement from a press event

This pseudocode starts after a verified input adapter has returned logical
button states. It intentionally supplies no disputed register constants:

```text
current = input_adapter.sample_required_controls()
pressed = current AND NOT previous

horizontal = 0
if current.left AND NOT current.right:
    horizontal = -1
if current.right AND NOT current.left:
    horizontal = 1

if pressed.fire:
    request_one_shot()
move_player(horizontal)
previous = current
```

Neutral movement for opposing directions and one shot per new press are our
example policies, not Landwehr's rules. Initialize `previous` deliberately;
a button held at startup can either count as a new press or be suppressed.
For automatic fire, use held state with an explicit repeat interval instead.
Edge detection is not electrical debouncing and does not cure matrix ghosting.

Check held movement, release, direction plus fire, opposing directions, and a
second press after release. Validate the adapter on each claimed machine.
No keyboard scan or simultaneous-key behaviour was measured in this survey.

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
untested proposals. Promote the useful sections beside the existing
[moving-object](../moving-objects.md) and
[animation](../animation.md) guidance without changing that status.

[october]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Hot%20Coco%20%28OCR%29/HotCoCo-1983-10.pdf>
[knight]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Hot%20Coco%20%28OCR%29/HotCoCo-1983-10.pdf#page=72>
[attacker]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Hot%20Coco%20%28OCR%29/HotCoCo-1983-10.pdf#page=82>
[attacker-code]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Hot%20Coco%20%28OCR%29/HotCoCo-1983-10.pdf#page=86>
[attacker-sectors]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Hot%20Coco%20%28OCR%29/HotCoCo-1983-10.pdf#page=84>
[keyboard]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Hot%20Coco%20%28OCR%29/HotCoCo-1983-10.pdf#page=106>
[november]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Hot%20Coco%20%28OCR%29/HotCoCo-1983-11.pdf#page=10>
[february]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Hot%20Coco%20%28OCR%29/HotCoCo-1986-02.pdf#page=58>
