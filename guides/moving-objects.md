# Move objects without losing the world

Read this when a moving character leaves holes in the scenery, or when drawing
changes which objects collide. Rendering and collision need separate decisions.
The sources below explain useful starting points. An original full-redraw
example now checks a bounded implementation on two emulator configurations.

## Start with what the drawing routine overwrites

Don Inman, Kurt Inman, and Dymax describe a small shape table and
joystick-driven
movement in *Assembly Language Graphics for the TRS-80 Color Computer*.
The example uses mode 6C. Its drawing routine copies two bytes on each of six
rows. Its erase routine clears that same rectangle before drawing elsewhere.
[Printed 151–156, PDF 159–164][graphics]

Our conclusion from those instructions is that clearing the rectangle cannot
restore arbitrary scenery. It replaces every byte in the rectangle, including
positions where the object shape has background-colour pixels. This is a
property of the examined listing, not an observed runtime failure.

The book's later two-saucer exercise asks readers to investigate overlap.
It does not provide a finished overlap-safe renderer or collision system.
[Printed 168–169, PDF 176–177][saucers]

## Choose how to restore the background

The full-redraw example below has emulator checks. Historical sources also
describe two background-restoration methods. Applying those methods to a new
starter renderer remains untested. The original masked example below uses
full-background redraw instead.
Choose a restoration strategy deliberately before adding scenery.

For a uniform background, repainting the old rectangle may be enough.
Check that no other object or trail occupies that rectangle.

For one object over an unchanged background, a saved rectangle is a possible
starting design:

1. Save the background bytes covered by the new object.
2. Draw the object.
3. Restore those saved bytes before moving the object.
4. Repeat at the new position.

This simple sequence needs more work when objects overlap or scenery changes.
Restoring an old snapshot can erase a newer object or resurrect removed scenery.
Do not claim that saving a rectangle alone solves overlap.

For several objects, consider redrawing affected regions from authoritative
world state. Restore the scenery first, then draw all intersecting objects in
a defined order. A full redraw is easier to reason about but can cost more time.
The [sound guide](sound.md) explains why that cost also matters to audio.

A transparency mask answers a different question: which destination pixels
should this draw preserve? It does not remember what was there before the draw.
A masked drawing routine still needs an erase or redraw strategy.
This distinction is our design guidance. This pass found no examined CoCo
masked-renderer listing to promote as an implementation reference.

## Restore from a persistent background

Harvey Brofman's *Dunkey Munkey* source keeps separate display and background
buffers. Its `ERASE` routine copies a rectangular region from the background
into the display. The source exposes this in `KONG.TXT`, lines 98–99, and
`GRAPH2.TXT`, lines 314–345. [Source ZIP][dunkey]

This background represents the scenery that should remain after an object moves.
It is not a snapshot captured immediately before the object was drawn. When a
rivet disappears, the game changes its state, erases it from the background,
then restores the display region. Read `SCREN2.TXT`, lines 308–316. The later
scenery update at lines 334–355 also changes the background before copying it.

Our proposed adaptation is to keep scenery authoritative in a separate buffer.
Update that buffer when a door opens, a pickup disappears, or terrain changes.
Restore old object regions from it, then redraw intersecting objects in their
layer order. That last redraw rule is our design recommendation; the examined
routines do not prove safe handling of arbitrary overlapping objects.

The two historical buffers alone occupy 12,288 bytes. Budget that cost before
choosing this method. Its renderer uses two-bit pixels and has no transparent-
colour skip in the examined shape loop. It is not a ready-made two-colour masked
renderer, and it has not been ported or validated by this starter.

## Save background regions separately for each screen

*GrafExpress 2.0* describes another method for objects that leave no trail.
Its manual calls them nonsticky sprites. The engine saves all regions needed by
the next frame before drawing sprites, draws all sprites, displays that screen,
then restores the previously displayed screen. The restoration uses a separate
set of saved regions belonging to that previous screen.
[Printed 22, PDF 27][graf-restoration]

For an original two-screen renderer, our adaptation would associate each saved
region with the screen buffer and frame from which it came. Save regions before
any objects are drawn into that frame. Do not reuse the newest saved pixels to
repair the previous screen. Test changes to scenery as well as overlapping
objects. These rules are derived design guidance, not a tested starter renderer.

GrafExpress explains that region saving and restoration cost time and memory.
Its two restoration-buffer sets do not establish that adding a third display
buffer is safe. Read the complete discussion before changing the buffering
scheme. Its own pixel-alignment rules and composite-only GE256 display method
also do not define portable CoCo 1/2 graphics behavior.

## Keep the whole object inside the screen

The book's screen-address calculation clamps placement before copying the
shape. The relevant calculation and listing are on printed 153–155,
PDF 161–163. Read the dimensions and storage units with the code.
[Inman and Inman with Dymax][bounds]

For a new renderer, our proposed pixel-coordinate contract is:

```text
0 <= x <= screen_width - object_width
0 <= y <= screen_height - object_height
```

This assumes a fully visible object and matching units. Clipping an object at
the edge requires a different routine. Convert pixel coordinates to byte offsets
only after defining packing and alignment. Check every horizontal alignment
the renderer supports, including partial bytes at the right edge.

## Decide whether the picture is also the collision map

Kenneth Reighard Jr.'s **"The Universal Pick-Up"** presents the BASIC game
*Interplanetary Trash Collector*. Its listing draws a trail, moves the current
point, checks screen bounds, and dispatches on `PPOINT` at the destination.
Different pixel values distinguish empty space, obstacles, trail, and pickups.
[The Rainbow, October 1992, cover/PDF 1 and printed/PDF 10][trash]

The article targets CoCo 3 and gives changes for CoCo 1/2 and composite output.
It also uses a faster clock. Those are the author's configurations, not tested
support claims for this starter. Do not copy its clock writes into a
normal-speed
project without changing the project's contract.

Our inference is that screen-based collision makes drawing part of game state.
A decorative pixel, an erase operation, or a new trail colour can change a
collision result. That can be a useful compact design for a trail game.
It becomes a constraint when art and collision rules need to vary independently.

For a new game, write down what each collision value means before choosing
colours.
If decoration must not affect movement, consider a separate occupancy map or
object bounds. These are proposed alternatives, not techniques reproduced from
this article. Tile maps and general masked collision still need source research.
The next
section adds a published example of separating visible and collision shapes.

### Separate appearance from collision shape

GrafExpress distinguishes transparency from solidity. A transparent-colour
picture makes those pixels both invisible and nonsolid, but a rectangle picture
can be invisible and still solid. The manual suggests using such rectangles for
collision against scenery drawn separately.
[Printed 3 and 15–16, PDF 8 and 20–21][graf-shapes]

Its sprite changes affect collision checks immediately but do not reach the
screen until the display command. [Printed 17, PDF 22][graf-state]
For a new game, decide whether collision uses the proposed next positions or the
currently displayed frame. Invisible walls and independently sized collision
bounds are possible design adaptations. Neither a tile collision map nor a
pixel-perfect collision implementation has been validated here.

## Test the awkward cases first

These checks are proposed acceptance cases for an original implementation:

- Move over a patterned background and compare the restored region exactly.
- Cross two objects, separate them, and check both drawing orders.
- Change scenery beneath an object before restoring its old location.
- Visit all four edges with the largest supported object.
- Check guards around screen and saved-background storage.
- Test empty space, obstacle, trail, and pickup outcomes independently.
- Test movement that could cross an obstacle between sampled positions.
- Change decorative colours and check whether collision changes as intended.

Use expected world state independent of the rendering code.
Then inspect the display for flicker and measure the work at the chosen clock.
A byte-correct frame alone does not establish smooth animation.

## Try the original full-redraw example

The [moving-objects example](../examples/moving-objects/README.md) draws the
current patterned background before two opaque, byte-aligned rectangles.
Their overlap order changes, and the scenery changes while they move.
This implements one restoration strategy without storing old background pixels.

Its XRoar checks cover 13 completed frames for each defined CoCo 1 and CoCo 2
configuration. They compare the entire framebuffer, positions, frame counter,
and memory guards against independent expectations. The cases include overlap
in both layer orders, separation, changed scenery, and boundary reversals.

Both configurations use NTSC, 32 KiB, a normal-clock 6809, and the non-T1
MC6847.
The CoCo 2 run selects its own firmware explicitly. This is not evidence for
all CoCo 2 revisions. Read the example's complete machine contract before reuse.

The example does not implement collision, masks, partial-byte placement, or
independent vertical motion for the two objects. Visual appearance, frame rate,
PAL, T1, and physical hardware remain unverified.

## Try masked objects

The [masked-object example](../examples/masked-objects/README.md) draws hollow
objects with transparent holes and opaque black and green pixels. Each scene
restores the complete background, then combines objects in the chosen order
with `(destination AND preserve_mask) OR ink`.

Twelve scenes on each defined CoCo 1/2 configuration check every framebuffer
byte, guards, corners, overlap order, removal and changed scenery. The oracle
uses independent pixel geometry. Origins must be byte-aligned and the entire
object must fit on screen. This example adds no clipping or collision system.
Emulator display appearance, timing and physical hardware remain untested.

## Sources and limits

- Don Inman, Kurt Inman with Dymax, *Assembly Language Graphics for the TRS-80
  Color Computer*, chapter 7. Examined printed 151–158, 163, 168–169,
  PDF 159–166, 171, 176–177. Resource `assembly-graphics`.
  The claims above use the specific subsets linked beside them.
  [Archive][graphics]
- Kenneth Reighard Jr., "The Universal Pick-Up," *The Rainbow*, October 1992,
  cover/PDF 1 and printed/PDF 10. The contents calls it "Inter-Planetary Trash".
  the listing is `IPTRASH`. Resource `rainbow-1992-10`. [Archive][trash]

- Harvey Brofman, *Dunkey Munkey*, source dated June 24, 1982. The source header
  credits Intellectronics; the archive filename credits Cercomp. File/routine
  citations above refer to the downloaded ZIP. [Archive][dunkey]
- Sundog Systems, *GrafExpress 2.0*, 1991. Printed 2–3, 15–18 and 21–22;
  PDF 7–8, 20–23 and 26–27. Resource `grafexpress`. [Archive][graf-restoration]

We examined the relevant page images and listing, but did not assemble the
book example or run the BASIC game. No physical-machine, timing, or
compatibility
result follows from this guide. The adaptation designs and test cases are
our original guidance; the cited historical methods remain untested here. Only
the bounded full-redraw and masked-object examples above have runtime
evidence. See [research notes](../guidance/game-research.md#rendering-and-collision-pass)
for earlier rejected leads and the limited correction search.
[Rendering source notes](../guidance/rendering-sources.md) record the later
source reading, hashes, rejected leads and implementation limits.

[graphics]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Graphics%20for%20the%20TRS-80%20Color%20Computer%20%28Don%20Inman%2C%20Kurt%20Inman%20with%20Dymax%29.pdf#page=159>

[saucers]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Graphics%20for%20the%20TRS-80%20Color%20Computer%20%28Don%20Inman%2C%20Kurt%20Inman%20with%20Dymax%29.pdf#page=176>

[bounds]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Graphics%20for%20the%20TRS-80%20Color%20Computer%20%28Don%20Inman%2C%20Kurt%20Inman%20with%20Dymax%29.pdf#page=161>

[trash]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow,%20The%20(OCR)/The%20Rainbow%20Vol.%2012%20No.%2003%20-%20October%201992.pdf#page=10>

[dunkey]: <https://colorcomputerarchive.com/repo/Programming/Source/Dunkey%20Monkey/Dunkey%20Munkey%20Source%20(Harvey%20Brofman)%20(Cercomp).zip>

[graf-restoration]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Programming/GrafExpress%202.0%20(Sundog%20Systems).pdf#page=27>

[graf-shapes]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Programming/GrafExpress%202.0%20(Sundog%20Systems).pdf#page=20>

[graf-state]: <https://colorcomputerarchive.com/repo/Documents/Manuals/Programming/GrafExpress%202.0%20(Sundog%20Systems).pdf#page=22>
