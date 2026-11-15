# Move objects without holes in the scenery

This example moves objects over scenery and puts the scenery back where each
object was. In each frame, it first restores the scenery at the old object
positions. Then it draws the objects at their new positions, the bottom layer
first.

The default method keeps a second copy of the scenery in RAM, the scenery
buffer. It copies each old rectangle back from that buffer.

The example does not hide the drawing from the display, so a frame can show
tearing. The [page flip](../page-flip/README.md) example draws this scene into
a hidden screen. The example does not draw transparent pixels, clip at an
edge, place objects inside a byte, detect collisions or time the frames.

## Choose a restore method

The scenery buffer is the default. Use it when the scenery has a pattern and
objects can overlap. It costs 6 KiB of RAM in RG6.

| Method | Variant | Extra RAM | Bytes for each object | Overlap rule | When the scenery changes |
| --- | --- | --- | --- | --- | --- |
| Scenery buffer | (none) | 6,144 | 32 | Any order | Change the buffer, then copy all of it |
| Save under | `save` | 36 | 48 | Reverse of the draw order | Draw all of the scenery again |
| Redraw | `redraw` | 0 | 16 | None | Nothing more |

- Extra RAM: the bytes that the method needs in this example, for two
  objects.

- Bytes for each object: the bytes that the method copies or writes for one
  16×8 object in each frame, with the draw. Redraw also writes 6,144 bytes of
  scenery in each frame.

- Overlap rule: the order in which to restore the old objects.

Notes on the methods:

- Scenery buffer: the buffer is the true scenery. When a door opens or a
  pickup goes, change the buffer and the screen. Restore all old objects
  before you draw any object.

- Save under: before each draw, keep the screen bytes under the object. In
  the next frame, put them back, the object drawn last first. The saved bytes
  of an object can include an object that was below it. Thus the wrong order
  shows that lower object again at its old position.

- Save under: saved bytes are not correct after the scenery changes beneath
  them. Draw all of the scenery again at that time.

- Redraw is the simplest method and the slowest. It writes the full screen in
  each frame.

Other ways that this example does not show:

- Erase the old rectangle with one colour. Inman's program does this, with
  `CLR`. It is correct only on a one-colour background. On this checker, it
  makes black holes.

- Restore only the screen strip that the object uncovers. This writes fewer
  bytes, but it needs a different routine for each direction.

- Redraw the tiles under the old rectangle from a tile map. The
  [tile room](../tile-room/README.md) keeps the room as a tile map.

The [moving-objects guide](../../guidance/techniques/moving-objects.md)
compares the published methods.

## Restore and draw

The example is the three `>>> EXAMPLE` parts of [main.asm](main.asm):

1. After the label `frame`, restore the scenery at the old object positions.
   - Scenery buffer: `copy_back` copies 8 rows of 2 bytes from the buffer to
     the screen. The buffer is at `$4400`, so each buffer byte is at the
     screen address plus `$4000`.
   - Save under: `put_back` writes the saved bytes of the object drawn last,
     then of the object drawn first.
   - Redraw: go to step 2 in each frame.

2. At `new_scenery`, show all of the new scenery. The scenery buffer method
   draws the scenery into the buffer, then copies 6,144 bytes to the screen.
   The other methods draw the scenery on the screen. This also removes the
   old objects, so step 1 does not occur in this frame.

3. At `draw_objects`, draw the objects, the bottom layer first.
   `rectangle` records the screen address of each object in a slot, for step
   1 of the next frame. The save under method also keeps the 16 screen bytes
   under the object in the slot.

The `--- CONTEXT` blocks are not part of the practice:

- They set up RG6 at `$0400` with colour set 0, as in
  [first-screen](../first-screen/README.md).

- They count the frames. The scenery is new in frame 1 and changes in each
  64th frame.

- They draw an 8×8 checker scenery. Bit 6 of the frame count inverts it.

- They move two opaque 16×8 rectangles. Green object A starts at the top
  left. Black object B starts at the top right. They move in opposite
  directions across the screen, and down together. Each reverses at an edge.

- Every 32 frames, they swap the layer order. Bit 5 of the frame count puts
  B below A.

- They pause after each frame.

The program keeps the interrupts, stack, direct page and CPU clock that BASIC
sets.

The program ends below `$4400`. The build fails if it reaches the scenery
buffer. The `state` label is data. The check fails if the CPU runs it.

## See and check each method

Open a terminal in the starter folder. Copy one line and paste it to see that
method in XRoar. The objects move until you close the window.

```sh
uv run python scripts/coco.py run examples/moving-objects                    # scenery buffer
uv run python scripts/coco.py run examples/moving-objects --variant save     # save under
uv run python scripts/coco.py run examples/moving-objects --variant redraw   # redraw
```

All three methods show the same picture. To check all three methods, paste
this line:

```sh
uv run python scripts/coco.py check examples/moving-objects --video
```

The `--video` option needs the
[instrumented XRoar](../../guidance/starter/toolchain.md#instrumented-xroar).

The check takes a snapshot at 15 frames. It compares all 6,144 screen bytes
and XRoar's rendered picture with [expected.py](expected.py).

The model in `expected.py` calculates each position from the bounce rule. It
sets each pixel from the scenery and the objects in layer order. It does not
model the restore. A correct restore leaves no trace of the old positions.

The frames include these cases:

- Frame 1, the first scenery, and frame 2, the first restore.

- Full overlap in both layer orders, frames 16 and 46, and the frame after
  each.

- The swap of the layer order, frames 31 and 32.

- The change of the scenery, frame 64, and the restore after it.

- The reversals at the edges, frames 185, 186, 369 and 370.

A save under restore in the wrong order fails at frame 17. A scenery buffer
restore of only one object fails at frame 2.

The check uses the CoCo 1 target in [coco.toml](coco.toml): NTSC, 32 KiB,
normal clock, the non-T1 MC6847 and Color BASIC 1.1. It does not prove the
result on a television, a physical CoCo, PAL, the MC6847T1 or the CoCo 3. It
does not measure the time of each method.

## Sources

Read these pages before you change the screen setup or the bit order. Use
[reference lookup](../../guidance/starter/references.md) to get them.

- Inman, Inman and Dymax, *Assembly Language Graphics for the TRS-80 Color
  Computer*, PDF 106–107: mode 6R is 256×192 at `$0400`–`$1BFF`. It has eight
  pixels in each byte and uses 6 KiB. With colour set 0, a 0 bit shows black
  and a 1 bit shows green.

- The same book, PDF 162: the program erases the old shape with `CLR` on each
  of its rows. Then it draws the shape at the new position.

- Motorola, *MC6847 Video Display Generator* datasheet, PDF 19, Table 3: in
  RG6, bit 7 is the leftmost pixel of a byte.

- Tandy, *Color Computer Technical Reference Manual*, PDF 14–15: the `$FF22`
  bits, and the SAM offset and mode bits. PDF 31: RG6 uses SAM V=`110` and
  `$FF22` bits 7 to 4 `1111`.

The restore methods, the scene and the bounce rule are our own design.
