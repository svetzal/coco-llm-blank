# Move objects without losing the world

Read this when a moving character leaves holes in the scenery, or when drawing
changes which objects collide. Rendering and collision need separate decisions.
The sources below explain useful starting points, not a tested sprite engine.

## Start with what the drawing routine overwrites

Don Inman, Kurt Inman, and Dymax describe a small shape table and joystick-driven
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

The following designs are our proposed adaptations. We have not implemented or
benchmarked them in this starter. Choose one deliberately before adding scenery.

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
support claims for this starter. Do not copy its clock writes into a normal-speed
project without changing the project's contract.

Our inference is that screen-based collision makes drawing part of game state.
A decorative pixel, an erase operation, or a new trail colour can change a
collision result. That can be a useful compact design for a trail game.
It becomes a constraint when art and collision rules need to vary independently.

For a new game, write down what each collision value means before choosing colours.
If decoration must not affect movement, consider a separate occupancy map or
object bounds. These are proposed alternatives, not techniques reproduced from
this article. Tile maps and general masked collision still need source research.

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

## Sources and limits

- Don Inman, Kurt Inman with Dymax, *Assembly Language Graphics for the TRS-80
  Color Computer*, chapter 7. Examined printed 151–158, 163, 168–169,
  PDF 159–166, 171, 176–177. Resource `assembly-graphics`.
  The claims above use the specific subsets linked beside them. [Archive][graphics]
- Kenneth Reighard Jr., "The Universal Pick-Up," *The Rainbow*, October 1992,
  cover/PDF 1 and printed/PDF 10. The contents calls it "Inter-Planetary Trash".
  the listing is `IPTRASH`. Resource `rainbow-1992-10`. [Archive][trash]

We examined the relevant page images and listing, but did not assemble the
book example or run the BASIC game. No physical-machine, timing, or compatibility
result follows from this guide. The restoration designs and test cases are
our original proposals. See [research notes](../guidance/game-research.md#rendering-and-collision-pass)
for rejected leads and the limited correction search.

[graphics]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Graphics%20for%20the%20TRS-80%20Color%20Computer%20%28Don%20Inman%2C%20Kurt%20Inman%20with%20Dymax%29.pdf#page=159>

[saucers]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Graphics%20for%20the%20TRS-80%20Color%20Computer%20%28Don%20Inman%2C%20Kurt%20Inman%20with%20Dymax%29.pdf#page=176>

[bounds]: <https://colorcomputerarchive.com/repo/Documents/Books/Assembly%20Language%20Graphics%20for%20the%20TRS-80%20Color%20Computer%20%28Don%20Inman%2C%20Kurt%20Inman%20with%20Dymax%29.pdf#page=161>

[trash]: <https://colorcomputerarchive.com/repo/Documents/Magazines/Rainbow,%20The%20(OCR)/The%20Rainbow%20Vol.%2012%20No.%2003%20-%20October%201992.pdf#page=10>
